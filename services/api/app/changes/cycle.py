"""The 30-day billing cycle and the days a pause adds to it (SUB-01, PAUSE-02).

DERIVED: each day inside a pause that is not cancelled (counted once, even
when a skip falls in it) moves the cycle forward one day, so the renewal date
is `first service date + paused days + 30 x cycles`."""
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.models import ScheduleChange

CYCLE_DAYS = 30


def paused_days(db: Session, vehicle_id: uuid.UUID) -> set[date]:
    rows = db.scalars(select(ScheduleChange).where(
        ScheduleChange.vehicle_id == vehicle_id, ScheduleChange.kind == "pause",
        ScheduleChange.status == "Active")).all()
    days: set[date] = set()
    for p in rows:
        days.update(p.start_date + timedelta(days=i)
                    for i in range((p.end_date - p.start_date).days + 1))
    return days


def cycle_window(first_service_date: date, paused: int, today: date) -> tuple[date, date]:
    """(start, renewal date) of the cycle that `today` falls in."""
    anchor = first_service_date + timedelta(days=paused)
    index = max(0, (today - anchor).days // CYCLE_DAYS)
    start = anchor + timedelta(days=CYCLE_DAYS * index)
    return start, start + timedelta(days=CYCLE_DAYS)


def renewal_date(db: Session, vehicle_id: uuid.UUID, first_service_date: date,
                 today: date) -> date:
    return cycle_window(first_service_date, len(paused_days(db, vehicle_id)), today)[1]
