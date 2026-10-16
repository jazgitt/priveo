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
    from app.customers.models import Subscription

    first = db.scalar(select(Subscription.first_service_date).where(
        Subscription.vehicle_id == vehicle_id))
    if first is None:
        return len(paused_days(db, vehicle_id)) + extension_days(db, vehicle_id)
    # A reactivation starts a new billing epoch; retain prior history without
    # applying its pauses/extensions again to the new first cycle.
    paused = sum(day >= first for day in paused_days(db, vehicle_id))
    extensions = db.scalar(select(func.count()).select_from(PlanExtension).where(
        PlanExtension.vehicle_id == vehicle_id, PlanExtension.on_date >= first)) or 0
    return paused + extensions


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
    """The last day the plan covers (the date shown as "Expires on").

    It is the end of the current cycle, or later when the customer has paid
    ahead: a Received plan payment for a later cycle moves it to the end of
    that cycle. So when the admin confirms a renewal payment, the expiry date
    moves on at once, before the renewal date arrives.
    """
    from app.billing.models import Payment

    cycle_days = lookup.setting(db, "billing.cycle_days")
    _, renewal = cycle_window(sub.first_service_date, shift_days(db, sub.vehicle_id),
                              today, cycle_days)
    end = renewal - timedelta(days=1)
    paid_to = db.scalar(select(func.max(Payment.cycle_end)).where(
        Payment.subscription_id == sub.id, Payment.kind == "Plan",
        Payment.status == "Received", Payment.voided_at.is_(None)))
    if paid_to is not None:
        end = max(end, paid_to - timedelta(days=1))
    return end
