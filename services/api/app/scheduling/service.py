"""Scheduling on the database: demand, capacity, runs, manual changes, the
freeze rules and the read models for the customer and crew apps."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.changes.models import ScheduleChange
from app.customers.models import WEEKDAYS, AddonRequest, Customer, Subscription, Vehicle
from app.customers.parking import label as parking_label
from app.customers.parking import slots as parking_slots
from app.directory import lookup
from app.directory.models import Plan, Society
from app.identity.models import Login
from app.notifications import emit  # notify hook
from app.platform.db import utcnow
from app.platform.errors import ApiError
from app.scheduling import queue, rules
from app.scheduling.models import (
    DURATIONS,
    Job,
    Schedule,
    SchedulingCrew,
    SchedulingCrewException,
    SchedulingEvent,
    Visit,
)
from app.scheduling.solver import SolverCrew, SolverJob, solve_day

DAY_DONE = ("Completed", "Skipped")


@dataclass(frozen=True)
class Demand:
    """A job that is due: one service for one vehicle on one date (ADM-CAP-03)."""

    day: date
    vehicle_id: uuid.UUID
    service: str
    finish_by: int | None
    addon_request_id: uuid.UUID | None = None
    # The customer skipped or paused the date before it was planned: the job is
    # created as Skipped, as it would be had it been planned first (SKIP-, PAUSE-).
    skipped: bool = False
    addon_booking_id: uuid.UUID | None = None
    source_job_id: uuid.UUID | None = None

    @property
    def duration(self) -> int:
        return DURATIONS[self.service]


@dataclass
class RunSummary:
    schedule_id: uuid.UUID
    society_id: uuid.UUID
    status: str
    placed: int
    unscheduled: int
    late: int


def daterange(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def minutes_of(t: time | None) -> int | None:
    return None if t is None else t.hour * 60 + t.minute


def record(
    db: Session,
    schedule_id: uuid.UUID,
    admin_id: uuid.UUID | None,
    kind: str,
    detail: str = "",
    changes: dict | None = None,
) -> None:
    db.add(
        SchedulingEvent(schedule_id=schedule_id, admin_login_id=admin_id, kind=kind, detail=detail)
    )
    if admin_id:
        from app.directory.service import audit

        # A-04: {field: [old, new]} when the caller knows it, else the text.
        audit(db, admin_id, "schedule", schedule_id, kind, changes or {"detail": detail})


# ---- demand and capacity ---------------------------------------------------


def _customer_changes(
    db: Session, vehicle_id: uuid.UUID, days: list[date]
) -> tuple[set[date], dict[date, int]]:
    """The dates the customer skipped or paused, and the cutoff times they set
    for single dates (CAL-07, CAL-08), as they stand when the schedule is planned."""
    rows = db.scalars(
        select(ScheduleChange)
        .where(
            ScheduleChange.vehicle_id == vehicle_id,
            ScheduleChange.status.in_(("Active", "Applied")),
            ScheduleChange.start_date <= days[-1],
            ScheduleChange.end_date >= days[0],
        )
        .order_by(ScheduleChange.created_at)
    ).all()
    off: set[date] = set()
    cutoffs: dict[date, int] = {}
    for c in rows:
        if c.kind in ("skip", "pause"):
            off.update(daterange(max(c.start_date, days[0]), min(c.end_date, days[-1])))
        elif c.cutoff_time is not None:
            cutoffs[c.start_date] = c.cutoff_time.hour * 60 + c.cutoff_time.minute
    return off, cutoffs


def build_demand(db: Session, society_id: uuid.UUID, days: list[date]) -> list[Demand]:
    """Cleaning-External every day, Cleaning-Internal on the interior care day
    and a Deep Spa on the date the customer asked for (ADM-SVS-10). Only
    Active subscriptions count (ADM-SUB-02)."""
    out: list[Demand] = []
    rows = db.execute(
        select(Subscription, Vehicle)
        .join(Vehicle, Subscription.vehicle_id == Vehicle.id)
        .join(Customer, Vehicle.customer_id == Customer.id)
        .where(
            func.coalesce(Vehicle.society_id, Customer.society_id) == society_id,
            Subscription.status == "Active",
            Vehicle.active.is_(True),
        )
        .order_by(Vehicle.created_at, Vehicle.id)
    ).all()
    for sub, vehicle in rows:
        default_cutoff = minutes_of(sub.cutoff_time)
        off, own_cutoff = _customer_changes(db, vehicle.id, days)
        for day in days:
            if day < sub.first_service_date:
                continue
            cutoff = own_cutoff.get(day, default_cutoff)
            out.append(Demand(day, vehicle.id, "Cleaning-External", cutoff, skipped=day in off))
            chosen_plan = (
                sub.pending_plan_id
                if sub.pending_plan_id and sub.pending_from and day >= sub.pending_from
                else sub.plan_id
            )
            plan = db.get(Plan, chosen_plan) if chosen_plan else None
            if (
                sub.interior_day
                and (plan is None or plan.includes_interior)
                and WEEKDAYS[day.weekday()] == sub.interior_day
            ):
                out.append(Demand(day, vehicle.id, "Cleaning-Internal", cutoff, skipped=day in off))
    addons = (
        db.execute(
            select(AddonRequest)
            .join(Customer, AddonRequest.customer_id == Customer.id)
            .join(Vehicle, AddonRequest.vehicle_id == Vehicle.id)
            .where(
                func.coalesce(Vehicle.society_id, Customer.society_id) == society_id,
                AddonRequest.service == "Deep Spa",
                AddonRequest.service_date.in_(days),
                Vehicle.active.is_(True),
            )
            .order_by(AddonRequest.created_at, AddonRequest.id)
        )
        .scalars()
        .all()
    )
    for addon in addons:
        # The finish-by time of an add-on is not stored yet (ADM-SCH-30).
        out.append(Demand(addon.service_date, addon.vehicle_id, "Deep Spa", None, addon.id))
    bookings = db.scalars(
        select(AddonBooking)
        .join(Vehicle, Vehicle.id == AddonBooking.vehicle_id)
        .join(Customer, Customer.id == Vehicle.customer_id)
        .where(
            func.coalesce(Vehicle.society_id, Customer.society_id) == society_id,
            AddonBooking.proposed_date.in_(days),
            AddonBooking.status.in_(("Requested", "Scheduled")),
            ~select(Job.id)
            .join(Visit, Visit.id == Job.visit_id)
            .where(
                Job.addon_booking_id == AddonBooking.id,
                Job.source_job_id.is_not(None),
                Visit.date == AddonBooking.proposed_date,
            )
            .exists(),
            Vehicle.active.is_(True),
        )
    ).all()
    for b in bookings:
        out.append(
            Demand(
                b.proposed_date,
                b.vehicle_id,
                b.service,
                minutes_of(b.finish_by),
                addon_booking_id=b.id,
            )
        )
    for job, visit in db.execute(
        select(Job, Visit)
        .join(Visit, Visit.id == Job.visit_id)
        .join(Schedule, Schedule.id == Visit.schedule_id)
        .where(
            Schedule.society_id == society_id,
            Visit.date.in_(days),
            Job.source_job_id.is_not(None),
            Job.status.in_(("Scheduled", "In progress")),
        )
    ):
        out.append(
            Demand(
                visit.date,
                visit.vehicle_id,
                job.service,
                job.finish_by_minute,
                job.addon_request_id,
                False,
                job.addon_booking_id,
                job.source_job_id,
            )
        )
    return out


def load_crew(db: Session, society_id: uuid.UUID) -> dict[uuid.UUID, SchedulingCrew]:
    from app.crew.society_moves import apply_due_moves
    from app.platform.clock import today_ist

    # Moves whose date has come take effect before the crew is read. The
    # caller's own commit keeps them.
    apply_due_moves(db, today_ist(), commit=False)
    rows = (
        db.execute(
            select(SchedulingCrew)
            .where(SchedulingCrew.society_id == society_id, SchedulingCrew.active.is_(True))
            .order_by(SchedulingCrew.id)
        )
        .scalars()
        .all()
    )
    return {c.id: c for c in rows}


def solver_crews(day_windows: dict[uuid.UUID, list[tuple[int, int]]]) -> list[SolverCrew]:
    """One solver "crew" for each working window, so a crew member with two
    windows in a day (05:00-13:00 and 17:00-19:00) is two separate time
    ranges that cannot overlap. The key is `<crew id>|<window number>`."""
    return [
        SolverCrew(f"{cid}|{i}", s, e)
        for cid, wins in day_windows.items()
        for i, (s, e) in enumerate(wins)
    ]


def crew_key_for(cid: uuid.UUID, start: int, windows: list[tuple[int, int]] | None) -> str:
    """The solver key of the window a job that starts at `start` falls in."""
    for i, (s, e) in enumerate(windows or []):
        if s <= start < e:
            return f"{cid}|{i}"
    return f"{cid}|0"


def base_crew(key: str) -> uuid.UUID:
    return uuid.UUID(key.split("|", 1)[0])


def fits_a_window(windows: list[tuple[int, int]] | None, start: int, minutes: int) -> bool:
    return any(s <= start and start + minutes <= e for s, e in windows or [])


def availability(
    db: Session, crew: dict[uuid.UUID, SchedulingCrew], days: list[date]
) -> dict[date, dict[uuid.UUID, list[tuple[int, int]]]]:
    """For each date, the working windows of every counted crew member: the
    weekday's hours (one or more slots), then the date's exception
    (ADM-CRW-04, ADM-CRW-09, ADM-CRW-25)."""
    exceptions: dict[tuple[uuid.UUID, date], SchedulingCrewException] = {}
    if crew and days:
        for ex in db.execute(
            select(SchedulingCrewException).where(
                SchedulingCrewException.crew_id.in_(list(crew)),
                SchedulingCrewException.on_date.in_(days),
            )
        ).scalars():
            exceptions[(ex.crew_id, ex.on_date)] = ex
    out: dict[date, dict[uuid.UUID, list[tuple[int, int]]]] = {}
    for day in days:
        out[day] = {}
        for cid, c in crew.items():
            ex = exceptions.get((cid, day))
            base = rules.hours_windows(
                c.working_hours, day.weekday(), c.start_minute, c.end_minute)
            windows = rules.windows_for(
                c.role, base, ex.kind if ex else None, ex.from_minute if ex else None)
            if windows:
                out[day][cid] = windows
    return out


def _clock(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def day_availability(
    crew: dict[uuid.UUID, SchedulingCrew],
    windows: dict[uuid.UUID, list[tuple[int, int]]],
    exceptions: dict[uuid.UUID, SchedulingCrewException],
    day: date,
) -> list[dict]:
    """For each crew member, the windows they can take work in on `day` and the
    reason when that is less than the weekday's hours (ADM-SCH-32)."""
    out = []
    for cid, c in crew.items():
        ex = exceptions.get(cid)
        wins = windows.get(cid, [])
        base = rules.hours_windows(c.working_hours, day.weekday(), c.start_minute, c.end_minute)
        slots = ", ".join(f"{_clock(s)}-{_clock(e)}" for s, e in wins)
        if c.role == "Trainee":
            status = "Off"
            reason = "Trainee: adds no capacity and follows the paired Member's jobs."
        elif ex and ex.kind in ("Sick", "Leave"):
            status, reason = "Off", f"{ex.kind} on this date."
        elif not base:
            status, reason = "Off", f"Day off: not a working day for {day.strftime('%A')}."
        elif ex and ex.kind == "Late start" and wins != base:
            status = "Partial"
            reason = f"Late start from {_clock(ex.from_minute or 0)}. Works {slots or 'no slot'}."
        else:
            status, reason = "Working", f"Works {slots}."
        out.append({"crew_id": cid, "status": status, "reason": reason,
                    "windows": [{"start": s, "end": e} for s, e in wins]})
    return out


