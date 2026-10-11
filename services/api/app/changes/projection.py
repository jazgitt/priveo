"""The service days a subscription implies, for dates the scheduler has not
planned yet (CAL-01).

The scheduler plans a week at a time. The calendar and the skip list also show
the dates after that, from the rules the scheduler itself uses
(`app.scheduling.service.build_demand`): Cleaning-External every day and
Cleaning-Internal on the interior care day, from the first service date, for
an Active subscription."""
from datetime import date, timedelta

from app.changes.cycle import CYCLE_DAYS
from app.customers.models import WEEKDAYS, Subscription


def day_services(sub: Subscription | None, day: date) -> list[str]:
    """The services the subscription implies on `day`. Empty when none."""
    if sub is None or sub.status != "Active" or day < sub.first_service_date:
        return []
    services = ["Cleaning-External"]
    if sub.interior_day and WEEKDAYS[day.weekday()] == sub.interior_day:
        services.append("Cleaning-Internal")
    return services


def renewals_between(first_service_date: date, paused: int, start: date, end: date) -> list[date]:
    """The renewal dates in [start, end]. Every day paused moves them one day
    on (PAUSE-02), the same rule as `cycle.cycle_window`."""
    anchor = first_service_date + timedelta(days=paused)
    out = []
    n = max(1, (start - anchor).days // CYCLE_DAYS)
    while True:
        d = anchor + timedelta(days=CYCLE_DAYS * n)
        if d > end:
            return out
        if d >= start:
            out.append(d)
        n += 1
