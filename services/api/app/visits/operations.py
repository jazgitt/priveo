"""Operations outcomes preserve original jobs, failure notes and proof."""

import uuid
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.customers.models import Customer, Vehicle
from app.directory import lookup
from app.directory.models import Society
from app.directory.service import audit
from app.identity.models import Login
from app.identity.service import User
from app.media.models import MediaUpload
from app.media.service import download_url
from app.media.store import get_object_store
from app.notifications import emit
from app.platform.clock import today_ist
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import service as scheduling
from app.scheduling.models import Job, Schedule, SchedulingCrew, Visit
from app.scheduling.outcomes import customer_summary, outcome_of_visit, visit_outcomes
from app.visits.models import JobOutcome, JobReassignment, OperationsDecision

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])

Day = date  # the field name `date` hides the type inside a model


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["Skip", "Reschedule"]
    reason: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=2000)


class SkipVisit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=2000)


class BulkSkip(BaseModel):
    """S-12: skip many visits at once for a disruption. Give `visit_ids`, or a
    `society_id` and `date`. The reason is mandatory."""

    model_config = ConfigDict(extra="forbid")
    visit_ids: list[uuid.UUID] | None = Field(default=None, max_length=500)
    society_id: uuid.UUID | None = None
    date: Day | None = None
    reason_key: str | None = Field(default=None, max_length=60)
    reason: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=2000)


class MoveDate(BaseModel):
    """S-05: move one scheduled service to any date from today on."""

    model_config = ConfigDict(extra="forbid")
    date: Day
    reason: str = Field(min_length=1, max_length=200)


class BulkReassign(BaseModel):
    """S-09: give many jobs to one crew member. Give `job_ids`, or the crew
    member whose day to hand over (`from_crew_id` and `date`)."""

    model_config = ConfigDict(extra="forbid")
    job_ids: list[uuid.UUID] | None = Field(default=None, max_length=500)
    from_crew_id: uuid.UUID | None = None
    date: Day | None = None
    to_crew_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=200)


def locked_job(db, job_id):
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None:
        raise ApiError("not_found", "Job not found.", 404)
    return job


def decide(db, job, body, actor):
    prior = db.scalar(select(OperationsDecision).where(OperationsDecision.job_id == job.id))
    if prior:
        if prior.action != body.action:
            raise ApiError("already_resolved", "This job already has an outcome.", 409)
        return False
    if job.status not in ("Scheduled", "Could not complete"):
        raise ApiError("job_not_open", "Choose a scheduled or missed job.", 409)
    if body.action == "Reschedule" and (
        job.status != "Could not complete" or job.service == "Cleaning-External"
    ):
        raise ApiError("invalid_outcome", "Only missed Interior and Spa jobs can be retried.", 409)
    decision = OperationsDecision(
        job_id=job.id,
        action=body.action,
        reason=body.reason.strip(),
        note=body.note.strip(),
        by_login_id=actor,
    )
    db.add(decision)
    db.flush()
    audit(
        db,
        actor,
        "operations",
        job.id,
        body.action.lower(),
        {
            "reason": decision.reason,
            "note": decision.note,
            "service": job.service,
        },
    )
    return True


def skip_job(db, job, body, actor, commit=True):
    if not decide(db, job, body, actor):
        return job
    if not db.scalar(select(JobOutcome.id).where(JobOutcome.job_id == job.id)):
        db.add(JobOutcome(job_id=job.id, kind="skipped", note=body.note.strip(), by_login_id=actor))
    job.status = "Skipped"
    db.flush()
    scheduling.refresh_visit_status(db, job.visit_id)
    if job.addon_booking_id:
        booking = db.get(AddonBooking, job.addon_booking_id)
        # There is no "Skipped" booking status. Retain Missed for admin refund/rebooking.
        if booking and booking.status != "Cancelled":
            booking.status = "Missed"
    if commit:
        db.commit()
        emit.job_status_changed(db, job)
    return job