def capacity(
    db: Session, society_id: uuid.UUID, start: date, end: date, schedule: Schedule | None = None
) -> list[dict]:
    """Crew minutes against the minutes of work due, for each date (ADM-CAP-01
    to ADM-CAP-04)."""
    days = daterange(start, end)
    crew = load_crew(db, society_id)
    windows = availability(db, crew, days)
    day_exceptions: dict[date, dict[uuid.UUID, SchedulingCrewException]] = {d: {} for d in days}
    if crew and days:
        for ex in db.execute(
            select(SchedulingCrewException).where(
                SchedulingCrewException.crew_id.in_(list(crew)),
                SchedulingCrewException.on_date.in_(days),
            )
        ).scalars():
            day_exceptions[ex.on_date][ex.crew_id] = ex
    names = {
        row.id: row.display_name
        for row in db.execute(
            select(Login).where(Login.id.in_([c.login_id for c in crew.values()]))
        ).scalars()
    }
    demand_minutes = dict.fromkeys(days, 0)
    lines: dict[date, dict[tuple[str, str], list[int]]] = {day: {} for day in days}
    durations = lookup.durations(db)
    for d in build_demand(db, society_id, days):
        if d.skipped:
            continue
        minutes = durations.get(d.service, d.duration)
        demand_minutes[d.day] += minutes
        source = "Add-on" if (d.addon_request_id or d.addon_booking_id) else "Subscription"
        line = lines[d.day].setdefault((d.service, source), [0, 0])
        line[0] += 1
        line[1] += minutes
    scheduled = dict.fromkeys(days, 0)
    if schedule is not None:
        rows = db.execute(
            select(Visit.date, Job.duration_minutes)
            .join(Job, Job.visit_id == Visit.id)
            .where(
                Visit.schedule_id == schedule.id, Job.crew_id.is_not(None), Job.status != "Skipped"
            )
        ).all()
        for day, minutes in rows:
            if day in scheduled:
                scheduled[day] += minutes
    out = []
    for day in days:
        cap = sum(e - s for wins in windows[day].values() for s, e in wins)
        crew_lines = [
            {
                "name": names.get(crew[cid].login_id, ""),
                "role": crew[cid].role,
                "minutes": sum(e - s for s, e in wins),
                "slots": ", ".join(f"{s // 60:02d}:{s % 60:02d}-{e // 60:02d}:{e % 60:02d}"
                                   for s, e in wins),
            }
            for cid, wins in windows[day].items()
            if wins
        ]
        crew_lines.sort(key=lambda c: c["name"])
        out.append(
            {
                "date": day,
                "crew": crew_lines,
                "availability": day_availability(crew, windows[day], day_exceptions[day], day),
                "demand": [
                    {"service": svc_name, "source": source, "jobs": n, "minutes": m}
                    for (svc_name, source), (n, m) in sorted(lines[day].items())
                ],
                "capacity_minutes": cap,
                "demand_minutes": demand_minutes[day],
                "scheduled_minutes": scheduled[day],
                "over_capacity": demand_minutes[day] > cap,
            }
        )
    return out


