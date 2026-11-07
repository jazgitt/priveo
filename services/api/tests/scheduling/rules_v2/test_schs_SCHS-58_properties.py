"""SCHS-58: property tests. Seeded random days check that the hard rules never
break and that a plan is repeatable. No property-testing library: a fixed list
of seeds in plain pytest loops (OG10), small enough to run in well under a minute.

Two levels:
- the solver (`solve_passes`): 200 random days, no database;
- the planner (`Scenario.run`): 24 random sites, each with 1 to 3 days. A site draws
  its own weekly off, first-job and Interior-earliest times, break (site setting and
  crew and date-range overrides), home zones and zone-less cars, a Trainee, sick days,
  cutoffs, Interior cars and overdue entitlement rows. The checks cover the window
  rules, the break (no Interior in a kept break), zones (a cross-zone job has a reason;
  a zone-less car is never cross-zone), the Trainee (never takes a job) and the
  Interior limits per car per day and per service week.
"""
import random
from collections import defaultdict
from datetime import time, timedelta

import pytest
from sqlalchemy import select

from app.scheduling import home_zone, passes
from app.scheduling.breaks import effective_break
from app.scheduling.models import InteriorEntitlement, Job, SchedulingCrewException, Visit
from app.scheduling.solver import SolverCrew, SolverJob, solve_day
from tests.scheduling.builders import INTERNAL, Scenario, default_of
from tests.scheduling.conftest import SUNDAY

EXT, INT = passes.EXTERIOR, INTERNAL
SOLVER_SEEDS = list(range(200))
PLANNER_SEEDS = list(range(24))
WEEK1 = SUNDAY
WEEK2 = SUNDAY + timedelta(days=7)


# ---- solver level --------------------------------------------------------


def _random_day(seed):
    rng = random.Random(seed)
    crew = []
    for i in range(rng.randint(1, 3)):
        start = rng.choice([420, 450, 480])
        crew.append(SolverCrew(f"c{i}", start, start + rng.choice([90, 120, 180])))
    cars = [f"v{i}" for i in range(rng.randint(2, 5))]
    jobs = []
    for n in range(rng.randint(3, 9)):
        interior = rng.random() < 0.45
        floor = rng.choice([None, 450, 480])  # a window opening later (floor, earliest)
        windows = ((floor, 660),) if floor else None
        hard = rng.random() < 0.6
        jobs.append(SolverJob(
            f"j{n}", rng.choice(cars), rng.choice([30, 45, 60]),
            finish_by=rng.choice([None, 510, 540, 600]) if hard else None,
            windows=windows, hard_cutoff=hard, interior=interior,
            week=rng.choice([WEEK1, WEEK2]) if interior else None,
            service=INT if interior else EXT))
    return crew, jobs


def _overlaps(spans):
    spans = sorted(spans)
    return any(a_end > b_start for (_, a_end), (b_start, _) in zip(spans, spans[1:], strict=False))


@pytest.mark.parametrize("block", range(0, 200, 50))
def test_schr_hard_properties_a_random_day_never_breaks_a_hard_rule(block):
    for seed in SOLVER_SEEDS[block:block + 50]:
        crew, jobs = _random_day(seed)
        by_key = {j.key: j for j in jobs}
        shift = {c.key: (c.start, c.end) for c in crew}
        res = passes.solve_passes(crew, jobs)
        ctx = f"seed {seed}"
        per_crew, per_car = defaultdict(list), defaultdict(list)
        interiors_day, interiors_week = defaultdict(int), defaultdict(int)
        for key, (c, start) in res.placed.items():
            job = by_key[key]
            end = start + job.duration
            per_crew[c].append((start, end))
            per_car[job.vehicle].append((start, end))
            assert shift[c][0] <= start and end <= shift[c][1], f"{ctx}: {key} outside the shift"
            if job.windows:  # every job inside a window
                assert any(s <= start and end <= e for s, e in job.windows), f"{ctx}: {key} outside window"
            if job.hard_cutoff and job.finish_by is not None:  # SCHR-CUT-02
                assert end <= job.finish_by and key not in res.late, f"{ctx}: {key} past cutoff"
            if job.interior:  # SCHR-HARD-10, SCHR-HARD-11
                interiors_day[job.vehicle] += 1
                interiors_week[(job.vehicle, job.week)] += 1
        assert not any(_overlaps(v) for v in per_crew.values()), f"{ctx}: a cleaner overlaps"
        assert not any(_overlaps(v) for v in per_car.values()), f"{ctx}: a car overlaps"
        assert all(n <= 1 for n in interiors_day.values()), f"{ctx}: two Interiors for a car in a day"
        assert all(n <= 1 for n in interiors_week.values()), f"{ctx}: two Interiors for a car in a week"
        assert set(res.placed) | set(res.unplaced) == set(by_key), f"{ctx}: a job is lost"


