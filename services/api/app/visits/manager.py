"""A Manager's attendance, working hours and reassign checks for their own
society (CRW-MGR-03, CRW-MGR-04, CRW-MGR-05).

Attendance is a `SchedulingCrewException`, the same row the admin writes, so
the scheduler's capacity reads it at once (ADM-CRW-11). Jobs that no longer
fit go through `scheduling.release_unfit` and, on a Frozen schedule, are
placed again at once when someone fits (ADM-SCH-27) or stay on the Needs
scheduling list (ADM-SCH-28). A Manager never runs or freezes a schedule: the
placing here is the system's own late assignment."""
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
from app.crew.service import (
    _TIME,
    MAX_RANGE_DAYS,
    DayHours,
    _hhmm,
    _minutes,
    _summary,
    check_hours,
)
from app.directory.models import Society
from app.identity.models import Login
from app.platform.clock import today_ist
from app.platform.errors import ApiError
from app.scheduling import rules
from app.scheduling import service as scheduling
from app.scheduling.models import (
    Job,
    Schedule,
    SchedulingCrew,
    SchedulingCrewException,
    Visit,
)
from app.customers.models import Vehicle
from app.visits import manager_schemas as m
from app.visits.models import CrewManagerChange

STATUSES = ("present", "Sick", "Leave", "Late start")
ASSIGNABLE_ROLES = ("Member", "Manager")


def _problem(message: str, **fields: str) -> ApiError:
    return ApiError("validation_failed", message, 422, fields)


def crew_of_society(db: Session, manager: SchedulingCrew, crew_id: str) -> SchedulingCrew:
    """A crew member of the Manager's own society. Anyone else is 404."""
    try:
        sc = db.get(SchedulingCrew, uuid.UUID(crew_id))
    except ValueError:
        sc = None
    if sc is None or sc.society_id != manager.society_id:
        raise ApiError("not_found", "This crew member was not found.", 404)
    return sc


def _society_crew(db: Session, manager: SchedulingCrew) -> list[tuple[SchedulingCrew, str]]:
    return list(db.execute(
        select(SchedulingCrew, Login.display_name)
        .join(Login, Login.id == SchedulingCrew.login_id)
        .where(SchedulingCrew.society_id == manager.society_id, SchedulingCrew.active.is_(True))
        .order_by(Login.display_name, SchedulingCrew.id)).all())


def _log(db: Session, manager: SchedulingCrew, crew: SchedulingCrew, by: uuid.UUID,
         kind: str, on_date: date, detail: str) -> None:
    db.add(CrewManagerChange(society_id=manager.society_id, crew_id=crew.id, by_login_id=by,
                             kind=kind, on_date=on_date, detail=detail))


# ---- releasing and placing again -------------------------------------------------

def _release(db: Session, crew: SchedulingCrew, today: date) -> list[m.CrewManagerReleasedJob]:
    """Takes the crew member's open jobs that no longer fit off them, then
    places the ones on Frozen schedules again where someone fits. Commits."""
    released = scheduling.release_unfit(db, crew, today)
    db.commit()
    if not released:
        return []
    ids = [r["job_id"] for r in released]
    frozen = list(db.scalars(
        select(Schedule).join(Visit, Visit.schedule_id == Schedule.id)
        .join(Job, Job.visit_id == Visit.id)
        .where(Job.id.in_(ids), Schedule.status == "Frozen").distinct()))
    for schedule in frozen:
        scheduling.run_schedule(db, schedule, None)
    placed = {j.id: j.crew_id is not None for j in db.scalars(select(Job).where(Job.id.in_(ids)))}
    return [m.CrewManagerReleasedJob(
        job_id=str(r["job_id"]), date=r["date"], service=r["service"],
        registration=r["registration"], reassigned=placed.get(r["job_id"], False))
        for r in released]


# ---- attendance (CRW-MGR-04) -----------------------------------------------------

def attendance(db: Session, manager: SchedulingCrew, day: date) -> m.CrewManagerAttendance:
    team = _society_crew(db, manager)
    ids = [sc.id for sc, _n in team]
    exceptions = {e.crew_id: e for e in db.scalars(
        select(SchedulingCrewException).where(SchedulingCrewException.crew_id.in_(ids),
                                              SchedulingCrewException.on_date == day))} \
        if ids else {}
    open_jobs = dict(db.execute(
        select(Job.crew_id, func.count()).join(Visit, Visit.id == Job.visit_id)
        .where(Job.crew_id.in_(ids), Job.status == "Scheduled", Visit.date == day)
        .group_by(Job.crew_id)).all()) if ids else {}
    entries = []
    for sc, name in team:
        base = rules.hours_window(sc.working_hours, day.weekday(), sc.start_minute,
                                  sc.end_minute)
        working = base is not None and base[1] > base[0]
        ex = exceptions.get(sc.id)
        entries.append(m.CrewManagerAttendanceEntry(
            crew_id=str(sc.id), name=name, role=sc.role, working=working,
            start=_hhmm(base[0]) if working else "", end=_hhmm(base[1]) if working else "",
            status=ex.kind if ex else "present",
            late_start=_hhmm(ex.from_minute) if ex and ex.kind == "Late start" else "",
            open_jobs=open_jobs.get(sc.id, 0)))
    society = db.scalar(select(Society.name).where(Society.id == manager.society_id)) or ""
    return m.CrewManagerAttendance(date=day, society=society, crew=entries)