def release_unfit(db: Session, crew: SchedulingCrew, today: date) -> list[dict]:
    """Takes the crew member's open jobs from `today` on that no longer fit
    (the day is off, an exception, a shorter day, a Trainee, deactivated) and
    puts them on the Needs scheduling list. No unfreeze code is needed
    (ADM-CRW-12, ADM-SCH-29). Started and finished jobs stay. The caller
    commits."""
    rows = db.execute(
        select(Job, Visit, Vehicle)
        .join(Visit, Job.visit_id == Visit.id)
        .join(Vehicle, Visit.vehicle_id == Vehicle.id)
        .where(Job.crew_id == crew.id, Job.status == "Scheduled", Visit.date >= today)
        .order_by(Visit.date, Job.start_minute)
    ).all()
    if not rows:
        return []
    days = sorted({visit.date for _job, visit, _v in rows})
    windows = availability(db, {crew.id: crew}, days) if crew.active else {}
    released = []
    for job, visit, vehicle in rows:
        start = job.start_minute or 0
        if fits_a_window(windows.get(visit.date, {}).get(crew.id), start, job.duration_minutes):
            continue
        job.crew_id, job.start_minute, job.late, job.manual = None, None, False, False
        job.note = "The crew member is not available."
        released.append(
            {
                "job_id": job.id,
                "date": visit.date,
                "service": job.service,
                "vehicle_id": vehicle.id,
                "registration": vehicle.registration or "",
            }
        )
    db.flush()
    return released


def release_open_jobs(db: Session, crew: SchedulingCrew, from_date: date) -> list[dict]:
    """Takes every open (Scheduled) job of the crew member from `from_date` on
    and puts it on the Needs scheduling list. Used when the crew member moves to
    another society: those jobs belong to the old society's schedules. Started
    and finished jobs, and earlier dates, stay. The caller commits."""
    rows = db.execute(
        select(Job, Visit, Vehicle)
        .join(Visit, Job.visit_id == Visit.id)
        .join(Vehicle, Visit.vehicle_id == Vehicle.id)
        .where(Job.crew_id == crew.id, Job.status == "Scheduled", Visit.date >= from_date)
        .order_by(Visit.date, Job.start_minute)
    ).all()
    released = []
    for job, visit, vehicle in rows:
        job.crew_id, job.start_minute, job.late, job.manual = None, None, False, False
        job.note = "The crew member moved to another society."
        released.append(
            {
                "job_id": job.id,
                "date": visit.date,
                "service": job.service,
                "vehicle_id": vehicle.id,
                "registration": vehicle.registration or "",
            }
        )
    db.flush()
    return released


