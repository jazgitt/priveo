"""SCHS-07: builders for scheduler scenario tests.

A scenario is a few lines on top of the `world` fixture:

    sc = Scenario(world)
    sc.slots(off=[6])                        # weekly off: Sunday has no slot
    sc.cleaner("Ravi", shift=(360, 600), zone="A")
    car = sc.car(zone="A", cutoff=time(9))
    sc.entitlement(car, SUNDAY)
    res = sc.run(SUNDAY, days=2)
    assert res.placed_on(SUNDAY, car) and not res.unassigned

Everything here builds against tables and fields that exist today. Where a
rule has no storage yet, a method says so in a `# EXTENSION POINT` comment and
uses the nearest thing that works; later stories replace the body, not the
call. Defaults come from the registry and `directory.defaults`, not from
numbers written here.
"""
from dataclasses import dataclass, field
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Subscription, Vehicle
from app.directory import defaults, lookup, settings_registry, site_settings
from app.directory.models import Plan, Society, WorkingSlot, Zone
from app.scheduling import service
from app.scheduling.models import (
    BreakRule,
    InteriorEntitlement,
    Job,
    Schedule,
    ScheduleFinding,
    SchedulingCrew,
    SchedulingCrewException,
    SocietySetting,
    Visit,
)

WEEKDAYS = defaults.WEEKDAYS  # Monday first, as `working_slots.days` counts them
ALL_DAYS = list(range(7))
EXTERNAL, INTERNAL = "Cleaning-External", "Cleaning-Internal"


def set_site_values(db: Session, society_id, values: dict) -> dict:
    """Save site settings through the SCHS-02 layer. Returns the site's own
    values as they were (key -> value or None), for `restore_site_values`."""
    from app.directory import rule_seed

    rule_seed.seed_rule_keys(db)  # the global defaults a site falls back to
    db.commit()
    before = {k: site_settings.own_value(db, society_id, k) for k in values}
    for key, raw in values.items():
        site_settings.write(db, society_id, key, raw, None)
    lookup.invalidate()
    return before


def restore_site_values(db: Session, society_id, before: dict) -> None:
    for key, old in before.items():
        if old is None:
            row = db.scalar(select(SocietySetting).where(
                SocietySetting.society_id == society_id, SocietySetting.key == key))
            if row is not None:
                db.delete(row)
        else:
            site_settings.write(db, society_id, key, old, None)
    db.commit()
    lookup.invalidate()


@dataclass
class Placed:
    day: date
    vehicle_id: object
    service: str
    crew_id: object
    start: int
    duration: int
    late: bool
    manual: bool


@dataclass
class Unassigned:
    day: date
    vehicle_id: object
    service: str
    reason_code: str | None  # None until SCHS-21 writes codes on the job
    note: str  # today's wording


@dataclass
class Result:
    """What a run did, read back from the database."""
    summary: object
    placed: list[Placed] = field(default_factory=list)
    unassigned: list[Unassigned] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)  # codes (schedule_findings)

    def placed_on(self, day, car=None, service=None) -> list[Placed]:
        return [p for p in self.placed if p.day == day
                and (car is None or p.vehicle_id == car.id)
                and (service is None or p.service == service)]

    def reasons(self) -> list[str | None]:
        return [u.reason_code for u in self.unassigned]


