"""The daily and hourly jobs, as HTTP endpoints for Vercel cron on dev.

Vercel cron calls each path with GET and sends `Authorization: Bearer
$CRON_SECRET`. Every job calls an existing service function and is safe to
run again: a repeat changes nothing and sends nothing twice.

Add this to `services/api/vercel.json` (the file is the coordinator's). Cron
times are UTC. IST is UTC+5:30, so `35 14` is 20:05 IST, just after the 8 PM
freeze cutoff time (ADM-SCH-25):

    "crons": [
      {"path": "/v1/internal/cron/freeze-due",          "schedule": "35 14 * * *"},
      {"path": "/v1/internal/cron/payments-daily",      "schedule": "30 20 * * *"},
      {"path": "/v1/internal/cron/renewal-reminders",   "schedule": "30 4 * * *"},
      {"path": "/v1/internal/cron/checkin-notify",      "schedule": "0 5 * * *"},
      {"path": "/v1/internal/cron/complaints-overdue",  "schedule": "30 15 * * *"}
    ]

`payments-daily` runs at 2:00 IST (20:30 UTC): it makes the current-cycle
payments, then marks overdue and runs auto-Inactive. The payment day changes at
2:00 IST (PAY-19). The old `payments-generate` and `payments-overdue` names still
answer a manual call. `renewal-reminders` stays at 10:00 IST (04:30 UTC) so no
push arrives at 2 AM.

Automatic planning and complaint escalation temporarily run daily at 21:00 IST
(15:30 UTC) for Vercel Hobby compatibility. Overdue complaints and pending alert
email retries are processed on that daily invocation. Hobby invocation timing
can vary within the scheduled hour. Planning still respects its admin settings.

`CRON_SECRET` is environment configuration, never committed. Without it every
call is refused."""
import hmac
from datetime import datetime, timedelta
from functools import lru_cache

from fastapi import APIRouter, Depends, Header
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from app.billing.config import MoneySettings, get_money_settings
from app.changes.rules import PAYMENT_DAY_START_HOUR, Clock, get_now, today_of
from app.notifications import emit
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


def _payment_clock(now: datetime) -> datetime:
    """The moment the payment jobs use: the payment day changes at 2:00 IST
    (PAY-19), so the services see the time two hours earlier and work out the
    right day. At 02:00 IST on 5 Nov they see 5 Nov 00:00, at 01:59 4 Nov 23:59."""
    return now - timedelta(hours=PAYMENT_DAY_START_HOUR)


def _payments_generate(db: Session, now: datetime, settings: MoneySettings) -> dict:
    from app.billing.service import generate_due_payments

    return {"created": generate_due_payments(_payment_clock(now), db, settings)}


def _payments_overdue(db: Session, now: datetime, settings: MoneySettings) -> dict:
    from app.billing.service import mark_overdue_and_inactive

    report = mark_overdue_and_inactive(_payment_clock(now), db, settings)
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


def _crew_society_moves(db: Session, now: datetime, settings: MoneySettings) -> dict:
    from app.changes.rules import today_of
    from app.crew.society_moves import apply_due_moves
    return {"applied": apply_due_moves(db, today_of(now))}


JOBS = {
    "crew-society-moves": _crew_society_moves,
    "automatic-planning": _automatic_planning,
    "freeze-due": _freeze_due,
    "payments-daily": _payments_daily,
    # Older names, kept so manual calls still work. Not scheduled any more.
    "payments-generate": _payments_generate,
    "payments-overdue": _payments_overdue,
    "renewal-reminders": _renewal_reminders,
    "checkin-notify": _checkin_notify,
    "complaints-overdue": _complaints_overdue,
}


@router.api_route("/{job}", methods=["GET", "POST"], dependencies=[Depends(require_cron_secret)])
def run_job(job: str, db: Session = Depends(get_db), now: Clock = Depends(get_now),
            settings: MoneySettings = Depends(get_money_settings)) -> dict:
    runner = JOBS.get(job)
    if runner is None:
        raise ApiError("not_found", "There is no such job.", 404)
    at = now()
    return {"job": job, "ran_at": at.isoformat(), "result": runner(db, at, settings)}