# ---- schedules -------------------------------------------------------------


def get_schedule(db: Session, schedule_id: uuid.UUID) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise ApiError("not_found", "That schedule does not exist.", 404)
    return schedule


def get_or_create_schedule(db: Session, society_id: uuid.UUID, start: date, days: int) -> Schedule:
    if db.get(Society, society_id) is None:
        raise ApiError("not_found", "That society does not exist.", 404)
    schedule = db.execute(
        select(Schedule).where(Schedule.society_id == society_id, Schedule.start_date == start)
    ).scalar_one_or_none()
    end = start + timedelta(days=days - 1)
    if db.scalar(
        select(Schedule.id).where(
            Schedule.society_id == society_id,
            Schedule.start_date != start,
            Schedule.start_date <= end,
            Schedule.end_date >= start,
        )
    ):
        raise ApiError("schedule_overlap", "This range overlaps an existing schedule.", 409)
    if schedule is None:
        schedule = Schedule(society_id=society_id, start_date=start, end_date=end)
        db.add(schedule)
        db.flush()
    elif schedule.status == "Draft":
        schedule.end_date = end
    return schedule


def _jobs_of(db: Session, schedule_id: uuid.UUID) -> list[tuple[Job, Visit]]:
    return list(
        db.execute(
            select(Job, Visit)
            .join(Visit, Job.visit_id == Visit.id)
            .where(Visit.schedule_id == schedule_id)
            .order_by(Visit.date, Job.id)
        ).all()
    )


def refresh_visit_status(db: Session, visit_id: uuid.UUID) -> None:
    visit = db.get(Visit, visit_id)
    statuses = db.execute(select(Job.status).where(Job.visit_id == visit_id)).scalars().all()
    visit.status = rules.visit_status(statuses)
    for job in db.scalars(
        select(Job).where(Job.visit_id == visit_id, Job.addon_booking_id.is_not(None))
    ):
        b = db.get(AddonBooking, job.addon_booking_id)
        if b is not None and b.status != "Cancelled" and visit.date == b.proposed_date:
            b.status = {
                "Completed": "Completed",
                "Could not complete": "Missed",
                "Skipped": "Missed",
            }.get(
                job.status,
                "Scheduled" if job.crew_id is not None and job.status != "Skipped" else "Requested",
            )


def service_windows(db, society_id, service, day):
    slots = lookup.working_slots(db, society_id, service)
    if not slots:
        return ((0, 1440),) if service == "Deep Spa" else ((300, 660),)
    return tuple((s.start_minute, s.end_minute) for s in slots if day.weekday() in s.days)