def test_schr_hier_07_the_same_input_gives_the_same_plan():
    for seed in SOLVER_SEEDS[:60]:
        crew, jobs = _random_day(seed)
        first = passes.solve_passes(crew, jobs)
        second = passes.solve_passes(crew, list(jobs))
        assert first.placed == second.placed and first.unplaced == second.unplaced, f"seed {seed}"


def test_schr_ext_03_pass_a_plans_the_exteriors_as_if_there_were_no_interiors():
    for seed in SOLVER_SEEDS[:60]:
        crew, jobs = _random_day(seed)
        exteriors = [j for j in jobs if j.service == EXT]
        if not exteriors:
            continue
        alone = solve_day(crew, exteriors)
        both = passes.solve_passes(crew, jobs)
        got = {k: v for k, v in both.placed.items() if k in {j.key for j in exteriors}}
        assert got == alone.placed, f"seed {seed}: an Interior moved or dropped an Exterior"
        # An Exterior left out is never given room to an Interior in its place.
        assert not (set(alone.unplaced) & set(both.placed)), f"seed {seed}"


# ---- planner level -------------------------------------------------------

ZONES = ("North", "South")
LAST_WEEK = WEEK1 - timedelta(days=7)


def _db_jobs(sc):
    """(job, visit) pairs of the site: the car, the day and the entitlement link are on them."""
    return sc.db.execute(select(Job, Visit).join(Visit, Visit.id == Job.visit_id)).all()


