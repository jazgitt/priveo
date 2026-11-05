# ruff: noqa: E501
"""The scheduled-job registry, the run recorder and the read-side rules
(ADM-OPS-05 to ADM-OPS-09).

Every call of a job is recorded in `cron_runs` through its own short session, so a
recorder fault never breaks a job. Statuses such as Late or Timed out are worked
out on read, not stored."""
import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.notifications.models import CronJob, CronRun
from app.platform.db import utcnow

log = logging.getLogger("priveo.cron")

# Every job is on or off here until the admin changes it (owner, 05-Nov-26).
DEFAULTS: dict[str, bool] = {
    "complaints-overdue": True,
    "payments-daily": True,
    "freeze-due": False,
    "automatic-planning": False,
    "renewal-reminders": False,
    "checkin-notify": False,
    "mani-retention": False,
}

# The schedule Vercel runs, as in services/api/vercel.json (a test keeps them equal).
EXPECTED: dict[str, str] = {
    "automatic-planning": "30 15 * * *",
    "freeze-due": "35 14 * * *",
    "payments-daily": "30 20 * * *",
    "renewal-reminders": "30 4 * * *",
    "checkin-notify": "0 5 * * *",
    "complaints-overdue": "30 15 * * *",
}

LABELS: dict[str, tuple[str, str]] = {
    "complaints-overdue": ("Overdue complaints",
                           "Alerts the admin about complaints still Raised after 4 hours and sends the queued alert emails."),
    "payments-daily": ("Daily payments",
                       "Makes each Active subscription's current-cycle payment, marks late payments Over due and makes a subscription Inactive after 7 days over due."),
    "freeze-due": ("Freeze schedules",
                   "Freezes Draft schedules once the freeze cutoff time has passed and tells the crew."),
    "automatic-planning": ("Automatic planning",
                           "Makes the next schedule draft for each active society at the planning time."),
    "renewal-reminders": ("Renewal reminders",
                          "Sends the renewal reminder 7 and 1 days before, on, and 1 and 7 days after the due date."),
    "checkin-notify": ("Check-in reminders",
                       "Sends the monthly check-in 4 days before renewal."),
    "mani-retention": ("Mani clean-up",
                       "Deletes old Mani chats and old action audit rows. Not scheduled on Vercel."),
}

GRACE = timedelta(minutes=70)  # Vercel Hobby may fire anywhere in the scheduled hour
TIMED_OUT_AFTER = timedelta(minutes=6)
KEEP_DAYS = 90


# ---- the switch ---------------------------------------------------------------

def is_enabled(db: Session, job: str) -> bool:
    row = db.get(CronJob, job)
    return row.enabled if row is not None else DEFAULTS.get(job, False)


def set_enabled(db: Session, job: str, enabled: bool, login_id: uuid.UUID | None) -> bool:
    """Returns the previous value. The caller commits."""
    before = is_enabled(db, job)
    row = db.get(CronJob, job)
    if row is None:
        row = CronJob(job=job, enabled=enabled)
        db.add(row)
    row.enabled = enabled
    row.updated_by_login_id = login_id
    row.updated_at = utcnow()
    return before


# ---- the recorder -------------------------------------------------------------

def _warn(what: str, exc: Exception) -> None:
    log.warning("cron recorder could not %s: %s", what, type(exc).__name__)


def start_run(db: Session, job: str, trigger: str, status: str = "started",
              result: dict | None = None) -> uuid.UUID | None:
    """Inserts the row in its own session and commits. None if it could not."""
    try:
        with Session(db.get_bind(), expire_on_commit=False) as s:
            now = utcnow()
            run = CronRun(job=job, trigger=trigger, started_at=now, status=status, result=result)
            if status != "started":
                run.finished_at, run.duration_ms = now, 0
            s.add(run)
            s.commit()
            return run.id
    except Exception as exc:
        _warn("start a run", exc)
        return None


def finish_run(db: Session, run_id: uuid.UUID | None, status: str, duration_ms: int,
               result: dict | None = None, error: str = "") -> None:
    if run_id is None:
        return
    try:
        with Session(db.get_bind(), expire_on_commit=False) as s:
            run = s.get(CronRun, run_id)
            if run is not None:
                run.status, run.duration_ms, run.finished_at = status, duration_ms, utcnow()
                run.result, run.error = result, error[:300]
                s.commit()
    except Exception as exc:
        _warn("finish a run", exc)


def error_text(exc: BaseException) -> str:
    """The exception class and a short message, never the stack."""
    text = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {text}"[:300] if text else type(exc).__name__


def log_line(job: str, trigger: str, status: str, duration_ms: int, result: dict | None,
             error: str = "") -> None:
    line = (f"cron job={job} trigger={trigger} status={status} duration_ms={duration_ms} "
            f"result={json.dumps(result, default=str, separators=(',', ':'))}")
    if error:
        line += f" error={error}"
    log.log(logging.ERROR if status == "failed" else logging.INFO, line)


def prune(db: Session, now: datetime | None = None) -> int:
    """Deletes run rows older than 90 days. Never raises."""
    try:
        cutoff = (now or utcnow()) - timedelta(days=KEEP_DAYS)
        with Session(db.get_bind(), expire_on_commit=False) as s:
            n = s.execute(delete(CronRun).where(CronRun.started_at < cutoff)).rowcount
            s.commit()
            return n or 0
    except Exception as exc:
        _warn("prune old runs", exc)
        return 0


