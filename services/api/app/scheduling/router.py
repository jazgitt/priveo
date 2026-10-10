import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.service import User
from app.platform.clock import now_ist, today_ist
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import service
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
    RunRequest,
    RunResponse,
    RunResult,
    ScheduleOut,
    UnfreezeRequest,
)

customer = APIRouter(prefix="/v1/customer", tags=["scheduling"])
crew = APIRouter(prefix="/v1/crew", tags=["scheduling"])
admin = APIRouter(prefix="/v1/admin/scheduling", tags=["scheduling"])


@customer.get("/next-service", response_model=CustomerNextService)
def next_service(from_date: date | None = None,
                 user: User = Depends(require_role("customer")),
                 db: Session = Depends(get_db)):
    row = service.customer_next_job(db, user.id, from_date or today_ist())
    if row is None:
        return {"job": None}
    return {"job": {
        "job_id": row["id"], "visit_id": row["visit_id"], "vehicle_id": row["vehicle_id"],
        "registration": row["registration"], "vehicle": row["vehicle"], "date": row["date"],
        "service": row["service"], "status": row["status"], "start_time": row["start_time"],
        "end_time": row["end_time"], "crew_name": row["crew_name"],
        "finish_by": row["finish_by"],
    }}


@crew.get("/day", response_model=CrewDay)
def crew_day(date: date,
             user: User = Depends(require_role("crew")),
             db: Session = Depends(get_db)):
    # No customer name or mobile number in a crew response (CRW-SCH-13).
    return service.crew_day(db, user.id, date)


@admin.post("/run", response_model=RunResponse)
def run(body: RunRequest, user: User = Depends(require_role("admin")),
        db: Session = Depends(get_db)):
    done = service.run(db, body.society_id, body.start_date, body.days, user.id)
    return {"schedules": [RunResult(**vars(s)) for s in done]}


@admin.get("/board", response_model=Board)
def board(schedule_id: uuid.UUID | None = None, society_id: uuid.UUID | None = None,
          start_date: date | None = None, user: User = Depends(require_role("admin")),
          db: Session = Depends(get_db)):
    if schedule_id is not None:
        schedule = service.get_schedule(db, schedule_id)
    elif society_id is not None and start_date is not None:
        schedule = db.execute(select(Schedule).where(
            Schedule.society_id == society_id, Schedule.start_date == start_date)
        ).scalar_one_or_none()
        if schedule is None:
            raise ApiError("not_found", "No schedule has been run for that week.", 404)
    else:
        raise ApiError("validation_failed", "Give a schedule_id, or a society_id and start_date.",
                       422)
    return service.board(db, schedule)


@admin.post("/jobs/{job_id}/move", response_model=AdminJob)
def move_job(job_id: uuid.UUID, body: MoveRequest,
             user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    job = service.move_job(db, job_id, body.crew_id, body.start_minute, user.id)
    rows = service.job_rows(db, Job.id == job.id)
    return rows[0]


@admin.post("/schedules/{schedule_id}/freeze", response_model=ScheduleOut)
def freeze(schedule_id: uuid.UUID, user: User = Depends(require_role("admin")),
           db: Session = Depends(get_db)):
    schedule = service.freeze(db, service.get_schedule(db, schedule_id), user.id)
    return service.board(db, schedule)["schedule"]


@admin.post("/schedules/{schedule_id}/unfreeze", response_model=ScheduleOut)
def unfreeze(schedule_id: uuid.UUID, body: UnfreezeRequest,
             user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    schedule = service.unfreeze(db, service.get_schedule(db, schedule_id), body.code, user.id)
    return service.board(db, schedule)["schedule"]


@admin.post("/freeze-due", response_model=FreezeDue)
def freeze_due(user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return {"frozen": service.freeze_due(db, now_ist())}


@admin.get("/needs-scheduling", response_model=NeedsScheduling)
def needs_scheduling(society_id: uuid.UUID | None = None,
                     user: User = Depends(require_role("admin")),
                     db: Session = Depends(get_db)):
    return {"jobs": service.needs_scheduling(db, society_id)}


@admin.get("/capacity", response_model=list[DayCapacity])
def capacity(society_id: uuid.UUID, start_date: date,
             days: int = Query(default=7, ge=1, le=31),
             user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    end = date.fromordinal(start_date.toordinal() + days - 1)
    return service.capacity(db, society_id, start_date, end)
