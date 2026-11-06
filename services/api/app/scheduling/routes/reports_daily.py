"""SCHS-26: the daily cleaner view (SCHR-OUT-01). Read only. Break, free slots
and the cross-zone reason stay null until the stories that produce them land."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.scheduling import service
from app.scheduling.models import Job, Schedule, ScheduleFinding, Visit
from app.scheduling.outcomes import SHORT_NAME

router = APIRouter(prefix="/v1/admin/scheduling/reports", tags=["scheduling"])


class DailyException(BaseModel):
    code: str
    detail: str = ""


class DailyJob(BaseModel):
    job_id: uuid.UUID
    vehicle_id: uuid.UUID
    registration: str
    zone: str
    type: str
    start_time: str
    end_time: str
    cutoff: str
    exceptions: list[DailyException]
    cross_zone_reason: str | None = None


class DailyCleaner(BaseModel):
    cleaner_id: uuid.UUID
    name: str
    break_window: dict | None = None
    free_slots: list[dict] | None = None
    jobs: list[DailyJob]


class DailyView(BaseModel):
    society_id: uuid.UUID
    date: date
    cleaners: list[DailyCleaner]


@router.get("/daily", response_model=DailyView)
def daily_cleaner_view(
    society_id: uuid.UUID,
    date: date,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = service.job_rows(
        db,
        Schedule.society_id == society_id,
        Visit.date == date,
        Job.crew_id.is_not(None),
        Job.status != "Skipped",
    )
    findings: dict[uuid.UUID, list[DailyException]] = {}
    if rows:
        for f in db.scalars(select(ScheduleFinding).where(
                ScheduleFinding.job_id.in_([r["id"] for r in rows]))):
            findings.setdefault(f.job_id, []).append(DailyException(code=f.code, detail=f.detail))
    reasons = dict(db.execute(select(Job.id, Job.cross_zone_reason).where(
        Job.id.in_([r["id"] for r in rows]))).all()) if rows else {}
    cleaners: dict[uuid.UUID, DailyCleaner] = {}
    for r in rows:
        cleaner = cleaners.setdefault(r["crew_id"], DailyCleaner(
            cleaner_id=r["crew_id"], name=r["crew_name"] or "", jobs=[]))
        cleaner.jobs.append(DailyJob(
            job_id=r["id"], vehicle_id=r["vehicle_id"], registration=r["registration"],
            zone=r["zone"], type=SHORT_NAME.get(r["service"], r["service"]),
            start_time=r["start_time"], end_time=r["end_time"], cutoff=r["finish_by"],
            exceptions=findings.get(r["id"], []), cross_zone_reason=reasons.get(r["id"])))
    return DailyView(society_id=society_id, date=date, cleaners=list(cleaners.values()))
