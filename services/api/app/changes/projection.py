"""The service days a subscription implies, for dates the scheduler has not
planned yet (CAL-01).

The scheduler plans a week at a time. The calendar and the skip list also show
the dates after that, from the rules the scheduler itself uses
(`app.scheduling.service.build_demand`): Cleaning-External every day and
Cleaning-Internal on the interior care day, from the first service date, for
an Active subscription."""
from datetime import date, timedelta

from sqlalchemy.orm import Session, object_session

from app.changes.cycle import CYCLE_DAYS
from app.customers import schedule_pattern
from app.customers.models import WEEKDAYS, Customer, Subscription, Vehicle

INTERIOR = "Cleaning-Internal"


def _society_id(session: Session, sub: Subscription):
    vehicle = session.get(Vehicle, sub.vehicle_id)
    if vehicle is None:
        return None
    if vehicle.society_id is not None:
        return vehicle.society_id
    customer = session.get(Customer, vehicle.customer_id)
    return customer.society_id if customer else None


def _entitlement_model(session: Session | None, sub: Subscription) -> bool:
    """True when the car has a site: an Interior is owed for the service week,
    and no weekday is promised for it (SCHS-38)."""
    society = _society_id(session, sub) if session is not None else None
    return society is not None


def interior_this_week(sub: Subscription | None, day: date) -> bool:
    """Whether the calendar says "Interior this week" for the service week of `day`
    : the plan owes an Interior that week and the ledger has not
    planned, completed or waived it. A week with a planned Interior job is the
    caller's to exclude, because it shows the planned day instead."""
    session = object_session(sub) if sub is not None else None
    if sub is None or sub.status != "Active" or session is None or not _entitlement_model(session, sub):
        return False
    from app.scheduling import entitlements

    week = entitlements.week_start(session, day, _society_id(session, sub))
    if week + timedelta(days=7) <= sub.first_service_date:
        return False
    rows = entitlements.rows_for_week(session, sub.vehicle_id, week)
    if rows:
        return any(r.status == entitlements.PENDING for r in rows)
    return entitlements.owes(session, sub, week)


def day_services(sub: Subscription | None, day: date) -> list[str]:
    """The services the subscription implies on `day`. Empty when none."""
    if sub is None or sub.status != "Active" or day < sub.first_service_date:
        return []
    session = object_session(sub)
    # Version 2 (SCHS-38): the Interior is owed for the week, not promised on the
    # preferred weekday. The calendar says "Interior this week" until it is planned.
    promise_interior = not _entitlement_model(session, sub)
    pattern = schedule_pattern.pattern_of(session, sub) if session is not None else None
    if pattern is not None:  # S-02: the same rule the scheduler uses
        exterior, interior = schedule_pattern.day_flags(session, sub, pattern, day)
        return (["Cleaning-External"] if exterior else []) + (
            [INTERIOR] if interior and promise_interior else [])
    services = ["Cleaning-External"]
    if promise_interior and sub.interior_day and WEEKDAYS[day.weekday()] == sub.interior_day:
        services.append(INTERIOR)
    return services


def renewals_between(first_service_date: date, paused: int, start: date, end: date,
                     cycle_days: int = CYCLE_DAYS) -> list[date]:
    """The renewal dates in [start, end], the same rule as `cycle.cycle_window`.
    `paused` shifts the dates by that many days; callers pass 0 because a pause,
    skip or credit does not move the cycle."""
    anchor = first_service_date + timedelta(days=paused)
    out = []
    n = max(1, (start - anchor).days // cycle_days)
    while True:
        d = anchor + timedelta(days=cycle_days * n)
        if d > end:
            return out
        if d >= start:
            out.append(d)
        n += 1
