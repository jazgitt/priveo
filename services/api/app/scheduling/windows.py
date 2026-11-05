"""Builds a cleaner's windows and a job's allowed windows by running the rules
found in `window_rules` (SCHS-04)."""
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.scheduling import window_rules
from app.scheduling.models import SchedulingCrew, SchedulingCrewException


def cleaner_windows(
    db: Session, crew: dict[uuid.UUID, SchedulingCrew], days: list[date]
) -> dict[date, dict[uuid.UUID, list[tuple[int, int]]]]:
    """For each date, the working windows of every counted crew member."""
    exceptions: dict[tuple[uuid.UUID, date], SchedulingCrewException] = {}
    if crew and days:
        for ex in db.execute(
            select(SchedulingCrewException).where(
                SchedulingCrewException.crew_id.in_(list(crew)),
                SchedulingCrewException.on_date.in_(days),
            )
        ).scalars():
            exceptions[(ex.crew_id, ex.on_date)] = ex
    rules = [m.cleaner_windows for m in window_rules.discover() if hasattr(m, "cleaner_windows")]
    out: dict[date, dict[uuid.UUID, list[tuple[int, int]]]] = {}
    for day in days:
        out[day] = {}
        for cid, c in crew.items():
            ex = exceptions.get((cid, day))
            windows = None
            for rule in rules:
                windows = rule(db, c, day, windows, ex)
            if windows:
                out[day][cid] = windows
    return out


def job_windows(db, society_id, service, day):
    """The windows a job of `service` may be placed in on `day`."""
    windows = None
    for m in window_rules.discover():
        if hasattr(m, "job_windows"):
            windows = m.job_windows(db, society_id, service, day, windows)
    return windows


def capacity_lines(db, society_id, day) -> list[dict]:
    """Extra lines the rules add to a day's capacity demand list."""
    out: list[dict] = []
    for m in window_rules.discover():
        if hasattr(m, "capacity_lines"):
            out.extend(m.capacity_lines(db, society_id, day) or [])
    return out
