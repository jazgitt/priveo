"""Temporary crew roles (P2-4, owner decisions 7 and 11).

A crew member has a permanent role on `SchedulingCrew.role`. A dated role
period gives another role for its days. The rules:

- A period covers its start and end days (both included). No end date means
  it lasts until the role is changed.
- Only days not yet run count: a period never changes a day before today
  (decision 7). Start dates in the past are refused.
- Pairing rules do not change (decision 11). A Trainee period needs a valid
  Member pairing that the crew member already has, and a Member with Trainees
  paired to them cannot take another role for any dates.
- A permanent role change (no dates) ends every period that has not ended
  yet (Derived: "effective until changed").

`load_crew` attaches each crew member's periods as `role_periods`, a list of
(first day, last day or None, role) with the first day never before today.
`role_on` reads them, so the scheduler, capacity and the day view see one
role per day.
"""
import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.platform.clock import today_ist
from app.platform.errors import ApiError
from app.scheduling.models import SchedulingCrew, SchedulingCrewRolePeriod

ROLES = ("Manager", "Member", "Trainee")


def attach(db: Session, crew: dict[uuid.UUID, SchedulingCrew], today: date) -> None:
    """Sets `role_periods` on each crew member from the periods still to run."""
    ids = [cid for cid in crew if cid is not None]
    grouped: dict[uuid.UUID, list[tuple[date, date | None, str]]] = {cid: [] for cid in ids}
    if ids:
        rows = db.execute(
            select(SchedulingCrewRolePeriod)
            .where(
                SchedulingCrewRolePeriod.crew_id.in_(ids),
                or_(SchedulingCrewRolePeriod.end_date.is_(None),
                    SchedulingCrewRolePeriod.end_date >= today),
            )
            .order_by(SchedulingCrewRolePeriod.start_date)
        ).scalars()
        for row in rows:
            grouped[row.crew_id].append((max(row.start_date, today), row.end_date, row.role))
    for cid, c in crew.items():
        if cid is not None:
            c.role_periods = grouped.get(cid, [])


def attach_missing(db: Session, crew: dict[uuid.UUID, SchedulingCrew]) -> None:
    """Attaches the periods to crew members that do not carry them yet."""
    missing = {cid: c for cid, c in crew.items() if not hasattr(c, "role_periods")}
    if missing:
        attach(db, missing, today_ist())


def role_on(crew, day: date) -> str:
    """The role a crew member has on `day`: the period that covers it, else the
    permanent role. A day before today is never covered."""
    for start, end, role in getattr(crew, "role_periods", ()):
        if start <= day and (end is None or day <= end):
            return role
    return crew.role


class _CrewOnDay:
    """The crew member's record with the role of one day. Every other field is
    read from the record itself."""

    def __init__(self, crew, role: str):
        self._crew = crew
        self.role = role

    def __getattr__(self, name):
        return getattr(self._crew, name)


def on_day(crew, day: date):
    """The crew member as the window rules see them on `day`."""
    role = role_on(crew, day)
    return crew if role == crew.role else _CrewOnDay(crew, role)


def periods_of(db: Session, sc: SchedulingCrew) -> list[SchedulingCrewRolePeriod]:
    """The periods that have not ended, soonest first."""
    today = today_ist()
    return list(db.scalars(
        select(SchedulingCrewRolePeriod)
        .where(SchedulingCrewRolePeriod.crew_id == sc.id,
               or_(SchedulingCrewRolePeriod.end_date.is_(None),
                   SchedulingCrewRolePeriod.end_date >= today))
        .order_by(SchedulingCrewRolePeriod.start_date)))


def _problem(code: str, message: str, status: int, fields: dict[str, str]) -> ApiError:
    return ApiError(code, message, status, fields)


def add_period(
    db: Session, sc: SchedulingCrew, role: str, start: date | None, end: date | None,
    actor_id: uuid.UUID | None,
) -> SchedulingCrewRolePeriod:
    """Adds a dated role. The caller commits and then re-plans the crew's open
    jobs (`release_unfit`)."""
    today = today_ist()
    if role not in ROLES:
        raise _problem("validation_failed", "Choose Manager, Member or Trainee.", 422,
                       {"role": "Choose a role."})
    if start is None and end is None:
        raise _problem("validation_failed", "Give a start or an end date. Without dates, change the role.",
                       422, {"start_date": "Choose a date."})
    start = start or today
    if start < today:
        raise _problem("validation_failed",
                       "Past dates cannot be changed. Choose today or a later date.", 422,
                       {"start_date": "Choose today or a later date."})
    if end is not None and end < start:
        raise _problem("validation_failed", "The end date is before the start date.", 422,
                       {"end_date": "Choose a date on or after the start date."})
    for other in periods_of(db, sc):
        if (other.end_date is None or other.end_date >= start) and (end is None or other.start_date <= end):
            raise ApiError("period_overlap",
                           "This crew member already has a role for some of these dates.", 409,
                           {"start_date": "Overlaps another role period."})
    if role == "Trainee" and sc.role != "Trainee":
        mate = db.get(SchedulingCrew, sc.paired_member_id) if sc.paired_member_id else None
        if mate is None or mate.role != "Member" or not mate.active or mate.society_id != sc.society_id:
            raise _problem("pairing_required",
                           "Pair this crew member with a Member before giving the Trainee role.",
                           422, {"role": "Choose a paired Member first."})
    if sc.role == "Member" and role != "Member":
        paired = db.scalar(select(SchedulingCrew.id).where(
            SchedulingCrew.paired_member_id == sc.id, SchedulingCrew.role == "Trainee",
            SchedulingCrew.active.is_(True)).limit(1))
        if paired is not None:
            raise ApiError("trainees_paired",
                           "Pair this Member's Trainees with another Member first.", 409,
                           {"role": "Trainees are paired with this Member."})
    row = SchedulingCrewRolePeriod(
        crew_id=sc.id, role=role, start_date=start, end_date=end, created_by=actor_id)
    db.add(row)
    db.flush()
    return row


def cancel_period(db: Session, sc: SchedulingCrew, period_id: uuid.UUID) -> None:
    """Removes a period that has not ended. The caller commits."""
    today = today_ist()
    row = db.get(SchedulingCrewRolePeriod, period_id)
    if row is None or row.crew_id != sc.id:
        raise ApiError("not_found", "This role period was not found.", 404)
    if row.end_date is not None and row.end_date < today:
        raise ApiError("period_done", "That role period has already ended.", 409)
    db.delete(row)
    db.flush()


def clear_open_periods(db: Session, crew_id: uuid.UUID, today: date) -> int:
    """Ends every period that has not ended, for a permanent role change. The
    caller commits. Returns how many were removed."""
    rows = list(db.scalars(select(SchedulingCrewRolePeriod).where(
        SchedulingCrewRolePeriod.crew_id == crew_id,
        or_(SchedulingCrewRolePeriod.end_date.is_(None),
            SchedulingCrewRolePeriod.end_date >= today))))
    for row in rows:
        db.delete(row)
    db.flush()
    return len(rows)