class Scenario:
    """Builds one site's world for a scenario. Wraps the `world` fixture."""

    def __init__(self, world):
        self.world = world
        self.db: Session = world.db
        self.site: Society = world.society
        self.zones: dict[str, Zone] = {}
        self.cleaners: dict[str, SchedulingCrew] = {}

    # ---- site ---------------------------------------------------------

    def add_site(self, name: str) -> Society:
        """Another site. Cars follow their customer's society, so a car on a
        second site needs a second customer: EXTENSION POINT, not built."""
        site = Society(name=name)
        self.db.add(site)
        self.db.flush()
        return site

    def slots(self, services=(EXTERNAL, INTERNAL), start=None, end=None, off=(), site=None):
        """Working slots for the site. `off` is the weekly off: those weekdays
        (Monday 0) get no slot. Start and end default to the seeded windows.
        EXTENSION POINT: there is no weekly-off field on the site yet; when
        one exists, set it here instead of leaving the day out."""
        site = site or self.site
        days = [d for d in ALL_DAYS if d not in off]
        for service_name in services:
            s, e, _days = defaults.DEFAULT_SLOT_WINDOWS[service_name]
            self.db.add(WorkingSlot(society_id=site.id, service=service_name,
                                    start_minute=s if start is None else start,
                                    end_minute=e if end is None else end, days=days))
        self.db.flush()
        return self

    def zone(self, name: str) -> Zone:
        if name not in self.zones:
            zone = Zone(society_id=self.site.id, name=name)
            self.db.add(zone)
            self.db.flush()
            self.zones[name] = zone
        return self.zones[name]

    def config(self, **values):
        """Site settings by key with dots as underscores:
        config(site_break_start_minute=600) sets site.break_start_minute.
        Use the `site_cfg` fixture instead when the test should restore them."""
        set_site_values(self.db, self.site.id, {_key(k): v for k, v in values.items()})
        return self

    # ---- cleaners -----------------------------------------------------

    def cleaner(self, name="Ravi", shift=None, zone=None, role="Member", days=None,
                reporting=None, first_job=None, paired=None) -> SchedulingCrew:
        """A cleaner. `shift` is (start, end) minutes; it defaults to the model
        default. `days` limits the weekdays worked (Monday 0). `zone` is the
        home zone name. `reporting` and `first_job` are the per-crew minutes."""
        member = self.world.add_crew(name=name, role=role, paired=paired,
                                     **({"start": shift[0], "end": shift[1]} if shift else {}))
        if days is not None:
            s, e = member.start_minute, member.end_minute
            member.working_hours = [
                {"day": WEEKDAYS[i], "working": i in days, "start": s, "end": e}
                for i in ALL_DAYS]
        if zone:
            member.home_zone_id = self.zone(zone).id
        member.reporting_minute, member.first_job_minute = reporting, first_job
        self.db.flush()
        self.cleaners[name] = member
        return member

    def exception(self, cleaner: SchedulingCrew, day: date, kind="Sick", from_minute=None):
        """A crew exception: Sick, Leave or Late start (with from_minute)."""
        row = SchedulingCrewException(crew_id=cleaner.id, on_date=day, kind=kind,
                                      from_minute=from_minute)
        self.db.add(row)
        self.db.flush()
        return row

    def break_rule(self, start: date, end: date, cleaner=None, minutes=None, enabled=True):
        """A break rule for a date range: site-wide, or one cleaner's.
        `minutes` is (start, end), or None to use the site break."""
        row = BreakRule(society_id=self.site.id, crew_id=cleaner.id if cleaner else None,
                        start_date=start, end_date=end, enabled=enabled,
                        start_minute=minutes[0] if minutes else None,
                        end_minute=minutes[1] if minutes else None)
        self.db.add(row)
        self.db.flush()
        return row

    # ---- cars and entitlements ---------------------------------------

    def car(self, zone=None, cutoff: time | None = None, interior_day=None,
            status="Active", interior=None) -> Vehicle:
        """A subscribed car. `zone` is a zone name of the site. At rules version 2
        every plan with Interior care owes an Interior each service week (SCHS-36),
        so a car is on an Exterior-only plan unless it names an `interior_day` or
        `interior=True`; scenarios about Exteriors then see no Interior."""
        vehicle = self.world.add_vehicle(cutoff=cutoff, interior_day=interior_day, status=status)
        if not (interior if interior is not None else interior_day):
            self._exterior_only(vehicle)
        if zone:
            vehicle.zone_id = self.zone(zone).id
        self.db.flush()
        return vehicle

    def _exterior_only(self, vehicle: Vehicle) -> None:
        plan = self.db.scalar(select(Plan).where(Plan.name == "Exterior only (test)"))
        if plan is None:
            plan = Plan(name="Exterior only (test)", monthly_price_rupees=999,
                        includes_interior=False)
            self.db.add(plan)
            self.db.flush()
        sub = self.db.scalar(select(Subscription).where(Subscription.vehicle_id == vehicle.id))
        sub.plan_id = plan.id

    def cars(self, n: int, **kw) -> list[Vehicle]:
        return [self.car(**kw) for _ in range(n)]

    def entitlement(self, car: Vehicle, week_start: date, seq=1, status="Pending",
                    waived_reason=None) -> InteriorEntitlement:
        """One Interior owed to a car for a service week (interior_entitlements)."""
        sub = self.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
        row = InteriorEntitlement(subscription_id=sub.id if sub else None, vehicle_id=car.id,
                                  service_week_start=week_start, seq=seq, status=status,
                                  waived_reason=waived_reason)
        self.db.add(row)
        self.db.flush()
        return row

    # ---- placements ---------------------------------------------------

    def fixed(self, car: Vehicle, day: date, cleaner: SchedulingCrew, start: int,
              service_name=EXTERNAL, duration=None, schedule_start=None, days=1) -> Job:
        """A job placed by hand (manual): a re-run keeps it. It lives in the
        draft schedule starting on `schedule_start` (default `day`) for `days`;
        call `run` with the same start and days so it finds that schedule."""
        schedule = service.get_or_create_schedule(
            self.db, self.site.id, schedule_start or day, days)
        visit = self.db.scalar(select(Visit).where(
            Visit.schedule_id == schedule.id, Visit.vehicle_id == car.id,
            Visit.date == day, Visit.addon_key == ""))
        if visit is None:
            visit = Visit(schedule_id=schedule.id, vehicle_id=car.id, date=day)
            self.db.add(visit)
            self.db.flush()
        job = Job(visit_id=visit.id, service=service_name, crew_id=cleaner.id,
                  start_minute=start, manual=True,
                  duration_minutes=duration or lookup.durations(self.db)[service_name])
        self.db.add(job)
        self.db.flush()
        return job

    # ---- running and reading back ------------------------------------

    def run(self, start: date, days=1) -> Result:
        """Run the scheduler for `days` from `start` and read the outcome."""
        self.db.commit()
        summary = service.run(self.db, self.site.id, start, days, None)[0]
        return self.read(summary)

    def read(self, summary=None) -> Result:
        self.db.expire_all()
        res = Result(summary=summary)
        schedules = list(self.db.scalars(
            select(Schedule).where(Schedule.society_id == self.site.id)))
        ids = [s.id for s in schedules]
        rows = self.db.execute(
            select(Job, Visit).join(Visit, Visit.id == Job.visit_id)
            .where(Visit.schedule_id.in_(ids)).order_by(Visit.date, Job.start_minute)).all()
        for job, visit in rows:
            if job.status == "Skipped":
                continue
            if job.crew_id is None:
                res.unassigned.append(Unassigned(visit.date, visit.vehicle_id, job.service,
                                                 job.reason_code, job.note))
            else:
                res.placed.append(Placed(visit.date, visit.vehicle_id, job.service, job.crew_id,
                                         job.start_minute, job.duration_minutes, job.late,
                                         job.manual))
        res.findings = [f.code for f in self.db.scalars(
            select(ScheduleFinding).where(ScheduleFinding.schedule_id.in_(ids)))]
        return res


def _key(name: str) -> str:
    """site_break_start_minute -> site.break_start_minute (first underscore only
    when the prefix is a registry group)."""
    for prefix in ("site", "scheduler", "schedule"):
        if name.startswith(prefix + "_"):
            return prefix + "." + name[len(prefix) + 1:]
    raise KeyError(name)


def default_of(key: str):
    """The seeded default of a registry key (neutral test values mirror it)."""
    return settings_registry.BY_KEY[key].default