def set_attendance(db: Session, manager: SchedulingCrew, crew_id: str,
                   body: m.CrewManagerAttendanceSet,
                   by: uuid.UUID) -> m.CrewManagerAttendanceResult:
    """Marks one crew member present, absent (Sick, Leave) or on a Late start
    for a date or a range. Replaces what was there, so it adds, edits and
    removes an exception in one call."""
    crew = crew_of_society(db, manager, crew_id)
    today = today_ist()
    if body.status not in STATUSES:
        raise _problem("Choose Present, Sick, Leave or Late start.",
                       status="Choose a status.")
    to_date = body.to_date or body.from_date
    if to_date < body.from_date:
        raise _problem("The last date is before the first date.",
                       to_date="Choose a date on or after the first date.")
    if body.from_date < today:
        raise _problem("Choose today or a later date.",
                       from_date="Choose today or a later date.")
    if (to_date - body.from_date).days >= MAX_RANGE_DAYS:
        raise _problem(f"A range can be at most {MAX_RANGE_DAYS} days.",
                       to_date="The range is too long.")
    from_minute = None
    if body.status == "Late start":
        if not _TIME.fullmatch(body.start):
            raise _problem("Give the time the crew member can start.", start="Use HH:MM.")
        from_minute = _minutes(body.start)
    if not crew.active:
        raise ApiError("crew_inactive", "This crew member is not active.", 409)

    days = [body.from_date + timedelta(days=i)
            for i in range((to_date - body.from_date).days + 1)]
    rows = {e.on_date: e for e in db.scalars(
        select(SchedulingCrewException).where(SchedulingCrewException.crew_id == crew.id,
                                              SchedulingCrewException.on_date.in_(days)))}
    for day in days:
        row = rows.get(day)
        if body.status == "present":
            if row is not None:
                db.delete(row)
        elif row is None:
            db.add(SchedulingCrewException(crew_id=crew.id, on_date=day, kind=body.status,
                                           from_minute=from_minute))
        else:
            row.kind, row.from_minute = body.status, from_minute
    span = (body.from_date.isoformat() if to_date == body.from_date
            else f"{body.from_date.isoformat()} to {to_date.isoformat()}")
    _log(db, manager, crew, by, "attendance", body.from_date,
         f"{body.status} {span}" + (f" from {body.start}" if from_minute is not None else ""))
    db.flush()
    released = _release(db, crew, today)
    return m.CrewManagerAttendanceResult(
        attendance=attendance(db, manager, body.from_date), released_jobs=released)


# ---- working hours (CRW-MGR-05) --------------------------------------------------