def make_redo(db, job, source, target_date, actor, note):
    """A follow-up job on `target_date`, linked by `source_job_id`, then a run
    of that day's schedule so the normal planner places it. Used by the
    next-day retry and by the admin's move-to-date (S-05). Commits."""
    origin = db.get(Schedule, source.schedule_id)
    target = db.scalar(
        select(Schedule)
        .where(
            Schedule.society_id == origin.society_id,
            Schedule.start_date <= target_date,
            Schedule.end_date >= target_date,
        )
        .with_for_update()
    )
    if target is None:
        target = scheduling.get_or_create_schedule(db, origin.society_id, target_date, 1)
    visit = Visit(
        schedule_id=target.id,
        vehicle_id=source.vehicle_id,
        date=target_date,
        addon_key=f"redo:{job.id}",
    )
    db.add(visit)
    db.flush()
    redo = Job(
        visit_id=visit.id,
        service=job.service,
        duration_minutes=job.duration_minutes,
        finish_by_minute=job.finish_by_minute,
        addon_booking_id=job.addon_booking_id,
        addon_request_id=job.addon_request_id,
        source_job_id=job.id,
    )
    db.add(redo)
    if job.addon_booking_id:
        booking = db.get(AddonBooking, job.addon_booking_id)
        booking.proposed_date = target_date
        booking.status = "Requested"
        booking.requested_date, booking.requested_finish_by = None, None
    db.flush()
    scheduling.record(db, target.id, actor, "redo", note)
    # The scheduler keeps frozen placements and includes explicit retry jobs.
    scheduling.run_schedule(db, target, actor)
    return redo


def reschedule(db, job, body, actor):
    if not decide(db, job, body, actor):
        return job
    source = db.get(Visit, job.visit_id)
    target_date = source.date + timedelta(days=1)
    if target_date < today_ist():
        raise ApiError(
            "retry_date_passed", "The next-day retry date has passed. Skip the job instead.", 409
        )
    make_redo(db, job, source, target_date, actor, f"Next-day retry for {job.id}")
    return job


def job_out(db, job, store, derived=None):
    visit = db.get(Visit, job.visit_id)
    schedule = db.get(Schedule, visit.schedule_id)
    vehicle = db.get(Vehicle, visit.vehicle_id)
    customer = db.get(Customer, vehicle.customer_id)
    society = db.get(Society, schedule.society_id)
    crew = db.get(SchedulingCrew, job.crew_id) if job.crew_id else None
    login = db.get(Login, crew.login_id) if crew else None
    failure = db.scalar(select(JobOutcome).where(JobOutcome.job_id == job.id))
    decision = db.scalar(select(OperationsDecision).where(OperationsDecision.job_id == job.id))
    redo = db.scalar(select(Job).where(Job.source_job_id == job.id))
    reason = lookup.reason_label(db, failure.reason_key) if failure and failure.reason_key else None
    photo = db.get(MediaUpload, failure.upload_id) if failure and failure.upload_id else None
    actor = db.get(Login, decision.by_login_id) if decision else None
    visit_outcome = derived.get(visit.id) if derived else None
    visit_outcome = visit_outcome or outcome_of_visit(db, visit)
    reporter = db.get(Login, failure.by_login_id) if failure else None
    return {
        "id": str(job.id),
        "visit_id": str(visit.id),
        "date": visit.date,
        "society_id": str(schedule.society_id),
        "society": society.name,
        "customer_id": str(customer.id),
        "customer_name": f"{customer.first_name} {customer.last_name}",
        "vehicle": f"{vehicle.make} {vehicle.model}",
        "registration": vehicle.registration,
        "crew_name": login.display_name if login else None,
        "service": job.service,
        "status": job.status,
        "reason_key": failure.reason_key if failure else None,
        "reason": reason or "",
        "note": failure.note if failure else "",
        # Who recorded the outcome and when (planned vs actual).
        "reported_by": reporter.display_name if reporter else None,
        "reported_at": failure.at if failure else None,
        # Derived for the whole visit: partial visits are flagged for follow-up.
        "visit_outcome": visit_outcome.outcome,
        "partial": visit_outcome.partial,
        "planned_services": visit_outcome.planned,
        "delivered_services": visit_outcome.delivered,
        "missed_services": visit_outcome.missed,
        "outcome_summary": customer_summary(
            visit_outcome.planned, visit_outcome.delivered, visit_outcome.missed),
        "photo_url": download_url(store, photo) if photo and photo.status == "Confirmed" else None,
        "outcome": decision.action
        if decision
        else (
            "Covered"
            if job.status == "Could not complete" and job.service == "Cleaning-External"
            else None
        ),
        "covered_on": visit.date + timedelta(days=1)
        if job.status == "Could not complete"
        and job.service == "Cleaning-External"
        and not decision
        else None,
        "rescheduled_on": db.get(Visit, redo.visit_id).date if redo else None,
        "replacement_job_id": str(redo.id) if redo else None,
        "replacement_status": redo.status if redo else None,
        "replacement_assigned": redo.crew_id is not None if redo else None,
        "resolution_reason": decision.reason if decision else "",
        "resolution_note": decision.note if decision else "",
        "resolved_by": actor.display_name if actor else None,
        "resolved_at": decision.at if decision else None,
    }