def run_schedule(db: Session, schedule: Schedule, admin_id: uuid.UUID | None) -> RunSummary:
    """Plan a schedule. On a Draft, every job not placed by hand is planned
    again and hand-made changes stay (ADM-SCH-14). On a Frozen schedule
    nothing moves: only jobs without a crew member are placed, without
    unfreezing (ADM-SCH-27)."""
    frozen = schedule.status == "Frozen"
    before = emit.assignment_snapshot(db, schedule)  # notify hook
    days = daterange(schedule.start_date, schedule.end_date)
    demand = build_demand(db, schedule.society_id, days)
    durations = lookup.durations(db)

    visits = {
        (v.vehicle_id, v.date, v.addon_key): v
        for v in db.execute(select(Visit).where(Visit.schedule_id == schedule.id)).scalars()
    }
    existing = {
        (
            v.vehicle_id,
            v.date,
            j.service,
            j.addon_request_id,
            j.addon_booking_id,
            j.source_job_id,
        ): j
        for j, v in _jobs_of(db, schedule.id)
    }
    wanted = set()
    for item in demand:
        key = (
            item.vehicle_id,
            item.day,
            item.service,
            item.addon_request_id,
            item.addon_booking_id,
            item.source_job_id,
        )
        wanted.add(key)
        addon_key = (
            f"redo:{item.source_job_id}"
            if item.source_job_id
            else str(item.addon_booking_id)
            if item.addon_booking_id
            else (f"legacy:{item.addon_request_id}" if item.addon_request_id else "")
        )
        visit_key = (item.vehicle_id, item.day, addon_key)
        visit = visits.get(visit_key)
        if visit is None:
            visit = Visit(
                schedule_id=schedule.id,
                vehicle_id=item.vehicle_id,
                date=item.day,
                addon_key=addon_key,
            )
            db.add(visit)
            db.flush()
            visits[visit_key] = visit
        job = existing.get(key)
        if job is None:
            db.add(
                Job(
                    visit_id=visit.id,
                    service=item.service,
                    duration_minutes=durations.get(item.service, item.duration),
                    finish_by_minute=item.finish_by,
                    addon_request_id=item.addon_request_id,
                    addon_booking_id=item.addon_booking_id,
                    source_job_id=item.source_job_id,
                    status="Skipped" if item.skipped else "Scheduled",
                )
            )
        elif not frozen or job.crew_id is None:
            job.finish_by_minute = item.finish_by
    # Work that is no longer due (a vehicle made Inactive, an add-on moved):
    # removing it needs no code (ADM-SCH-29).
    for key, job in existing.items():
        if key not in wanted and job.status == "Scheduled":
            job.status = "Skipped"
            job.crew_id, job.start_minute = None, None
    db.flush()
    for visit in list(visits.values()):
        if not db.execute(select(Job.id).where(Job.visit_id == visit.id).limit(1)).first():
            db.delete(visit)
    db.flush()

    crew = load_crew(db, schedule.society_id)
    windows = availability(db, crew, days)
    rows = _jobs_of(db, schedule.id)
    by_day: dict[date, list[tuple[Job, Visit]]] = {}
    for job, visit in rows:
        by_day.setdefault(visit.date, []).append((job, visit))

    # Where each job sits now, to renumber only the crew days that change (S-13).
    before_place = {job.id: (job.crew_id, job.start_minute, visit.date) for job, visit in rows}

    for day, items in by_day.items():
        day_windows = windows.get(day, {})
        free: list[tuple[Job, Visit]] = []
        solver_jobs: list[SolverJob] = []
        for job, visit in items:
            if job.status == "Skipped":
                continue
            if job.status != "Scheduled" and job.crew_id not in day_windows:
                continue
            if job.crew_id is not None and job.crew_id not in day_windows:
                # The crew member is away that day: the job goes back to the pool.
                job.crew_id, job.start_minute, job.manual = None, None, False
            if not frozen and not job.manual and job.status == "Scheduled":
                job.crew_id, job.start_minute, job.late, job.note = None, None, False, ""
            if job.crew_id is None and job.manual:
                job.note = "Taken off the schedule by the admin."
                continue
            if job.crew_id is None and job.status != "Scheduled":
                continue
            fixed = None
            if job.crew_id is not None:
                at = job.start_minute or 0
                fixed = (crew_key_for(job.crew_id, at, day_windows.get(job.crew_id)), at)
            else:
                free.append((job, visit))
            slots = service_windows(db, schedule.society_id, job.service, day)
            if (
                fixed is None
                and (frozen or job.addon_booking_id is not None)
                and job.finish_by_minute is not None
            ):
                slots = tuple((s, min(e, job.finish_by_minute)) for s, e in slots)
            solver_jobs.append(
                SolverJob(
                    str(job.id),
                    str(visit.vehicle_id),
                    job.duration_minutes,
                    job.finish_by_minute,
                    fixed,
                    slots,
                )
            )
        if not solver_jobs:
            continue
        result = solve_day(solver_crews(day_windows), solver_jobs)
        for job, _visit in items:
            key = str(job.id)
            if key in result.placed:
                crew_key, start = result.placed[key]
                job.crew_id = base_crew(crew_key)
                job.start_minute = start
                job.note = ""
            elif key in result.unplaced:
                job.crew_id, job.start_minute = None, None
                job.note = result.unplaced[key]
            job.late = key in result.late
    db.flush()
    touched: set = set()
    for job, visit in rows:
        old = before_place[job.id]
        if (job.crew_id, job.start_minute) != old[:2] or (
            job.crew_id is not None and job.sequence is None
        ):
            touched.add((job.crew_id, visit.date))
            touched.add((old[0], old[2]))
        if job.crew_id is None or job.status == "Skipped":
            job.sequence = None
    queue.resequence_all(db, touched)
    for _job, visit in rows:
        refresh_visit_status(db, visit.id)

    all_jobs = [j for j, _v in _jobs_of(db, schedule.id)]
    summary = RunSummary(
        schedule_id=schedule.id,
        society_id=schedule.society_id,
        status=schedule.status,
        placed=sum(1 for j in all_jobs if j.crew_id is not None and j.status != "Skipped"),
        unscheduled=sum(1 for j in all_jobs if j.crew_id is None and j.status == "Scheduled"),
        late=sum(1 for j in all_jobs if j.late),
    )
    record(
        db,
        schedule.id,
        admin_id,
        "assign-late" if frozen else "rerun",
        f"placed {summary.placed}, unscheduled {summary.unscheduled}, late {summary.late}",
    )
    db.commit()
    emit.late_assignments(db, schedule, before)  # notify hook
    return summary


def run(
    db: Session,
    society_id: uuid.UUID | None,
    start: date,
    days: int | None,
    admin_id: uuid.UUID | None,
) -> list[RunSummary]:
    """Start scheduling for one society, or all active societies (ADM-SCH-01)."""
    if days is None:
        import calendar

        period = lookup.setting(db, "schedule.period")
        if period == "Daily":
            days = 1
        elif period == "Monthly":
            start = start.replace(day=1)
            days = calendar.monthrange(start.year, start.month)[1]
        else:
            week_start = lookup.setting(db, "schedule.week_start")
            start -= timedelta(days=(start.weekday() - week_start) % 7)
            days = 7
    if society_id is not None:
        society_ids = [society_id]
    else:
        society_ids = list(
            db.execute(
                select(Society.id).where(Society.active.is_(True)).order_by(Society.name)
            ).scalars()
        )
    out = []
    for sid in society_ids:
        schedule = get_or_create_schedule(db, sid, start, days)
        out.append(run_schedule(db, schedule, admin_id))
    return out


# ---- manual changes and the freeze ----------------------------------------


def _s(value) -> str | None:
    return None if value is None else str(value)