def _hours_out(sc: SchedulingCrew, name: str) -> m.CrewManagerHours:
    hours = sc.working_hours or []
    if not hours:
        # A record with one window for every day (older rows and tests).
        window = (_hhmm(sc.start_minute), _hhmm(sc.end_minute))
        hours = [{"day": d, "working": True, "start": window[0], "end": window[1]}
                 for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")]
    return m.CrewManagerHours(crew_id=str(sc.id), name=name, role=sc.role,
                              working_hours=[DayHours(**h) for h in hours])


def hours_list(db: Session, manager: SchedulingCrew) -> list[m.CrewManagerHours]:
    return [_hours_out(sc, name) for sc, name in _society_crew(db, manager)]


def set_hours(db: Session, manager: SchedulingCrew, crew_id: str,
              body: m.CrewManagerHoursSet, by: uuid.UUID) -> m.CrewManagerHoursResult:
    """New hours for a crew member of the society, applied from today on.
    Role, society and password are not touched (CRW-MGR-05)."""
    crew = crew_of_society(db, manager, crew_id)
    if not crew.active:
        raise ApiError("crew_inactive", "This crew member is not active.", 409)
    hours = check_hours(body.working_hours)
    crew.working_hours = hours
    crew.start_minute, crew.end_minute = _summary(hours)
    # The directory keeps the same hours, so an admin edit starts from them.
    member = db.scalar(select(CrewMember).where(CrewMember.login_id == crew.login_id))
    if member is not None:
        member.working_hours = hours
    today = today_ist()
    off = [h["day"] for h in hours if not h["working"]]
    _log(db, manager, crew, by, "hours", today,
         "off: " + (", ".join(off) if off else "none"))
    db.flush()
    released = _release(db, crew, today)
    name = db.scalar(select(Login.display_name).where(Login.id == crew.login_id)) or ""
    return m.CrewManagerHoursResult(hours=_hours_out(crew, name), released_jobs=released)


# ---- reassign checks (CRW-MGR-03) ------------------------------------------------

def _busy(db: Session, target: SchedulingCrew, day: date,
          skip: uuid.UUID) -> list[tuple[int, int]]:
    rows = db.execute(
        select(Job.start_minute, Job.duration_minutes)
        .join(Visit, Visit.id == Job.visit_id)
        .where(Job.crew_id == target.id, Visit.date == day, Job.id != skip,
               Job.status != "Skipped", Job.start_minute.is_not(None))
        .order_by(Job.start_minute)).all()
    return [(s, s + d) for s, d in rows]


def _first_slot(window: tuple[int, int], busy: list[tuple[int, int]],
                duration: int) -> int | None:
    at = window[0]
    for s, e in busy:
        if s - at >= duration:
            break
        at = max(at, e)
    return at if at + duration <= window[1] else None


def _why_not_working(db: Session, target: SchedulingCrew, day: date) -> str:
    ex = db.scalar(select(SchedulingCrewException).where(
        SchedulingCrewException.crew_id == target.id, SchedulingCrewException.on_date == day))
    if ex is not None and ex.kind in ("Sick", "Leave"):
        return f"Is away that day ({ex.kind})."
    if target.role == "Trainee":
        return "A Trainee is not given jobs."
    return "Has the day off."


def reassign_problem(db: Session, job: Job, visit: Visit,
                     target: SchedulingCrew) -> tuple[str, str, int | None] | None:
    """What stops this job going to `target`, as (code, words, start minute to
    use), or None when it can go. The start is the job's own time, or the
    first free time when the job has none yet."""
    if target.id == job.crew_id:
        return "same_crew", "The job is already on this crew member.", None
    window = scheduling.availability(db, {target.id: target}, [visit.date])[visit.date].get(
        target.id)
    if window is None:
        return "crew_not_working", _why_not_working(db, target, visit.date), None
    busy = _busy(db, target, visit.date, job.id)
    start = job.start_minute
    if start is None:
        start = _first_slot(window, busy, job.duration_minutes)
        if start is None:
            return "no_slot", "Has no free time that day.", None
        return None if True else None  # a slot was found
    end = start + job.duration_minutes
    if start < window[0] or end > window[1]:
        return ("outside_hours",
                f"Works {rules.hhmm(window[0])} to {rules.hhmm(window[1])} that day. The job "
                f"is {rules.hhmm(start)} to {rules.hhmm(end)}.", None)
    if any(start < e and s < end for s, e in busy):
        return "overlap", "Has another job at that time.", None
    return None


def check_assignable(db: Session, manager: SchedulingCrew, target: SchedulingCrew | None) -> None:
    if (target is None or not target.active or target.society_id != manager.society_id
            or target.role not in ASSIGNABLE_ROLES):
        raise ApiError("validation_failed", "Choose a Member or Manager of this society.", 422,
                       {"crew_id": "Not available for this job."})


def reassign_options(db: Session, manager: SchedulingCrew,
                     job: Job) -> list[m.CrewManagerReassignOption]:
    visit = db.get(Visit, job.visit_id)
    out = []
    for sc, name in _society_crew(db, manager):
        if sc.role not in ASSIGNABLE_ROLES:
            continue
        problem = reassign_problem(db, job, visit, sc)
        out.append(m.CrewManagerReassignOption(
            crew_id=str(sc.id), name=name, role=sc.role, can_assign=problem is None,
            problem_code=problem[0] if problem else "",
            problem=problem[1] if problem else ""))
    return out


def apply_start(db: Session, job: Job, visit: Visit, target: SchedulingCrew) -> None:
    """A job with no time yet gets the target's first free time."""
    if job.start_minute is not None:
        return
    window = scheduling.availability(db, {target.id: target}, [visit.date])[visit.date][
        target.id]
    job.start_minute = _first_slot(window, _busy(db, target, visit.date, job.id),
                                   job.duration_minutes)
    end = job.start_minute + job.duration_minutes
    job.late = job.finish_by_minute is not None and end > job.finish_by_minute
    job.note = ""


def vehicle_registration(db: Session, visit: Visit) -> str:
    return db.scalar(select(Vehicle.registration).where(Vehicle.id == visit.vehicle_id)) or ""
