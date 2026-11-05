"""The scheduled jobs, as HTTP endpoints for Vercel cron.

Vercel cron calls each path with GET and sends `Authorization: Bearer
$CRON_SECRET`. Every job calls an existing service function and is safe to
run again: a repeat changes nothing and sends nothing twice. Schedules are in
`services/api/vercel.json` (cron times are UTC; IST is UTC+5:30) and are mirrored
in `cron_log.EXPECTED`; a test keeps them equal.

The API runs on Vercel Hobby: each job runs once a day, anywhere inside its
scheduled hour. A job can be switched off by the admin (Scheduled jobs page,
`cron_jobs`); a switched-off job does nothing and answers `skipped`. Every call
is recorded in `cron_runs` and logged on `priveo.cron` (`cron_log`).

`payments-daily` runs at 2:00 IST: it makes the current-cycle payments, then
marks overdue and runs auto-Inactive. The payment day changes at 2:00 IST
(PAY-19). Crew society moves have no job: they apply when the crew data or the
scheduler is read (`apply_due_moves`).

`CRON_SECRET` is environment configuration, never committed. Without it every
call is refused."""
import hmac
import time
from datetime import datetime
from functools import lru_cache

from fastapi import APIRouter, Depends, Header, Request
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from app.billing.config import MoneySettings, get_money_settings
from app.changes.rules import Clock, get_now, payment_day_of, today_of
from app.notifications import cron_log, emit
from app.platform.db import get_db
from app.platform.errors import ApiError

router = APIRouter(prefix="/v1/internal/cron", tags=["cron"], include_in_schema=False)


class CronSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cron_secret: str = ""


@lru_cache
def get_cron_settings() -> CronSettings:
    return CronSettings()


def require_cron_secret(authorization: str | None = Header(default=None),
                        settings: CronSettings = Depends(get_cron_settings)) -> None:
    secret = settings.cron_secret.strip()
    if not secret:
        raise ApiError("cron_disabled", "Scheduled jobs are not set up.", 503)
    given = ""
    if authorization and authorization.lower().startswith("bearer "):
        given = authorization[7:].strip()
    if not hmac.compare_digest(given.encode(), secret.encode()):
        raise ApiError("unauthorized", "Not allowed.", 401)


def _freeze_due(db: Session, now: datetime, settings: MoneySettings) -> dict:
    from app.scheduling import service

    return {"frozen": len(service.freeze_due(db, now))}


def _payments_generate(db: Session, now: datetime, settings: MoneySettings) -> dict:
    from app.billing.service import generate_due_payments

    return {"created": generate_due_payments(now, db, settings, today=payment_day_of(now))}


def _payments_overdue(db: Session, now: datetime, settings: MoneySettings) -> dict:
    from app.billing.service import mark_overdue_and_inactive

    report = mark_overdue_and_inactive(now, db, settings, today=payment_day_of(now))
    return {"marked_overdue": report.marked_overdue, "inactivated": len(report.inactivated)}


def _payments_daily(db: Session, now: datetime, settings: MoneySettings) -> dict:
    """The 2:00 IST job (ADM-PAY-14), in this order: make each Active
    subscription's current-cycle payment (the day after a cycle ends, the next
    one appears), then mark overdue and run auto-Inactive (ADM-SUB-03). The
    reminders go out separately at 10:00 IST (`renewal-reminders`)."""
    return {**_payments_generate(db, now, settings), **_payments_overdue(db, now, settings)}


def _renewal_reminders(db: Session, now: datetime, settings: MoneySettings) -> dict:
    return {"sent": emit.renewal_reminders(db, today_of(now)) or 0}


def _support(db: Session, now: datetime):
    from app.notifications.bridge import SupportNotifier
    from app.support.notify import QueuedEmailNotifier
    from app.support.service import SupportService

    return SupportService(db, SupportNotifier(db), QueuedEmailNotifier(db),
                          now=lambda: now, today=lambda: today_of(now))


def _checkin_notify(db: Session, now: datetime, settings: MoneySettings) -> dict:
    return {"sent": _support(db, now).notify_due_checkins()}


def _complaints_overdue(db: Session, now: datetime, settings: MoneySettings) -> dict:
    from app.support.email_delivery import deliver_pending
    alerted = _support(db, now).alert_overdue_complaints()
    return {"alerted": alerted, "emails_sent": deliver_pending(db, now=now)}


def _automatic_planning(db: Session, now: datetime, settings: MoneySettings) -> dict:
    from app.scheduling.automatic import run_due
    return run_due(db, now)


JOBS = {
    "automatic-planning": _automatic_planning,
    "freeze-due": _freeze_due,
    "payments-daily": _payments_daily,
    "renewal-reminders": _renewal_reminders,
    "checkin-notify": _checkin_notify,
    "complaints-overdue": _complaints_overdue,
}


@router.api_route("/{job}", methods=["GET", "POST"], dependencies=[Depends(require_cron_secret)])
def run_job(job: str, request: Request, db: Session = Depends(get_db), now: Clock = Depends(get_now),
            settings: MoneySettings = Depends(get_money_settings)) -> dict:
    runner = JOBS.get(job)
    if runner is None:
        raise ApiError("not_found", "There is no such job.", 404)
    at = now()
    trigger = "vercel" if request.headers.get("user-agent", "").startswith("vercel-cron") else "manual"
    if not cron_log.is_enabled(db, job):
        cron_log.start_run(db, job, trigger, "skipped", {"skipped": "disabled"})
        cron_log.log_line(job, trigger, "skipped", 0, {"skipped": "disabled"})
        return {"job": job, "ran_at": at.isoformat(), "skipped": "disabled"}
    run_id = cron_log.start_run(db, job, trigger)
    began = time.monotonic()
    try:
        result = runner(db, at, settings)
    except BaseException as exc:
        ms = int((time.monotonic() - began) * 1000)
        error = cron_log.error_text(exc)
        cron_log.finish_run(db, run_id, "failed", ms, error=error)
        cron_log.log_line(job, trigger, "failed", ms, None, error)
        raise
    ms = int((time.monotonic() - began) * 1000)
    cron_log.finish_run(db, run_id, "success", ms, result)
    cron_log.log_line(job, trigger, "success", ms, result)
    if job == "payments-daily":
        cron_log.prune(db, at)
    return {"job": job, "ran_at": at.isoformat(), "result": result}
