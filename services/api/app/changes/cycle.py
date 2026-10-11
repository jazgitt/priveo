"""The 30-day billing cycle and the days a pause adds to it (SUB-01, PAUSE-02).

DERIVED: each day inside a pause that is not cancelled (counted once, even
when a skip falls in it) moves the cycle forward one day, so the renewal date
is `first service date + paused days + 30 x cycles`. A Cleaning-External
visit skipped by operations adds one day too (ADM-OPS-03, `PlanExtension`)."""
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.changes.models import PlanExtension, ScheduleChange
from app.directory import lookup

# The starting value; the live one is `billing.cycle_days` (see app.directory.lookup).
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


def extension_days(db: Session, vehicle_id: uuid.UUID) -> int:
    """Days added to the plan because operations skipped a Cleaning-External
    visit (ADM-OPS-03). Each one moves the renewal date forward one day."""
    return db.scalar(select(func.count()).select_from(PlanExtension)
                     .where(PlanExtension.vehicle_id == vehicle_id)) or 0


def shift_days(db: Session, vehicle_id: uuid.UUID) -> int:
    """Everything that moves the renewal date forward: paused days and days
    added by operations."""
    return len(paused_days(db, vehicle_id)) + extension_days(db, vehicle_id)


def cycle_window(first_service_date: date, paused: int, today: date,
                 cycle_days: int = CYCLE_DAYS) -> tuple[date, date]:
    """(start, renewal date) of the cycle that `today` falls in."""
    anchor = first_service_date + timedelta(days=paused)
    index = max(0, (today - anchor).days // cycle_days)
    start = anchor + timedelta(days=cycle_days * index)
    return start, start + timedelta(days=cycle_days)


def renewal_date(db: Session, vehicle_id: uuid.UUID, first_service_date: date,
                 today: date) -> date:
    return cycle_window(first_service_date, shift_days(db, vehicle_id), today,
                        lookup.setting(db, "billing.cycle_days"))[1]