def move_job(
    db: Session,
    job_id: uuid.UUID,
    crew_id: uuid.UUID | None,
    start_minute: int | None,
    admin_id: uuid.UUID | None,
    commit: bool = True,
) -> Job:
    """Place a job by hand, or take it off its crew member (ADM-SCH-13).
    On a Frozen schedule only taking it off is allowed (ADM-SCH-29); adding or
    moving needs the schedule unfrozen with the code (ADM-SCH-17)."""
    job = db.get(Job, job_id)
    if job is None:
        raise ApiError("not_found", "That job does not exist.", 404)
    visit = db.get(Visit, job.visit_id)
    schedule = db.get(Schedule, visit.schedule_id)
    if job.status != "Scheduled":
        raise ApiError("job_not_open", "That job has already started or finished.", 409)
    if crew_id is None:
        previous_crew_id = job.crew_id  # notify hook
        before = (job.crew_id, job.start_minute)
        job.crew_id, job.start_minute, job.late = None, None, False
        job.sequence, job.queue_unlocked = None, False
        queue.resequence_all(db, {(previous_crew_id, visit.date)})
        job.manual = True
        job.note = "Taken off the schedule by the admin."
        record(db, schedule.id, admin_id, "move", f"job {job.id} taken off", {
            "job": str(job.id), "crew_id": [_s(before[0]), None],
            "start_minute": [before[1], None]})
        if commit:
            db.commit()
            emit.job_taken_off(db, job, previous_crew_id)
        else:
            db.flush()
        return job
    if schedule.status == "Frozen":
        raise ApiError(
            "schedule_frozen",
            "This schedule is frozen. Unfreeze it with the code to move work.",
            409,
        )
    if start_minute is None:
        raise ApiError(
            "validation_failed", "Please give a start time.", 422, {"start_minute": "Required."}
        )
    crew = load_crew(db, schedule.society_id)
    member = crew.get(crew_id)
    if member is None:
        raise ApiError("crew_not_found", "That crew member is not in this society.", 404)
    windows = availability(db, {crew_id: member}, [visit.date])[visit.date].get(crew_id)
    if not windows:
        raise ApiError("crew_unavailable", "That crew member is not working that day.", 409)
    if not fits_a_window(windows, start_minute, job.duration_minutes):
        raise ApiError("outside_hours", "That time is outside the crew member's hours.", 409)
    if not any(
        s <= start_minute and start_minute + job.duration_minutes <= e
        for s, e in service_windows(db, schedule.society_id, job.service, visit.date)
    ):
        raise ApiError("outside_slot", "That time is outside this service's working slots.", 409)
    end = start_minute + job.duration_minutes
    others = db.execute(
        select(Job, Visit)
        .join(Visit, Job.visit_id == Visit.id)
        .where(
            Visit.schedule_id == schedule.id,
            Visit.date == visit.date,
            Job.id != job.id,
            Job.crew_id.is_not(None),
            Job.status != "Skipped",
        )
    ).all()
    for other, other_visit in others:
        if other.crew_id != crew_id and other_visit.vehicle_id != visit.vehicle_id:
            continue
        o_start = other.start_minute or 0
        if start_minute < o_start + other.duration_minutes and o_start < end:
            raise ApiError("overlap", "That time overlaps another job.", 409)
    before = (job.crew_id, job.start_minute)
    old_crew_id = job.crew_id
    job.crew_id, job.start_minute, job.manual, job.note = crew_id, start_minute, True, ""
    job.late = job.finish_by_minute is not None and end > job.finish_by_minute
    job.queue_unlocked = False
    # The moved job takes its place by start time on its new day (Derived).
    queue.resequence_all(db, {(crew_id, visit.date), (old_crew_id, visit.date)})
    record(db, schedule.id, admin_id, "move", f"job {job.id} to {rules.hhmm(start_minute)}", {
        "job": str(job.id), "crew_id": [_s(before[0]), str(crew_id)],
        "start_minute": [before[1], start_minute]})
    refresh_visit_status(db, visit.id)
    if commit:
        db.commit()
    else:
        db.flush()
    return job


def reconcile_vehicle(db: Session, vehicle_id: uuid.UUID) -> None:
    """Reconcile existing future schedules only; never starts an unplanned period."""
    from app.platform.clock import today_ist

    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return
    owner = db.get(Customer, vehicle.customer_id)
    society_id = vehicle.society_id or owner.society_id
    schedules = list(
        db.scalars(
            select(Schedule)
            .where(Schedule.society_id == society_id, Schedule.end_date >= today_ist())
            .order_by(Schedule.start_date)
        )
    )
    for schedule in schedules:
        run_schedule(db, schedule, None)


def freeze(db: Session, schedule: Schedule, admin_id: uuid.UUID | None) -> Schedule:
    if schedule.status == "Frozen":
        raise ApiError("already_frozen", "This schedule is already frozen.", 409)
    schedule.status = "Frozen"
    schedule.frozen_at = utcnow()
    schedule.frozen_by = admin_id
    record(db, schedule.id, admin_id, "freeze")
    db.commit()
    emit.schedules_frozen(db, [schedule.id])  # notify hook
    return schedule


def unfreeze(db: Session, schedule: Schedule, code: str, admin_id: uuid.UUID | None) -> Schedule:
    if code != lookup.unfreeze_code(db):
        raise ApiError("wrong_code", "That code is not right.", 403)
    if schedule.status != "Frozen":
        raise ApiError("not_frozen", "This schedule is not frozen.", 409)
    schedule.status = "Draft"
    schedule.frozen_at = None
    schedule.frozen_by = None
    record(db, schedule.id, admin_id, "unfreeze")
    db.commit()
    return schedule


def freeze_due(db: Session, now: datetime) -> list[uuid.UUID]:
    """Freeze every Draft whose freeze cutoff time has passed (ADM-SCH-25)."""
    frozen = []
    hour = lookup.setting(db, "schedule.freeze_hour")
    drafts = db.execute(select(Schedule).where(Schedule.status == "Draft")).scalars().all()
    for schedule in drafts:
        if now >= rules.freeze_deadline(schedule.start_date, hour):
            schedule.status = "Frozen"
            schedule.frozen_at = utcnow()
            record(db, schedule.id, None, "freeze", "at the freeze cutoff time")
            frozen.append(schedule.id)
    db.commit()
    emit.schedules_frozen(db, frozen)  # notify hook
    return frozen


def set_job_status(db: Session, job_id: uuid.UUID, status: str) -> Job:
    """Used by the crew module when a job starts, finishes or cannot complete."""
    job = db.get(Job, job_id)
    if job is None:
        raise ApiError("not_found", "That job does not exist.", 404)
    job.status = status
    db.flush()
    refresh_visit_status(db, job.visit_id)
    db.commit()
    emit.job_status_changed(db, job)  # notify hook
    return job


# ---- reads -----------------------------------------------------------------


def vehicle_label(v: Vehicle) -> str:
    return " ".join(p for p in (v.make, v.model) if p)


