"""Atomic swaps, preview-only suggestions and cutoff-request resolution."""

import hashlib
import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.models import ScheduleChange
from app.customers.administration import audit
from app.customers.models import Customer, Vehicle
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import service
from app.scheduling.models import Job, Schedule, Visit
from app.scheduling.solver import SolverJob, solve_day

router = APIRouter(prefix="/v1/admin/scheduling", tags=["scheduling"])


class SwapIn(BaseModel):
    first_job_id: uuid.UUID
    second_job_id: uuid.UUID


class SuggestionApply(BaseModel):
    fingerprint: str
    job_ids: list[uuid.UUID]


class ResolveCutoff(BaseModel):
    apply: bool


def stamp(rows):
    payload = sorted(
        (
            str(j.id),
            str(j.crew_id),
            j.start_minute,
            j.status,
            j.finish_by_minute,
            j.duration_minutes,
            j.manual,
        )
        for j, _ in rows
    )
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()


def draft(db, schedule_id):
    s = service.get_schedule(db, schedule_id)
    if s.status == "Frozen":
        raise ApiError("schedule_frozen", "Unfreeze the schedule to make changes.", 409)
    return s


@router.post("/jobs/swap")
def swap_jobs(
    body: SwapIn, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    first, second = db.get(Job, body.first_job_id), db.get(Job, body.second_job_id)
    if first is None or second is None:
        raise ApiError("not_found", "Job not found.", 404)
    v1, v2 = db.get(Visit, first.visit_id), db.get(Visit, second.visit_id)
    if first.id == second.id or v1.schedule_id != v2.schedule_id or v1.date != v2.date:
        raise ApiError("validation_failed", "Choose two jobs in the same schedule and day.", 422)
    draft(db, v1.schedule_id)
    if any(
        j.status != "Scheduled" or j.crew_id is None or j.start_minute is None
        for j in (first, second)
    ):
        raise ApiError("job_not_open", "Both jobs must be assigned and not started.", 409)
    placements = [
        (first.id, second.crew_id, second.start_minute),
        (second.id, first.crew_id, first.start_minute),
    ]
    first.crew_id, first.start_minute = None, None
    second.crew_id, second.start_minute = None, None
    db.flush()
    try:
        for job_id, crew_id, start in placements:
            service.move_job(db, job_id, crew_id, start, user.id, commit=False)
        service.record(db, v1.schedule_id, user.id, "swap", f"{first.id} with {second.id}")
        db.commit()
    except ApiError:
        db.rollback()
        raise
    return {"swapped": True}


def preview(db, schedule):
    rows = service._jobs_of(db, schedule.id)
    crew = service.load_crew(db, schedule.society_id)
    suggestions = []
    for day in service.daterange(schedule.start_date, schedule.end_date):
        windows = service.availability(db, crew, [day])[day]
        jobs = []
        for job, visit in rows:
            if visit.date != day or job.status == "Skipped":
                continue
            fixed = (
                (
                    service.crew_key_for(
                        job.crew_id, job.start_minute or 0, windows.get(job.crew_id)),
                    job.start_minute or 0,
                )
                if job.crew_id and (job.manual or job.status != "Scheduled")
                else None
            )
            jobs.append(
                SolverJob(
                    str(job.id),
                    str(visit.vehicle_id),
                    job.duration_minutes,
                    job.finish_by_minute,
                    fixed,
                    tuple(
                        (start, min(end, job.finish_by_minute))
                        for start, end in service.service_windows(
                            db, schedule.society_id, job.service, day
                        )
                    )
                    if job.addon_booking_id or job.addon_request_id
                    else service.service_windows(db, schedule.society_id, job.service, day),
                )
            )
        result = solve_day(service.solver_crews(windows), jobs)
        for job, visit in rows:
            proposed = result.placed.get(str(job.id))
            if proposed:
                proposed = (str(service.base_crew(proposed[0])), proposed[1])
            if (
                proposed
                and job.status == "Scheduled"
                and visit.date == day
                and (proposed != (str(job.crew_id), job.start_minute))
            ):
                suggestions.append(
                    {
                        "job_id": str(job.id),
                        "crew_id": proposed[0],
                        "start_minute": proposed[1],
                        "date": day,
                        "service": job.service,
                        "old_start_minute": job.start_minute,
                    }
                )
    return {"fingerprint": stamp(rows), "items": suggestions}


@router.get("/schedules/{schedule_id}/suggestions")
def suggestions(
    schedule_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return preview(db, draft(db, schedule_id))


@router.post("/schedules/{schedule_id}/suggestions/apply")
def apply_suggestions(
    schedule_id: uuid.UUID,
    body: SuggestionApply,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    result = preview(db, draft(db, schedule_id))
    if result["fingerprint"] != body.fingerprint:
        raise ApiError("stale_suggestions", "The schedule changed. Preview again.", 409)
    proposed = {i["job_id"]: i for i in result["items"]}
    selected = list(dict.fromkeys(str(i) for i in body.job_ids))
    if not selected or any(i not in proposed for i in selected):
        raise ApiError("validation_failed", "Choose current suggestions.", 422)
    for job_id in selected:
        job = db.get(Job, uuid.UUID(job_id))
        job.crew_id, job.start_minute = None, None
    db.flush()
    try:
        for job_id in selected:
            item = proposed[job_id]
            service.move_job(
                db,
                uuid.UUID(job_id),
                uuid.UUID(item["crew_id"]),
                item["start_minute"],
                user.id,
                commit=False,
            )
        service.record(db, schedule_id, user.id, "suggestions", f"Applied {len(selected)}")
        db.commit()
    except ApiError:
        db.rollback()
        raise
    return {"applied": len(selected)}


@router.get("/cutoff-requests")
def cutoff_requests(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    result = []
    for c in db.scalars(
        select(ScheduleChange)
        .where(ScheduleChange.kind == "cutoff", ScheduleChange.status == "Requested")
        .order_by(ScheduleChange.created_at)
    ):
        v = db.get(Vehicle, c.vehicle_id)
        owner = db.get(Customer, c.customer_id)
        assignment = next(
            (
                r
                for r in service.job_rows(
                    db,
                    Visit.vehicle_id == c.vehicle_id,
                    Visit.date == c.start_date,
                    Visit.addon_key == "",
                )
                if r["crew_id"]
            ),
            None,
        )
        result.append(
            {
                "id": str(c.id),
                "vehicle_id": str(c.vehicle_id),
                "date": c.start_date,
                "cutoff_time": c.cutoff_time.strftime("%H:%M"),
                "registration": v.registration,
                "customer_name": f"{owner.first_name} {owner.last_name}",
                "old_cutoff": assignment["finish_by"] if assignment else None,
                "crew_name": assignment["crew_name"] if assignment else None,
                "start_time": assignment["start_time"] if assignment else None,
            }
        )
    return result


@router.post("/cutoff-requests/{request_id}/handle")
def handle_cutoff(
    request_id: uuid.UUID,
    body: ResolveCutoff,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    change = db.get(ScheduleChange, request_id)
    if change is None or change.kind != "cutoff" or change.status != "Requested":
        raise ApiError("not_found", "Request not found.", 404)
    rows = list(
        db.execute(
            select(Visit, Schedule)
            .join(Schedule, Schedule.id == Visit.schedule_id)
            .where(
                Visit.vehicle_id == change.vehicle_id,
                Visit.date == change.start_date,
                Visit.addon_key == "",
            )
        )
    )
    if body.apply and any(s.status == "Frozen" for _, s in rows):
        raise ApiError("schedule_frozen", "Unfreeze the schedule before applying the cutoff.", 409)
    change.status = "Applied" if body.apply else "Rejected"
    audit(db, user.id, "cutoff_request", change.id, "resolve", {"apply": body.apply})
    db.commit()
    if body.apply:
        service.reconcile_vehicle(db, change.vehicle_id)
    return {"handled": True}
