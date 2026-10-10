"""The 9 PM rule (SCHED-01) and the clock the rules read."""
from collections.abc import Callable
from datetime import date, datetime, time, timedelta

from app.platform import clock
from app.platform.errors import ApiError

Clock = Callable[[], datetime]
CUTOFF_HOUR = 21


def get_now() -> Clock:
    """The clock of a request. Looked up at call time, so a test may patch
    `app.platform.clock.now_ist` or override this dependency."""
    return lambda: clock.now_ist()


def show_date(d: date) -> str:
    """`07-Nov-26`."""
    return d.strftime("%d-%b-%y")


def today_of(now: datetime) -> date:
    return now.astimezone(clock.IST).date()


def cutoff_at(day: date) -> datetime:
    """9 PM the evening before `day`, in IST: the last moment a customer may
    change that day's schedule."""
    return datetime.combine(day - timedelta(days=1), time(CUTOFF_HOUR, 0), tzinfo=clock.IST)


def is_open(day: date, now: datetime) -> bool:
    return now < cutoff_at(day)


def require_open(day: date, now: datetime, *, bound: bool) -> None:
    """Customers are bound by the 9 PM rule. The admin is not (ADM-CUS-11),
    but cannot change a day that is already past."""
    if bound:
        if not is_open(day, now):
            raise ApiError(
                "after_cutoff",
                f"Changes for {show_date(day)} closed at 9 PM the evening before. "
                "Please call support.", 409, {"date": "after_cutoff"})
    elif day < today_of(now):
        raise ApiError("date_in_past", "That date has passed.", 409, {"date": "date_in_past"})
