"""Pure rules for the schedule: the freeze and customer deadlines, visit status
and working windows. No database here."""

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from app.directory import settings_registry
from app.platform.clock import IST


def _hour(key: str, hour: int | None) -> int:
    """The hour passed by a caller that read the live setting, else the seeded
    registry value (ADM-SET-*, `schedule.*`, read through `app.directory.lookup`)."""
    if hour is not None:
        return hour
    definition = settings_registry.BY_KEY[key]
    return settings_registry.typed(definition, settings_registry.default_for(key))


def freeze_deadline(first_day: date, hour: int | None = None) -> datetime:
    """The freeze hour (`schedule.freeze_hour`, ADM-SCH-25) the day before the
    first day of the schedule's period."""
    hour = _hour("schedule.freeze_hour", hour)
    return datetime.combine(first_day - timedelta(days=1), time(hour), tzinfo=IST)


def customer_deadline(day: date, hour: int | None = None) -> datetime:
    """The last moment a customer can change that date's schedule
    (`schedule.customer_change_hour`, SCHED-01). The admin is not bound by it
    (ADM-CUS-11)."""
    hour = _hour("schedule.customer_change_hour", hour)
    return datetime.combine(day - timedelta(days=1), time(hour), tzinfo=IST)


def customer_can_change(day: date, now: datetime, hour: int | None = None) -> bool:
    return now < customer_deadline(day, hour)


def visit_status(job_statuses: Iterable[str]) -> str:
    """A visit is Completed only when all its jobs are done or skipped. A Deferred
    job (SCHS-31) is not done, so it keeps the visit from Completed and the visit
    reads Could not complete, as for any job that was not done."""
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


def window_for(
    role: str, start: int, end: int, exception_kind: str | None, from_minute: int | None
) -> tuple[int, int] | None:
    """A crew member's working window on a day, or None when they do not work
    or do not count (ADM-CAP-01, ADM-CAP-02)."""
    if role == "Trainee":
        return None
    if exception_kind in ("Sick", "Leave"):
        return None
    if exception_kind == "Late start" and from_minute is not None:
        start = max(start, from_minute)
    return (start, end) if end > start else None


def _clock(text: str) -> int:
    hour, minute = text.split(":")
    return int(hour) * 60 + int(minute)


def hours_windows(
    working_hours: list | None, weekday: int, start: int, end: int
) -> list[tuple[int, int]]:
    """All base windows on a weekday (0 is Monday): the day's first window and
    its extra slots, for example 05:00-13:00 and 17:00-19:00 (ADM-CRW-04,
    ADM-CRW-25). With no per-weekday hours the single window applies every day.
    Empty on a day off."""
    if not working_hours:
        return [(start, end)]
    entry = working_hours[weekday] if weekday < len(working_hours) else None
    if not entry or not entry.get("working"):
        return []
    found = []
    try:
        found.append((_clock(entry["start"]), _clock(entry["end"])))
    except (KeyError, ValueError, AttributeError):
        return []
    for slot in entry.get("extra_slots") or []:
        try:
            found.append((_clock(slot["start"]), _clock(slot["end"])))
        except (KeyError, ValueError, AttributeError, TypeError):
            continue
    return [w for w in sorted(found) if w[1] > w[0]]


def windows_for(
    role: str, windows: list[tuple[int, int]], exception_kind: str | None,
    from_minute: int | None,
) -> list[tuple[int, int]]:
    """The windows a crew member really works on a date: none for a Trainee, none
    on Sick or Leave, and a Late start moves the start of every window that has
    not ended yet (ADM-CAP-01, ADM-CAP-02, ADM-CRW-09)."""
    if role == "Trainee" or exception_kind in ("Sick", "Leave"):
        return []
    out = []
    for start, end in windows:
        if exception_kind == "Late start" and from_minute is not None:
            start = max(start, from_minute)
        if end > start:
            out.append((start, end))
    return out


def hours_window(
    working_hours: list | None, weekday: int, start: int, end: int
) -> tuple[int, int] | None:
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