def _build(world, site_cfg, seed):
    """A random site for one seed. Each seed draws its own zones, breaks, Trainee,
    sick days, cutoffs, Interior cars and entitlement rows (SCHR-ZONE, BRK, INT, CUT)."""
    rng = random.Random(seed)
    off = rng.sample(range(7), rng.randint(0, 2))
    first_job = rng.choice([330, 360, 390])
    earliest = rng.choice([420, 450, 480])
    break_start = rng.choice([540, 570, 600])
    site_cfg({"site.first_job_minute": first_job,
              "site.interior_earliest_minute": earliest, "site.weekday_cutoff_hard": True,
              "site.break_enabled": rng.random() < 0.8})
    # A break must start before it ends, and the settings are saved one at a time. Move the
    # edge that keeps the order valid first: the start when it moves earlier, else the end.
    if break_start < 570:  # the default break starts at 570
        site_cfg({"site.break_start_minute": break_start})
        site_cfg({"site.break_end_minute": break_start + 30})
    else:
        site_cfg({"site.break_end_minute": break_start + 30})
        site_cfg({"site.break_start_minute": break_start})
    start_day = SUNDAY + timedelta(days=rng.randint(0, 6))
    days = rng.randint(1, 3)
    sc = Scenario(world)
    sc.slots(off=off)
    members = []
    for i in range(rng.randint(1, 3)):
        start = rng.choice([300, 330, 360, 420])
        zone = rng.choice([None, *ZONES])  # None: a cleaner with no home zone (ZONE-11)
        members.append(sc.cleaner(f"C{i}", shift=(start, start + rng.choice([120, 180, 240])),
                                  zone=zone))
    trainee = None
    if rng.random() < 0.5:  # a Trainee follows the first Member (ZONE-09)
        trainee = sc.cleaner("T0", shift=(330, 600), role="Trainee", paired=members[0].id)
    for member in members:  # break overrides: a crew range, or none (BRK-06)
        if rng.random() < 0.25:
            s = rng.choice([540, 570, 600, 660])
            sc.break_rule(start_day, start_day + timedelta(days=6), cleaner=member, minutes=(s, s + 30))
    day = start_day + timedelta(days=rng.randint(0, days - 1))
    for member in members:  # sick days (HARD-01)
        if rng.random() < 0.2:
            sc.exception(member, day, "Sick")
    cutoffs, car_zone, interior_cars = {}, {}, []
    for _ in range(rng.randint(3, 8)):
        cutoff = rng.choice([None, time(8, 30), time(9, 0), time(10, 0)])
        interior_day = rng.choice([None, "Monday", "Tuesday", "Thursday", "Saturday"])
        zone = rng.choice([None, *ZONES])
        interior = rng.random() < 0.4
        car = sc.car(cutoff=cutoff, interior_day=interior_day, zone=zone, interior=interior or None)
        cutoffs[car.id] = cutoff
        car_zone[car.id] = zone
        if interior:
            interior_cars.append(car)
            if rng.random() < 0.3:  # an overdue row from the week before (INT-12, INT-13)
                sc.entitlement(car, LAST_WEEK, seq=2)
    return {"sc": sc, "cutoffs": cutoffs, "car_zone": car_zone, "off": off,
            "first_job": first_job, "earliest": earliest, "start_day": start_day,
            "days": days, "members": members, "trainee": trainee}


def _plan(sc, start_day, days):
    res = sc.run(start_day, days=days)
    return res, sorted((p.day, str(p.vehicle_id), p.service, str(p.crew_id), p.start) for p in res.placed)


def _zone_names(sc):
    return {z.id: name for name, z in sc.zones.items()}


STATS: dict[str, int] = defaultdict(int)  # data the random sites produced; read by the last test