def _job_dict(
    job: Job,
    visit: Visit,
    vehicle: Vehicle,
    customer: Customer | None,
    crew_name: str | None,
    schedule: Schedule,
) -> dict:
    end = None if job.start_minute is None else job.start_minute + job.duration_minutes
    return {
        "id": job.id,
        "visit_id": visit.id,
        "schedule_id": schedule.id,
        "schedule_status": schedule.status,
        "date": visit.date,
        "vehicle_id": vehicle.id,
        "registration": vehicle.registration or "",
        "vehicle": vehicle_label(vehicle),
        "parking": "-".join(p for p in (vehicle.parking_basement, vehicle.parking_number) if p),
        "customer_name": (
            f"{customer.first_name} {customer.last_name}".strip() if customer else ""
        ),
        "service": job.service,
        "status": job.status,
        "duration_minutes": job.duration_minutes,
        "crew_id": job.crew_id,
        "crew_name": crew_name,
        "start_minute": job.start_minute,
        "start_time": rules.hhmm(job.start_minute),
        "end_time": rules.hhmm(end),
        "finish_by": rules.hhmm(job.finish_by_minute),
        "late": job.late,
        "manual": job.manual,
        "reason": job.note,
        "sequence": job.sequence,
        "queue_unlocked": job.queue_unlocked,
        "visit_outcome": "Scheduled",
        "planned_services": [],
        "delivered_services": [],
    }


def _moved_dates(db: Session, result: list[dict]) -> None:
    """S-05: a Skipped job with a follow-up job was moved. Show both dates."""
    ids = [r["id"] for r in result]
    if not ids:
        return
    follow = db.execute(
        select(Job.source_job_id, Visit.date)
        .join(Visit, Visit.id == Job.visit_id)
        .where(Job.source_job_id.in_(ids))
    ).all()
    to_date = dict(follow)
    sources = {
        j.id: (j.status, v.date)
        for j, v in db.execute(
            select(Job, Visit).join(Visit, Visit.id == Job.visit_id).where(
                Job.id.in_(select(Job.source_job_id).where(Job.id.in_(ids))))
        ).all()
    }
    parent = dict(db.execute(
        select(Job.id, Job.source_job_id).where(Job.id.in_(ids), Job.source_job_id.is_not(None))
    ).all())
    for r in result:
        if r["status"] == "Skipped" and r["id"] in to_date:
            r["moved_to_date"] = to_date[r["id"]]
        src = sources.get(parent.get(r["id"]))
        if src and src[0] == "Skipped":
            r["moved_from_date"] = src[1]


def job_rows(db: Session, *where) -> list[dict]:
    rows = db.execute(
        select(Job, Visit, Vehicle, Customer, Schedule, Login.display_name)
        .join(Visit, Job.visit_id == Visit.id)
        .join(Schedule, Visit.schedule_id == Schedule.id)
        .join(Vehicle, Visit.vehicle_id == Vehicle.id)
        .join(Customer, Vehicle.customer_id == Customer.id)
        .outerjoin(SchedulingCrew, Job.crew_id == SchedulingCrew.id)
        .outerjoin(Login, SchedulingCrew.login_id == Login.id)
        .where(*where)
        .order_by(Visit.date, Job.start_minute.is_(None), Job.start_minute, Vehicle.id, Job.service)
    ).all()
    result = [_job_dict(j, v, veh, c, name, s) for j, v, veh, c, s, name in rows]
    on = parking_slots(db, [(veh, v.date) for _, v, veh, *_ in rows])
    for r, (_, v, veh, *_) in zip(result, rows, strict=True):
        r["parking"] = parking_label(on[(veh.id, v.date)])
    from app.scheduling.outcomes import visit_outcomes

    derived = visit_outcomes(db, {r["visit_id"] for r in result})
    _moved_dates(db, result)
    for r in result:
        d = derived[r["visit_id"]]
        r["visit_outcome"], r["planned_services"], r["delivered_services"] = (
            d.outcome, d.planned, d.delivered)
    return result


def schedule_summary(db: Session, schedule: Schedule) -> dict:
    """A schedule's dates, status and freeze deadline (ADM-SCH-11, ADM-SCH-16)."""
    society = db.get(Society, schedule.society_id)
    return {
        "id": schedule.id,
        "society_id": schedule.society_id,
        "society_name": society.name if society else "",
        "start_date": schedule.start_date,
        "end_date": schedule.end_date,
        "status": schedule.status,
        "frozen_at": schedule.frozen_at,
        "freeze_deadline": rules.freeze_deadline(
            schedule.start_date, lookup.setting(db, "schedule.freeze_hour")
        ),
    }


def schedules_of(db: Session, society_id: uuid.UUID, date_from: date | None) -> list[dict]:
    """The schedules of a society that end on or after `date_from`, oldest
    first, so the Board can offer all their days (ADM-SCH-35)."""
    q = select(Schedule).where(Schedule.society_id == society_id)
    if date_from is not None:
        q = q.where(Schedule.end_date >= date_from)
    return [schedule_summary(db, s) for s in db.scalars(q.order_by(Schedule.start_date))]


def board(db: Session, schedule: Schedule) -> dict:
    crew = load_crew(db, schedule.society_id)
    names = {
        row.id: row.display_name
        for row in db.execute(
            select(Login).where(Login.id.in_([c.login_id for c in crew.values()]))
        ).scalars()
    }
    return {
        "schedule": schedule_summary(db, schedule),
        "days": capacity(db, schedule.society_id, schedule.start_date, schedule.end_date, schedule),
        "crew": [
            {
                "id": c.id,
                "name": names.get(c.login_id, ""),
                "role": c.role,
                "start_minute": c.start_minute,
                "end_minute": c.end_minute,
            }
            for c in crew.values()
        ],
        "jobs": job_rows(db, Visit.schedule_id == schedule.id),
    }


