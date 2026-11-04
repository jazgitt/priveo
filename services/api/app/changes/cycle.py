"""The 30-day billing cycle (SUB-01, PAY-14, PAUSE-02).

DERIVED: a cycle is 30 days with both ends inclusive (1 Jan to 30 Jan; the next
starts on 31 Jan). Nothing moves it: not a payment, a pause, a skip or a credit
(owner decision, 4 Nov 2026). So the renewal date is
`first service date + 30 x cycles`, and the plan expires at the end of the
current cycle. `shift_days` stays as the one place that would hold a shift; it
is always 0. The old `PlanExtension` rows are kept as history, not counted."""
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.models import ScheduleChange
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
    """Always 0. A skipped visit no longer extends the plan (B-01). Every
    `PlanExtension` row was created by a skip, so none is counted."""
    return 0


def shift_days(db: Session, vehicle_id: uuid.UUID) -> int:
    """Always 0: pause, skip and credit do not move the cycle."""
    return 0


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


def plan_expires_on(db: Session, sub, today: date) -> date:
    """The last day the plan covers: the end of the current cycle (inclusive).
    Paying ahead does not extend it."""
    cycle_days = lookup.setting(db, "billing.cycle_days")
    _, renewal = cycle_window(sub.first_service_date, shift_days(db, sub.vehicle_id),
                              today, cycle_days)
    return renewal - timedelta(days=1)
