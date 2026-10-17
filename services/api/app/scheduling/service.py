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
from app.directory import lookup
from app.directory.models import Plan, Society
from app.identity.models import Login
from app.notifications import emit  # notify hook
from app.platform.db import utcnow
from app.platform.errors import ApiError
from app.scheduling import rules
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
    db: Session, schedule_id: uuid.UUID, admin_id: uuid.UUID | None, kind: str, detail: str = ""
) -> None:
    db.add(
        SchedulingEvent(schedule_id=schedule_id, admin_login_id=admin_id, kind=kind, detail=detail)
    )
    if admin_id:
        from app.directory.service import audit

        audit(db, admin_id, "schedule", schedule_id, kind, {"detail": detail})


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


def availability(
    db: Session, crew: dict[uuid.UUID, SchedulingCrew], days: list[date]
) -> dict[date, dict[uuid.UUID, tuple[int, int]]]:
    """For each date, the working window of every counted crew member: the
    weekday's hours, then the date's exception (ADM-CRW-04, ADM-CRW-09)."""
    exceptions: dict[tuple[uuid.UUID, date], SchedulingCrewException] = {}
    if crew and days:
        for ex in db.execute(
            select(SchedulingCrewException).where(
                SchedulingCrewException.crew_id.in_(list(crew)),
                SchedulingCrewException.on_date.in_(days),
            )
        ).scalars():
            exceptions[(ex.crew_id, ex.on_date)] = ex
    out: dict[date, dict[uuid.UUID, tuple[int, int]]] = {}
    for day in days:
        out[day] = {}
        for cid, c in crew.items():
            ex = exceptions.get((cid, day))
            base = rules.hours_window(c.working_hours, day.weekday(), c.start_minute, c.end_minute)
            if base is None:
                continue
            window = rules.window_for(
                c.role, base[0], base[1], ex.kind if ex else None, ex.from_minute if ex else None
            )
            if window is not None:
                out[day][cid] = window
    return out


def capacity(
    db: Session, society_id: uuid.UUID, start: date, end: date, schedule: Schedule | None = None
) -> list[dict]:
    """Crew minutes against the minutes of work due, for each date (ADM-CAP-01
    to ADM-CAP-04)."""
    days = daterange(start, end)
    crew = load_crew(db, society_id)
    windows = availability(db, crew, days)
    demand_minutes = dict.fromkeys(days, 0)
    durations = lookup.durations(db)
    for d in build_demand(db, society_id, days):
        if d.skipped:
            continue
        demand_minutes[d.day] += durations.get(d.service, d.duration)
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
        cap = sum(e - s for s, e in windows[day].values())
        out.append(
            {
                "date": day,
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
        window = windows.get(visit.date, {}).get(crew.id)
        start = job.start_minute or 0
        if window is not None and start >= window[0] and start + job.duration_minutes <= window[1]:
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
                fixed = (str(job.crew_id), job.start_minute or 0)
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
        crew_in = [SolverCrew(str(cid), s, e) for cid, (s, e) in day_windows.items()]
        result = solve_day(crew_in, solver_jobs)
        for job, _visit in items:
            key = str(job.id)
            if key in result.placed:
                crew_key, start = result.placed[key]
                job.crew_id = uuid.UUID(crew_key)
                job.start_minute = start
                job.note = ""
            elif key in result.unplaced:
                job.crew_id, job.start_minute = None, None
                job.note = result.unplaced[key]
            job.late = key in result.late
    db.flush()
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
        job.crew_id, job.start_minute, job.late = None, None, False
        job.manual = True
        job.note = "Taken off the schedule by the admin."
        record(db, schedule.id, admin_id, "move", f"job {job.id} taken off")
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
    window = availability(db, {crew_id: member}, [visit.date])[visit.date].get(crew_id)
    if window is None:
        raise ApiError("crew_unavailable", "That crew member is not working that day.", 409)
    if start_minute < window[0] or start_minute + job.duration_minutes > window[1]:
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
    job.crew_id, job.start_minute, job.manual, job.note = crew_id, start_minute, True, ""
    job.late = job.finish_by_minute is not None and end > job.finish_by_minute
    record(db, schedule.id, admin_id, "move", f"job {job.id} to {rules.hhmm(start_minute)}")
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
    }


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
    return [_job_dict(j, v, veh, c, name, s) for j, v, veh, c, s, name in rows]


def board(db: Session, schedule: Schedule) -> dict:
    society = db.get(Society, schedule.society_id)
    crew = load_crew(db, schedule.society_id)
    names = {
        row.id: row.display_name
        for row in db.execute(
            select(Login).where(Login.id.in_([c.login_id for c in crew.values()]))
        ).scalars()
    }
    return {
        "schedule": {
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
        },
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
        .order_by(Job.start_minute, Job.id)
    ).all()
    jobs = []
    for job, visit, vehicle in rows:
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
                "parking_basement": vehicle.parking_basement,
                "parking_number": vehicle.parking_number,
                "society": empty["society"],
                "service": job.service,
                "status": job.status,
                "start_time": rules.hhmm(job.start_minute),
                "end_time": rules.hhmm(end),
                "finish_by": rules.hhmm(job.finish_by_minute),
            }
        )
    done = sum(1 for j in jobs if j["status"] in DAY_DONE)
    empty.update(total=len(jobs), done=done, left=len(jobs) - done, jobs=jobs)
    return empty