def skipped_jobs(
    db: Session, society_id: uuid.UUID, date_from: date, date_to: date
) -> list[dict]:
    """Skipped jobs of a society between two dates, each with whether it was
    paused or skipped and by whom (ADM-SCH-36)."""
    from app.visits.models import JobOutcome, OperationsDecision

    rows = job_rows(
        db,
        Schedule.society_id == society_id,
        Job.status == "Skipped",
        Visit.date >= date_from,
        Visit.date <= date_to,
    )
    if not rows:
        return rows
    ids = [r["id"] for r in rows]
    decided = set(db.scalars(
        select(OperationsDecision.job_id).where(
            OperationsDecision.job_id.in_(ids), OperationsDecision.action == "Skip")))
    by_crew = set(db.scalars(
        select(JobOutcome.job_id).where(JobOutcome.job_id.in_(ids), JobOutcome.kind == "skipped")))
    changes = db.scalars(
        select(ScheduleChange).where(
            ScheduleChange.vehicle_id.in_({r["vehicle_id"] for r in rows}),
            ScheduleChange.kind.in_(("skip", "pause")),
            ScheduleChange.status.in_(("Active", "Applied")),
            ScheduleChange.start_date <= date_to,
            ScheduleChange.end_date >= date_from,
        ).order_by(ScheduleChange.created_at)
    ).all()
    for r in rows:
        change = next((c for c in reversed(changes) if c.vehicle_id == r["vehicle_id"]
                       and c.start_date <= r["date"] <= c.end_date), None)
        if change is not None:
            who = "the admin" if change.actor == "admin" else "the customer"
            r["skip_kind"] = "Paused" if change.kind == "pause" else "Skipped"
            r["skip_reason"] = (
                f"Paused by {who}, {change.start_date:%d-%b-%y} to {change.end_date:%d-%b-%y}"
                if change.kind == "pause" else f"Skipped by {who}")
        elif r["id"] in decided:
            r["skip_kind"], r["skip_reason"] = "Skipped", "Skipped by operations"
        elif r["id"] in by_crew:
            r["skip_kind"], r["skip_reason"] = "Skipped", "Skipped by a crew manager"
        else:
            r["skip_kind"] = "Skipped"
            r["skip_reason"] = "No longer due (subscription, vehicle or add-on changed)"
    return rows


def needs_scheduling(db: Session, society_id: uuid.UUID | None) -> list[dict]:
    """Jobs with no crew member: Unscheduled in a draft, or on the Needs
    scheduling list of a frozen schedule (ADM-SCH-08, ADM-SCH-28)."""
    where = [Job.crew_id.is_(None), Job.status == "Scheduled"]
    if society_id is not None:
        where.append(Schedule.society_id == society_id)
    return job_rows(db, *where)


def customer_next_job(db: Session, login_id: uuid.UUID, from_date: date) -> dict | None:
    """The next open job on the customer's vehicles, from frozen schedules only:
    a customer sees the assigned crew member and time once it is assigned
    (CAL-10)."""
    customer = db.execute(
        select(Customer).where(Customer.login_id == login_id)
    ).scalar_one_or_none()
    if customer is None:
        return None
    rows = job_rows(
        db,
        Vehicle.customer_id == customer.id,
        Visit.date >= from_date,
        Schedule.status == "Frozen",
        Job.status.in_(("Scheduled", "In progress")),
    )
    return rows[0] if rows else None


def crew_day(db: Session, login_id: uuid.UUID, day: date) -> dict:
    """A crew member's jobs for one date, from frozen schedules only
    (CRW-SCH-11). A Trainee sees the paired Member's jobs (CRW-SCH-10)."""
    me = db.execute(
        select(SchedulingCrew).where(SchedulingCrew.login_id == login_id)
    ).scalar_one_or_none()
    empty = {"date": day, "society": "", "total": 0, "done": 0, "left": 0, "jobs": []}
    if me is None:
        return empty
    society = db.get(Society, me.society_id)
    empty["society"] = society.name if society else ""
    target = me.id
    if me.role == "Trainee":
        if me.paired_member_id is None:
            return empty
        target = me.paired_member_id
    rows = db.execute(
        select(Job, Visit, Vehicle)
        .join(Visit, Job.visit_id == Visit.id)
        .join(Schedule, Visit.schedule_id == Schedule.id)
        .join(Vehicle, Visit.vehicle_id == Vehicle.id)
        .where(Job.crew_id == target, Visit.date == day, Schedule.status == "Frozen")
    ).all()
    rows.sort(key=lambda r: queue._order_key((r[0], r[1])))
    states = queue.states_for(db, [r[0] for r in rows])
    jobs = []
    on = parking_slots(db, [(vehicle, day) for _, _, vehicle in rows])
    for job, visit, vehicle in rows:
        state = states.get(job.id)
        end = None if job.start_minute is None else job.start_minute + job.duration_minutes
        jobs.append(
            {
                "id": job.id,
                "visit_id": visit.id,
                "vehicle_id": vehicle.id,
                "registration": vehicle.registration or "",
                "make": vehicle.make,
                "model": vehicle.model,
                "category": vehicle.category,
                "parking_basement": on[(vehicle.id, day)][0],
                "parking_number": on[(vehicle.id, day)][1],
                "society": empty["society"],
                "service": job.service,
                "status": job.status,
                "start_time": rules.hhmm(job.start_minute),
                "end_time": rules.hhmm(end),
                "finish_by": rules.hhmm(job.finish_by_minute),
                "sequence": job.sequence,
                "locked": bool(state and state.locked),
                "current": bool(state and state.current),
            }
        )
    done = sum(1 for j in jobs if j["status"] in DAY_DONE)
    empty.update(total=len(jobs), done=done, left=len(jobs) - done, jobs=jobs)
    return empty