@pytest.mark.parametrize("seed", PLANNER_SEEDS)
def test_schr_hard_properties_a_planned_day_keeps_the_site_rules(world, site_cfg, seed):
    b = _build(world, site_cfg, seed)
    sc, cutoffs, off, first_job, earliest = b["sc"], b["cutoffs"], b["off"], b["first_job"], b["earliest"]
    res, _ = _plan(sc, b["start_day"], b["days"])
    strict_free = {int(d) for d in str(default_of("site.weekend_weekdays")).split(",")}
    per_crew, per_car = defaultdict(list), defaultdict(list)
    interiors, week_interiors = defaultdict(int), defaultdict(int)
    crew_by_id = {c.id: c for c in sc.cleaners.values()}
    zone_name = _zone_names(sc)
    jobs = _db_jobs(sc)
    for p in res.placed:
        key = f"seed {seed}: {p.day} {p.service} at {p.start}"
        end = p.start + p.duration
        assert p.day.weekday() not in off, f"{key}: planned on the weekly off"  # SCHR-PAR-02
        crew = crew_by_id[p.crew_id]
        assert p.start >= max(first_job, crew.start_minute), f"{key}: before the first-job floor"  # SCHR-HARD-04
        assert not (b["trainee"] and p.crew_id == b["trainee"].id), f"{key}: a Trainee took a job"  # SCHR-ZONE-09
        if p.service == INTERNAL:  # SCHR-HARD-05
            assert p.start >= earliest, f"{key}: Interior before the earliest time"
            interiors[(p.vehicle_id, p.day)] += 1
            br = effective_break(sc.db, crew, p.day)  # SCHR-BRK-02: an Interior never takes a kept break
            if br is not None:
                assert end <= br.start_minute or p.start >= br.end_minute, f"{key}: Interior in the break"
        cutoff = cutoffs[p.vehicle_id]
        if cutoff is not None and p.day.weekday() not in strict_free and not p.manual:
            assert end <= cutoff.hour * 60 + cutoff.minute, f"{key}: past the strict cutoff"  # SCHR-CUT-02
        per_crew[(p.day, p.crew_id)].append((p.start, end))
        per_car[(p.day, p.vehicle_id)].append((p.start, end))
    for job, visit in jobs:
        if job.crew_id is None or job.status == "Skipped":
            continue
        car_zone = b["car_zone"].get(visit.vehicle_id)
        crew = crew_by_id[job.crew_id]
        homes = {zone_name[z.id] for z in home_zone.effective_zones(sc.db, crew)}
        if job.cross_zone_reason:  # SCHR-ZONE-04, ZONE-06: a cross-zone job has a car zone, a home zone, and a reason
            assert car_zone is not None and homes and car_zone not in homes, f"seed {seed}: bad cross-zone"
        if car_zone is None:  # SCHR-ZONE-08: a zone-less car is never cross-zone
            assert job.cross_zone_reason is None, f"seed {seed}: zone-less car marked cross-zone"
        if job.service == INTERNAL and not job.manual:  # SCHR-INT-11: each Interior carries its service week
            assert job.service_week_start is not None, f"seed {seed}: Interior without a service week"
            week_interiors[(visit.vehicle_id, job.service_week_start)] += 1
    assert not any(_overlaps(v) for v in per_crew.values()), f"seed {seed}: a cleaner overlaps"
    assert not any(_overlaps(v) for v in per_car.values()), f"seed {seed}: a car overlaps"
    assert all(n <= 1 for n in interiors.values()), f"seed {seed}: two Interiors for a car in a day"  # SCHR-HARD-11
    assert all(n <= 1 for n in week_interiors.values()), f"seed {seed}: two Interiors in a week"  # SCHR-HARD-10
    STATS["seeds"] += 1
    STATS["interiors"] += sum(1 for p in res.placed if p.service == INTERNAL)
    STATS["cross_zone"] += sum(1 for j, _v in jobs if j.cross_zone_reason)
    STATS["trainee_seeds"] += b["trainee"] is not None
    STATS["sick_days"] += sc.db.query(SchedulingCrewException).count()
    STATS["overdue_rows"] += sum(1 for r in sc.db.scalars(select(InteriorEntitlement))
                                 if r.service_week_start == LAST_WEEK)
    STATS["break_days"] += sum(1 for c in sc.cleaners.values()
                               if effective_break(sc.db, c, b["start_day"]) is not None)


@pytest.mark.parametrize("seed", PLANNER_SEEDS[:8])
def test_schr_hier_07_planning_the_same_input_again_gives_the_same_plan(world, site_cfg, seed):
    b = _build(world, site_cfg, seed)
    sc = b["sc"]
    first_res, first = _plan(sc, b["start_day"], b["days"])
    second_res, second = _plan(sc, b["start_day"], b["days"])
    assert first == second, f"seed {seed}"
    assert len(first_res.unassigned) == len(second_res.unassigned)


def test_the_random_sites_exercise_every_kind_of_data():
    """Guards against vacuous properties. Runs after the per-seed tests above (pytest keeps
    file order) and reads what they produced: across the seeds there must be Interiors,
    cross-zone jobs, Trainee seeds, sick days, overdue rows and break days."""
    assert STATS["seeds"] == len(PLANNER_SEEDS), dict(STATS)
    for name in ("interiors", "cross_zone", "trainee_seeds", "sick_days", "overdue_rows", "break_days"):
        assert STATS[name] > 0, f"no seed produced any {name}: {dict(STATS)}"


def test_schr_par_02_the_random_sites_do_plan_work():
    # Guard against vacuous properties: a typical seed has room for jobs.
    crew, jobs = _random_day(0)
    assert passes.solve_passes(crew, jobs).placed
