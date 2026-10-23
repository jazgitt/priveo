import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.identity.service import User
from app.platform.clock import now_ist, today_ist
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import queue, service
from app.scheduling.models import Job, Schedule
from app.scheduling.schemas import (
    AdminJob,
    Board,
    CrewDay,
    CustomerNextService,
    DayCapacity,
    FreezeDue,
    MoveRequest,
    NeedsScheduling,
    QueueChange,
    QueueReorder,
    QueueUnlock,
    RunRequest,
    RunResponse,
    RunResult,
    ScheduleOut,
    UnfreezeRequest,
)

customer = APIRouter(prefix="/v1/customer", tags=["scheduling"])
crew = APIRouter(prefix="/v1/crew", tags=["scheduling"])
admin = APIRouter(prefix="/v1/admin/scheduling", tags=["scheduling"])


class AutomaticPlanningSettings(BaseModel):
    enabled: bool = False
    time_ist: str = ""


@admin.get("/automatic-planning", response_model=AutomaticPlanningSettings)
def automatic_settings(_: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    from app.directory import lookup
    return AutomaticPlanningSettings(enabled=bool(lookup.setting(db, "schedule.auto_enabled")),
                                      time_ist=lookup.setting(db, "schedule.auto_time"))


@admin.put("/automatic-planning", response_model=AutomaticPlanningSettings)
def save_automatic_settings(body: AutomaticPlanningSettings,
                            user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    from app.directory.service import save_settings
    save_settings(db, user.id, {"schedule.auto_enabled": int(body.enabled),
                               "schedule.auto_time": body.time_ist})
    return automatic_settings(user, db)


@customer.get("/next-job", response_model=CustomerNextService)
def next_service(
    from_date: date | None = None,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    row = service.customer_next_job(db, user.id, from_date or today_ist())
    if row is None:
        return {"job": None}
    return {
        "job": {
            "job_id": row["id"],
            "visit_id": row["visit_id"],
            "vehicle_id": row["vehicle_id"],
            "registration": row["registration"],
            "vehicle": row["vehicle"],
            "date": row["date"],
            "service": row["service"],
            "status": row["status"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "crew_name": row["crew_name"],
            "finish_by": row["finish_by"],
        }
    }


@crew.get("/day", response_model=CrewDay)
def crew_day(date: date, user: User = Depends(require_role("crew")), db: Session = Depends(get_db)):
    # No customer name or mobile number in a crew response (CRW-SCH-13).
    return service.crew_day(db, user.id, date)


@admin.post("/run", response_model=RunResponse)
def run(
    body: RunRequest, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    done = service.run(db, body.society_id, body.start_date, body.days, user.id)
    return {"schedules": [RunResult(**vars(s)) for s in done]}


@admin.get("/schedules", response_model=list[ScheduleOut])
def schedules(
    society_id: uuid.UUID,
    date_from: date | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """The society's schedules that end on or after `date_from`, oldest first (ADM-SCH-35)."""
    return service.schedules_of(db, society_id, date_from)


@admin.get("/board", response_model=Board)
def board(
    schedule_id: uuid.UUID | None = None,
    society_id: uuid.UUID | None = None,
    start_date: date | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if schedule_id is not None:
        schedule = service.get_schedule(db, schedule_id)
    elif society_id is not None and start_date is not None:
        schedule = db.execute(
            select(Schedule).where(
                Schedule.society_id == society_id, Schedule.start_date == start_date
            )
        ).scalar_one_or_none()
        if schedule is None:
            raise ApiError("not_found", "No schedule has been run for that week.", 404)
    else:
        raise ApiError(
            "validation_failed", "Give a schedule_id, or a society_id and start_date.", 422
        )
    return service.board(db, schedule)


@admin.post("/jobs/{job_id}/move", response_model=AdminJob)
def move_job(
    job_id: uuid.UUID,
    body: MoveRequest,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    job = service.move_job(db, job_id, body.crew_id, body.start_minute, user.id)
    rows = service.job_rows(db, Job.id == job.id)
    return rows[0]


@admin.post("/queue/reorder", response_model=QueueChange)
def reorder_queue(
    body: QueueReorder, user: User = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    """S-13, B-06: the admin reorders one crew member's day. A reason is
    required; the change is audited and the crew member is told."""
    ids = queue.reorder(db, user.id, body.crew_id, body.date, body.ordered_job_ids, body.reason)
    return {"message": "The queue was reordered and the crew member was told.",
            "ordered_job_ids": ids}


@admin.post("/jobs/{job_id}/unlock", response_model=QueueChange)
def unlock_job(
    job_id: uuid.UUID,
    body: QueueUnlock,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """C-04: lets the crew action one job out of turn. A reason is required."""
    job = queue.unlock(db, user.id, job_id, body.reason)
    return {"message": "The job was unlocked and the crew member was told.",
            "ordered_job_ids": [job.id]}


@admin.post("/schedules/{schedule_id}/freeze", response_model=ScheduleOut)
def freeze(
    schedule_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    schedule = service.freeze(db, service.get_schedule(db, schedule_id), user.id)
    return service.board(db, schedule)["schedule"]


@admin.post("/schedules/{schedule_id}/unfreeze", response_model=ScheduleOut)
def unfreeze(
    schedule_id: uuid.UUID,
    body: UnfreezeRequest,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    schedule = service.unfreeze(db, service.get_schedule(db, schedule_id), body.code, user.id)
    return service.board(db, schedule)["schedule"]


@admin.post("/freeze-due", response_model=FreezeDue)
def freeze_due(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return {"frozen": service.freeze_due(db, now_ist())}


@admin.get("/skipped", response_model=list[AdminJob])
def skipped(
    society_id: uuid.UUID,
    date_from: date,
    date_to: date,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Skipped and paused jobs of a society between two dates (ADM-SCH-36)."""
    if date_to < date_from:
        raise ApiError("validation_failed", "The end date is before the start date.", 422,
                       {"date_to": "Must be on or after date_from."})
    return service.skipped_jobs(db, society_id, date_from, date_to)


@admin.get("/needs-scheduling", response_model=NeedsScheduling)
def needs_scheduling(
    society_id: uuid.UUID | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from app.addons.models import AddonBooking
    from app.customers.models import Customer, Vehicle
    query = select(AddonBooking, Vehicle).join(Vehicle, Vehicle.id == AddonBooking.vehicle_id)
    query = query.join(Customer, Customer.id == Vehicle.customer_id).where(
        AddonBooking.status == "Requested", AddonBooking.proposed_date >= today_ist(),
        ~select(Job.id).where(Job.addon_booking_id == AddonBooking.id,
                              Job.status == "Scheduled").exists())
    if society_id:
        query = query.where(func.coalesce(Vehicle.society_id, Customer.society_id) == society_id)
    return {"jobs": service.needs_scheduling(db, society_id), "pending_addons": [
        {"id": str(b.id), "date": b.proposed_date, "registration": v.registration,
         "finish_by": b.finish_by.strftime("%H:%M"), "service": b.service}
        for b, v in db.execute(query)]}


@admin.get("/capacity", response_model=list[DayCapacity])
def capacity(
    society_id: uuid.UUID,
    start_date: date,
    days: int = Query(default=7, ge=1, le=31),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    end = date.fromordinal(start_date.toordinal() + days - 1)
    return service.capacity(db, society_id, start_date, end)
