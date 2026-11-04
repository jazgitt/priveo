"""The admin's view of the scheduled jobs: state, last run, history and the on/off
switch (ADM-OPS-05 to ADM-OPS-09). Admin only."""
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.directory.service import audit, invalid
from app.identity.service import User
from app.notifications import cron_log
from app.notifications.cron import JOBS
from app.notifications.models import CronRun
from app.platform.db import get_db, utcnow
from app.platform.deps import require_role
from app.platform.errors import ApiError

router = APIRouter(prefix="/v1/admin/operations/cron", tags=["operations"])

Admin = Annotated[User, Depends(require_role("admin"))]
Db = Annotated[Session, Depends(get_db)]


class CronRunOut(BaseModel):
    id: uuid.UUID
    trigger: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    duration_ms: int | None
    what_it_did: str
    error: str


class CronJobOut(BaseModel):
    job: str
    label: str
    purpose: str
    schedule_utc: str
    schedule_ist: str
    scheduled_on_vercel: bool
    enabled: bool
    status: str
    last_run: CronRunOut | None
    purpose_achieved: bool | None
    purpose_achieved_text: str


class CronSwitch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def _run_out(job: str, run: CronRun, now: datetime) -> CronRunOut:
    return CronRunOut(id=run.id, trigger=run.trigger, started_at=run.started_at,
                      finished_at=run.finished_at, status=cron_log.run_status(run, now),
                      duration_ms=run.duration_ms, what_it_did=cron_log.result_words(job, run),
                      error=run.error)


def _job_out(db: Session, job: str, now: datetime) -> CronJobOut:
    enabled = cron_log.is_enabled(db, job)
    runs = cron_log.last_runs(db, job, 1)
    last = runs[0] if runs else None
    label, purpose = cron_log.LABELS[job]
    cron = cron_log.EXPECTED.get(job)
    utc, ist = cron_log.schedule_texts(cron)
    achieved, achieved_text = cron_log.purpose(job, enabled, db, now)
    return CronJobOut(
        job=job, label=label, purpose=purpose, schedule_utc=utc, schedule_ist=ist,
        scheduled_on_vercel=cron is not None, enabled=enabled,
        status=cron_log.job_status(job, enabled, last, last is not None, now),
        last_run=_run_out(job, last, now) if last else None,
        purpose_achieved=achieved, purpose_achieved_text=achieved_text)


def _known(job: str) -> None:
    if job not in cron_log.DEFAULTS and job not in JOBS:
        raise ApiError("not_found", "There is no such job.", 404)


@router.get("", response_model=list[CronJobOut])
def list_jobs(_: Admin, db: Db):
    now = utcnow()
    return [_job_out(db, job, now) for job in cron_log.DEFAULTS]


@router.get("/{job}/runs", response_model=list[CronRunOut])
def job_runs(job: str, _: Admin, db: Db, limit: Annotated[int, Query(ge=1, le=200)] = 20):
    _known(job)
    now = utcnow()
    return [_run_out(job, r, now) for r in cron_log.last_runs(db, job, limit)]


@router.put("/{job}", response_model=CronJobOut)
def switch_job(job: str, body: CronSwitch, user: Admin, db: Db):
    _known(job)
    if body.enabled and job == "automatic-planning":
        from app.directory import lookup

        if not lookup.setting(db, "schedule.auto_time"):
            raise invalid("enabled", "Set the planning time in Settings before switching this on.")
    before = cron_log.set_enabled(db, job, body.enabled, user.id)
    if before != body.enabled:
        audit(db, user.id, "cron_job", job, "update", {"enabled": [before, body.enabled]})
    db.commit()
    return _job_out(db, job, utcnow())
