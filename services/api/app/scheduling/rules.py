"""Pure rules for the schedule: the freeze and customer deadlines, visit status
and working windows. No database here."""
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from app.platform.clock import IST

# ADM-SCH-18: the secret code that unfreezes a schedule is the word "unfreeze".
UNFREEZE_CODE = "unfreeze"

FREEZE_HOUR = 20     # ADM-SCH-25: 8 PM the day before the first day.
CUSTOMER_HOUR = 21   # SCHED-01: customers change by 9 PM the previous day.


def freeze_deadline(first_day: date) -> datetime:
    """8 PM (IST) the day before the first day of the schedule's period."""
    return datetime.combine(first_day - timedelta(days=1), time(FREEZE_HOUR), tzinfo=IST)


def customer_deadline(day: date) -> datetime:
    """The last moment a customer can change that date's schedule. The admin
    is not bound by it (ADM-CUS-11)."""
    return datetime.combine(day - timedelta(days=1), time(CUSTOMER_HOUR), tzinfo=IST)


def customer_can_change(day: date, now: datetime) -> bool:
    return now < customer_deadline(day)


def visit_status(job_statuses: Iterable[str]) -> str:
    """A visit is Completed only when all its jobs are done or skipped."""
    statuses = list(job_statuses)
    if not statuses:
        return "Scheduled"
    if all(s == "Skipped" for s in statuses):
        return "Skipped"
    if all(s in ("Completed", "Skipped") for s in statuses):
        return "Completed"
    if any(s in ("Scheduled", "In progress") for s in statuses):
        started = any(s in ("In progress", "Completed") for s in statuses)
        return "In progress" if started else "Scheduled"
    return "Could not complete"


def hhmm(minute: int | None) -> str | None:
    if minute is None:
        return None
    return f"{minute // 60:02d}:{minute % 60:02d}"


def window_for(role: str, start: int, end: int, exception_kind: str | None,
               from_minute: int | None) -> tuple[int, int] | None:
    """A crew member's working window on a day, or None when they do not work
    or do not count (ADM-CAP-01, ADM-CAP-02)."""
    if role == "Trainee":
        return None
    if exception_kind in ("Sick", "Leave"):
        return None
    if exception_kind == "Late start" and from_minute is not None:
        start = max(start, from_minute)
    return (start, end) if end > start else None


def hours_window(working_hours: list | None, weekday: int, start: int,
                 end: int) -> tuple[int, int] | None:
    """The base window on a weekday (0 is Monday) from the per-weekday hours
    (ADM-CRW-04). With no per-weekday hours the single window applies every
    day. None on a day off."""
    if not working_hours:
        return (start, end)
    entry = working_hours[weekday] if weekday < len(working_hours) else None
    if not entry or not entry.get("working"):
        return None
    try:
        s_h, s_m = entry["start"].split(":")
        e_h, e_m = entry["end"].split(":")
    except (KeyError, ValueError, AttributeError):
        return None
    return (int(s_h) * 60 + int(s_m), int(e_h) * 60 + int(e_m))
