import datetime as dt

from pydantic import BaseModel


class SkipIn(BaseModel):
    date: dt.date


class PauseIn(BaseModel):
    from_date: dt.date
    to_date: dt.date


class CutoffChangeIn(BaseModel):
    date: dt.date
    # HH:MM in 30-minute steps (ONB-16).
    cutoff_time: str


class ChangeOut(BaseModel):
    id: str
    vehicle_id: str
    kind: str  # skip | pause | cutoff
    status: str
    start_date: dt.date
    end_date: dt.date
    days: int
    cutoff_time: str | None = None
    actor: str
    # A pause: the visits paused and the new renewal date (PAUSE-02, PAUSE-03).
    visits_paused: int | None = None
    renewal_date: dt.date | None = None
    created_at: dt.datetime


class ChangesOut(BaseModel):
    vehicle_id: str
    skips: list[ChangeOut]
    pauses: list[ChangeOut]
    cutoff_changes: list[ChangeOut]
    renewal_date: dt.date | None = None
    # The last day the current plan covers. A customer can skip or pause only
    # up to this date (SKIP-09, PAUSE-08).
    plan_ends_on: dt.date | None = None


class UpcomingDay(BaseModel):
    date: dt.date
    services: list[str]
    # Scheduled | Skipped | Paused
    state: str
    skip_id: str | None = None
    pause_id: str | None = None
    cutoff_time: str | None = None
    # False once 9 PM the day before has passed (SCHED-02).
    can_change: bool
    # Frozen: a cutoff change is only a request (CAL-07).
    frozen: bool


class PreferencesIn(BaseModel):
    # HH:MM in 30-minute steps (ONB-16). Omit to leave it as it is.
    cutoff_time: str | None = None
    interior_day: str | None = None


class PreferencesOut(BaseModel):
    vehicle_id: str
    cutoff_time: str | None
    interior_day: str | None
    # The first date the new default applies to (SCHED-01).
    applies_from: dt.date
    # Planned dates in a frozen schedule that keep the old cutoff time.
    frozen_days_unchanged: int