def configure_logging() -> None:
    """INFO lines of `priveo.cron` reach stdout; the rest of the app is unchanged."""
    import sys

    if any(getattr(h, "_priveo_cron", False) for h in log.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler._priveo_cron = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


# ---- reading ------------------------------------------------------------------

def expected_last(cron: str, now: datetime) -> datetime:
    """The latest scheduled time at or before `now` for a daily 'M H * * *' cron (UTC)."""
    minute, hour = (int(x) for x in cron.split()[:2])
    at = now.astimezone(UTC).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return at - timedelta(days=1) if at > now else at


def schedule_texts(cron: str | None) -> tuple[str, str]:
    from app.platform.clock import IST

    if not cron:
        return "Not scheduled", "Not scheduled"
    minute, hour = (int(x) for x in cron.split()[:2])
    base = datetime(2026, 1, 1, hour, minute, tzinfo=UTC)
    ist = base.astimezone(IST)
    day = " (next day)" if ist.date() != base.date() else ""
    return f"Daily at {hour:02d}:{minute:02d} UTC", f"Daily at {ist:%H:%M} IST{day}"


def _zero(result: dict | None) -> bool:
    nums = [v for v in (result or {}).values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return not any(nums) and not any(v is True for v in (result or {}).values())


def run_status(run: CronRun | None, now: datetime) -> str:
    if run is None:
        return "Never run"
    if run.status == "started":
        return "Timed out" if now - run.started_at > TIMED_OUT_AFTER else "Running"
    if run.status == "failed":
        return "Failed"
    if run.status == "skipped":
        return "Skipped"
    return "Did nothing" if _zero(run.result) else "Success"


def job_status(job: str, enabled: bool, last: CronRun | None, any_run: bool, now: datetime) -> str:
    """The status chip for a job. A disabled job is Disabled and never Late."""
    if not enabled:
        return "Disabled"
    cron = EXPECTED.get(job)
    if last is None:
        return "Never run"
    if cron and any_run:
        due = expected_last(cron, now)
        if now > due + GRACE and last.started_at < due:
            return "Late"
    return run_status(last, now)


def result_words(job: str, run: CronRun | None) -> str:
    if run is None:
        return ""
    if run.status == "skipped":
        return "Switched off, so it did nothing."
    if run.status == "failed":
        return "The job failed."
    if run.status == "started":
        return "Started, no result yet."
    r = run.result or {}
    n = lambda k: int(r.get(k) or 0)  # noqa: E731
    if job == "payments-daily":
        return (f"Made {n('created')} payments, marked {n('marked_overdue')} over due, "
                f"made {n('inactivated')} subscriptions Inactive.")
    if job == "freeze-due":
        return f"Froze {n('frozen')} schedules."
    if job == "renewal-reminders":
        return f"Sent {n('sent')} renewal reminders."
    if job == "checkin-notify":
        return f"Sent {n('sent')} check-in reminders."
    if job == "complaints-overdue":
        return f"Alerted {n('alerted')} overdue complaints, sent {n('emails_sent')} emails."
    if job == "automatic-planning":
        if r.get("not_due"):
            return "Not time yet, so it planned nothing."
        return f"Planned {n('planned')} schedules, {n('errors')} errors."
    parts = [f"{k.replace('_', ' ')} {v}" for k, v in r.items() if isinstance(v, int)]
    return ", ".join(parts).capitalize() + "." if parts else "Done."


def purpose(job: str, enabled: bool, db: Session, now: datetime) -> tuple[bool | None, str]:
    """Whether the job's purpose is met right now, from live counts.
    (None, text) means it is not checked."""
    if not enabled:
        return None, "Off"
    from app.changes.rules import payment_day_of
    from app.support.models import Complaint

    if job == "payments-daily":
        from app.billing.models import Payment

        late = db.scalar(select(func.count()).select_from(Payment).where(
            Payment.status == "Open", Payment.overdue_since.is_(None),
            Payment.due_date < payment_day_of(now), Payment.kind != "Add-on",
            Payment.voided_at.is_(None))) or 0
        return (late == 0, "Every late payment is marked Over due." if late == 0
                else f"{late} late payments are not marked Over due.")
    if job == "complaints-overdue":
        waiting = db.scalar(select(func.count()).select_from(Complaint).where(
            Complaint.status == "Raised", Complaint.created_at <= now - timedelta(hours=4),
            Complaint.overdue_alerted_at.is_(None))) or 0
        return (waiting == 0, "Every complaint over 4 hours has been alerted." if waiting == 0
                else f"{waiting} complaints over 4 hours have no alert yet.")
    if job == "freeze-due":
        from app.directory import lookup
        from app.scheduling import rules
        from app.scheduling.models import Schedule

        hour = lookup.setting(db, "schedule.freeze_hour")
        starts: list[date] = list(db.scalars(select(Schedule.start_date).where(Schedule.status == "Draft")))
        late = sum(1 for d in starts if now >= rules.freeze_deadline(d, hour))
        return (late == 0, "No Draft schedule is past the freeze cutoff." if late == 0
                else f"{late} Draft schedules are past the freeze cutoff.")
    return None, "Not checked"


def last_runs(db: Session, job: str, limit: int) -> list[CronRun]:
    return list(db.scalars(select(CronRun).where(CronRun.job == job)
                           .order_by(CronRun.started_at.desc()).limit(limit)))
