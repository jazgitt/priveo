"""Operations outcomes preserve original jobs, failure notes and proof."""

import uuid
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.changes.extension import extend_for_skipped_job
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
from app.visits.models import JobOutcome, OperationsDecision

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["Skip", "Reschedule"]
    reason: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=2000)


class SkipVisit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=2000)


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
    extend_for_skipped_job(db, job, actor)
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


def reschedule(db, job, body, actor):
    if not decide(db, job, body, actor):
        return job
    source = db.get(Visit, job.visit_id)
    target_date = source.date + timedelta(days=1)
    if target_date < today_ist():
        raise ApiError(
            "retry_date_passed", "The next-day retry date has passed. Skip the job instead.", 409
        )
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
    scheduling.record(db, target.id, actor, "redo", f"Next-day retry for {job.id}")
    # The scheduler keeps frozen placements and includes explicit retry jobs.
    scheduling.run_schedule(db, target, actor)
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