@router.get("/reasons")
def reasons(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return [{"key": r.key, "label": r.label} for r in lookup.reasons(db)]


@router.get("/jobs")
def jobs(
    queue: Literal["missed", "scheduled", "history"] = "missed",
    society_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reason_key: str | None = None,
    service: str | None = None,
    unresolved: bool = False,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store=Depends(get_object_store),
):
    if date_from and date_to and date_from > date_to:
        raise ApiError("validation_failed", "The last date must follow the first date.", 422)
    q = (
        select(Job)
        .join(Visit, Visit.id == Job.visit_id)
        .join(Schedule, Schedule.id == Visit.schedule_id)
    )
    if queue == "missed":
        q = q.where(
            Job.status == "Could not complete",
            ~select(OperationsDecision.id).where(OperationsDecision.job_id == Job.id).exists(),
        )
    elif queue == "scheduled":
        q = q.where(Job.status == "Scheduled")
    else:
        q = q.join(OperationsDecision, OperationsDecision.job_id == Job.id)
    if society_id:
        q = q.where(Schedule.society_id == society_id)
    if date_from:
        q = q.where(Visit.date >= date_from)
    if date_to:
        q = q.where(Visit.date <= date_to)
    if reason_key:
        q = q.join(JobOutcome, JobOutcome.job_id == Job.id).where(
            JobOutcome.reason_key == reason_key
        )
    if service:
        q = q.where(Job.service == service)
    if unresolved:
        q = q.where(
            ~select(OperationsDecision.id).where(OperationsDecision.job_id == Job.id).exists(),
            Job.service != "Cleaning-External",
        )
    found = list(db.scalars(q.order_by(Visit.date.desc(), Job.id).limit(500)))
    derived = visit_outcomes(db, {j.visit_id for j in found})
    return [job_out(db, j, store, derived) for j in found]


@router.post("/jobs/{job_id}/resolve")
def resolve(
    job_id: uuid.UUID,
    body: Resolution,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store=Depends(get_object_store),
):
    job = locked_job(db, job_id)
    try:
        if body.action == "Skip":
            skip_job(db, job, body, user.id)
        else:
            reschedule(db, job, body, user.id)
    except ApiError:
        db.rollback()
        raise
    return job_out(db, job, store)


@router.post("/visits/{visit_id}/skip")
def skip_visit(
    visit_id: uuid.UUID,
    body: SkipVisit,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store=Depends(get_object_store),
):
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise ApiError("not_found", "Visit not found.", 404)
    rows = list(db.scalars(select(Job).where(Job.visit_id == visit_id).with_for_update()))
    eligible = [j for j in rows if j.status in ("Scheduled", "Could not complete")]
    if not eligible:
        raise ApiError("job_not_open", "No scheduled or missed jobs remain on this visit.", 409)
    resolution = Resolution(action="Skip", **body.model_dump())
    try:
        for job in eligible:
            skip_job(db, job, resolution, user.id, commit=False)
        db.commit()
    except ApiError:
        db.rollback()
        raise
    for job in eligible:
        emit.job_status_changed(db, job)
    return [job_out(db, j, store) for j in rows]


@router.post("/bulk-skip")
def bulk_skip_visits(
    body: BulkSkip,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """S-12: skip a list of visits, or a society's whole day, in one go."""
    return bulk_skip(db, body, user.id)


# ---- S-12 bulk skip ---------------------------------------------------------------

def _open_jobs(db, visit_id):
    rows = list(db.scalars(select(Job).where(Job.visit_id == visit_id).with_for_update()))
    return rows, [j for j in rows if j.status in ("Scheduled", "Could not complete")]


def bulk_skip(db, body: BulkSkip, actor):
    """Skip the open jobs of many visits in one transaction (S-12). A visit
    with nothing open is counted as ignored. Nothing extends the plan (B-01).
    One audit row per visit and one for the batch."""
    reason = body.reason.strip()
    if body.reason_key:
        reason = reason or lookup.reason_label(db, body.reason_key) or ""
    if not reason:
        raise ApiError("validation_failed", "Give a reason.", 422, {"reason": "Required."})
    by_ids = body.visit_ids is not None
    by_day = body.society_id is not None and body.date is not None
    if by_ids == by_day or (body.visit_ids is not None and not body.visit_ids):
        raise ApiError(
            "validation_failed", "Give visit_ids, or a society_id and a date.", 422)
    if by_ids:
        ids = list(dict.fromkeys(body.visit_ids))
        found = {v.id for v in db.scalars(select(Visit).where(Visit.id.in_(ids)))}
        missing = [str(i) for i in ids if i not in found]
        if missing:
            raise ApiError("not_found", "A visit was not found.", 404, {"visit_ids": missing[0]})
    else:
        ids = list(db.scalars(
            select(Visit.id)
            .join(Schedule, Schedule.id == Visit.schedule_id)
            .where(Schedule.society_id == body.society_id, Visit.date == body.date)
            .order_by(Visit.id)
        ))
    resolution = Resolution(action="Skip", reason=reason, note=body.note)
    skipped, ignored, jobs = [], 0, []
    try:
        for visit_id in ids:
            _rows, eligible = _open_jobs(db, visit_id)
            if not eligible:
                ignored += 1
                continue
            for job in eligible:
                skip_job(db, job, resolution, actor, commit=False)
            jobs.extend(eligible)
            skipped.append(visit_id)
            audit(db, actor, "operations", visit_id, "bulk-skip-visit",
                  {"reason": reason, "note": body.note.strip(), "jobs": len(eligible)})
        if not skipped:
            raise ApiError("job_not_open", "No scheduled or missed jobs remain on these visits.",
                           409)
        audit(db, actor, "operations", "batch", "bulk-skip",
              {"reason": reason, "note": body.note.strip(), "visits": len(skipped),
               "jobs": len(jobs), "ignored": ignored,
               "society_id": str(body.society_id) if body.society_id else None,
               "date": body.date.isoformat() if body.date else None})
        db.commit()
    except ApiError:
        db.rollback()
        raise
    for job in jobs:
        emit.job_status_changed(db, job)
    return {"visits_skipped": len(skipped), "jobs_skipped": len(jobs),
            "visits_ignored": ignored, "visit_ids": [str(v) for v in skipped]}


# ---- S-05 move one service to any date --------------------------------------------

def move_to_date(db, job_id, body: MoveDate, actor):
    """The admin moves one scheduled service to another date (S-05). The
    recurring pattern is untouched. The original job is closed (Skipped, with a
    note) and kept; a linked job (`source_job_id`) on the new date goes through
    the normal planner. The customer calendar shows the new date."""
    reason = body.reason.strip()
    if not reason:
        raise ApiError("validation_failed", "Give a reason.", 422, {"reason": "Required."})
    if body.date < today_ist():
        raise ApiError("date_passed", "Choose today or a later date.", 422, {"date": "Too early."})
    job = locked_job(db, job_id)
    source = db.get(Visit, job.visit_id)
    if job.status != "Scheduled":
        raise ApiError("job_not_open", "Only a scheduled service can be moved.", 409)
    if body.date == source.date:
        raise ApiError("same_date", "The service is already on that date.", 409)
    if db.scalar(select(Job.id).where(Job.source_job_id == job.id)):
        raise ApiError("already_moved", "This service has already been moved.", 409)
    duplicate = db.scalar(
        select(Job.id)
        .join(Visit, Visit.id == Job.visit_id)
        .where(
            Visit.vehicle_id == source.vehicle_id,
            Visit.date == body.date,
            Job.service == job.service,
            Job.status != "Skipped",
        )
    )
    if duplicate:
        raise ApiError("duplicate_service", "That vehicle already has this service that day.", 409)
    previous_crew = job.crew_id
    job.status, job.crew_id, job.start_minute, job.late = "Skipped", None, None, False
    job.note = f"Moved to {body.date.strftime('%d-%b-%y')}."
    db.flush()
    scheduling.refresh_visit_status(db, job.visit_id)
    audit(db, actor, "operations", job.id, "move-date",
          {"reason": reason, "service": job.service, "from": source.date.isoformat(),
           "to": body.date.isoformat()})
    try:
        redo = make_redo(db, job, source, body.date, actor, f"Moved {job.id} to {body.date}")
    except ApiError:
        db.rollback()
        raise
    emit.job_taken_off(db, job, previous_crew)
    return job, redo


# ---- S-09 bulk reassign -----------------------------------------------------------

def bulk_reassign(db, body: BulkReassign, actor):
    """Give many jobs to one crew member in one transaction (S-09). Each keeps
    its start time and goes through `move_job`'s checks. If any job fails,
    nothing changes and the error lists every job with its result."""
    reason = body.reason.strip()
    if not reason:
        raise ApiError("validation_failed", "Give a reason.", 422, {"reason": "Required."})
    by_ids = body.job_ids is not None
    by_day = body.from_crew_id is not None and body.date is not None
    if by_ids == by_day or (body.job_ids is not None and not body.job_ids):
        raise ApiError("validation_failed", "Give job_ids, or from_crew_id and a date.", 422)
    if by_ids:
        ids = list(dict.fromkeys(body.job_ids))
    else:
        ids = list(db.scalars(
            select(Job.id)
            .join(Visit, Visit.id == Job.visit_id)
            .where(Job.crew_id == body.from_crew_id, Visit.date == body.date,
                   Job.status == "Scheduled")
            .order_by(Job.start_minute, Job.id)
        ))
        if not ids:
            raise ApiError("job_not_open", "That crew member has no scheduled jobs that day.", 409)
    target = db.get(SchedulingCrew, body.to_crew_id)
    if target is None or not target.active:
        raise ApiError("crew_not_found", "That crew member was not found.", 404)
    results, failed, moves = [], False, []
    for job_id in ids:
        job = db.get(Job, job_id)
        if job is None:
            results.append({"job_id": str(job_id), "ok": False, "code": "not_found",
                            "message": "Job not found."})
            failed = True
            continue
        previous = job.crew_id
        try:
            if previous == target.id:
                raise ApiError("same_crew", "The job is already with that crew member.", 409)
            scheduling.move_job(db, job_id, target.id, job.start_minute, actor, commit=False)
        except ApiError as e:
            results.append({"job_id": str(job_id), "ok": False, "code": e.code,
                            "message": e.message})
            failed = True
            continue
        db.add(JobReassignment(job_id=job_id, from_crew_id=previous, to_crew_id=target.id,
                               by_login_id=actor))
        moves.append(job)
        results.append({"job_id": str(job_id), "ok": True, "code": "", "message": ""})
    if failed:
        db.rollback()
        raise ApiError("reassign_failed",
                       "Nothing was changed. Fix the jobs that failed and try again.", 409,
                       {r["job_id"]: r["code"] for r in results if not r["ok"]})
    audit(db, actor, "scheduling", "batch", "bulk-reassign",
          {"reason": reason, "to_crew_id": str(target.id), "jobs": [str(j.id) for j in moves]})
    db.commit()
    for job in moves:
        emit.job_reassigned(db, job)
    return {"reassigned": len(moves), "results": results}
