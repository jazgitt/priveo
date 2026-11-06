"""SCHS-58: property tests. Seeded random days check that the hard rules never
break and that a plan is repeatable. No property-testing library: a fixed list
of seeds in plain pytest loops (OG10), small enough to run in well under a minute.

Two levels:
- the solver (`solve_passes`): 200 random days, no database;
- the planner (`Scenario.run`): a few dozen random days on a real site, which
  covers the window rules (weekly off, first-job floor, Interior earliest).
"""
import random
from collections import defaultdict
from datetime import time, timedelta

import pytest

from app.scheduling import passes
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


def _build(world, site_cfg, seed):
    rng = random.Random(seed)
    off = rng.sample(range(7), rng.randint(0, 2))
    first_job = rng.choice([330, 360, 390])
    earliest = rng.choice([420, 450, 480])
    site_cfg({"scheduler.rules_version": 2, "site.first_job_minute": first_job,
              "site.interior_earliest_minute": earliest, "site.weekday_cutoff_hard": True})
    sc = Scenario(world)
    sc.slots(off=off)
    for i in range(rng.randint(1, 3)):
        start = rng.choice([300, 330, 360, 420])
        sc.cleaner(f"C{i}", shift=(start, start + rng.choice([120, 180, 240])))
    cutoffs = {}
    for _ in range(rng.randint(3, 8)):
        cutoff = rng.choice([None, time(8, 30), time(9, 0), time(10, 0)])
        day = rng.choice([None, "Monday", "Tuesday", "Thursday", "Saturday"])
        car = sc.car(cutoff=cutoff, interior_day=day)
        cutoffs[car.id] = cutoff
    start_day = SUNDAY + timedelta(days=rng.randint(0, 6))
    return sc, cutoffs, off, first_job, earliest, start_day, rng.randint(1, 3)


def _plan(sc, start_day, days):
    res = sc.run(start_day, days=days)
    return res, sorted((p.day, str(p.vehicle_id), p.service, str(p.crew_id), p.start) for p in res.placed)


@pytest.mark.parametrize("seed", PLANNER_SEEDS)
def test_schr_hard_properties_a_planned_day_keeps_the_site_rules(world, site_cfg, seed):
    sc, cutoffs, off, first_job, earliest, start_day, days = _build(world, site_cfg, seed)
    res, _ = _plan(sc, start_day, days)
    strict_free = {int(d) for d in str(default_of("site.weekend_weekdays")).split(",")}
    per_crew, per_car, interiors = defaultdict(list), defaultdict(list), defaultdict(int)
    for p in res.placed:
        key = f"seed {seed}: {p.day} {p.service} at {p.start}"
        end = p.start + p.duration
        assert p.day.weekday() not in off, f"{key}: planned on the weekly off"  # SCHR-PAR-02
        crew = next(c for c in sc.cleaners.values() if c.id == p.crew_id)
        assert p.start >= max(first_job, crew.start_minute), f"{key}: before the first-job floor"  # SCHR-HARD-04
        if p.service == INTERNAL:  # SCHR-HARD-05
            assert p.start >= earliest, f"{key}: Interior before the earliest time"
            interiors[(p.vehicle_id, p.day)] += 1
        cutoff = cutoffs[p.vehicle_id]
        if cutoff is not None and p.day.weekday() not in strict_free and not p.manual:
            assert end <= cutoff.hour * 60 + cutoff.minute, f"{key}: past the strict cutoff"  # SCHR-CUT-02
        per_crew[(p.day, p.crew_id)].append((p.start, end))
        per_car[(p.day, p.vehicle_id)].append((p.start, end))
    assert not any(_overlaps(v) for v in per_crew.values()), f"seed {seed}: a cleaner overlaps"
    assert not any(_overlaps(v) for v in per_car.values()), f"seed {seed}: a car overlaps"
    assert all(n <= 1 for n in interiors.values()), f"seed {seed}: two Interiors for a car in a day"  # SCHR-HARD-11


@pytest.mark.parametrize("seed", PLANNER_SEEDS[:8])
def test_schr_hier_07_planning_the_same_input_again_gives_the_same_plan(world, site_cfg, seed):
    sc, *_, start_day, days = _build(world, site_cfg, seed)
    first_res, first = _plan(sc, start_day, days)
    second_res, second = _plan(sc, start_day, days)
    assert first == second, f"seed {seed}"
    assert len(first_res.unassigned) == len(second_res.unassigned)


def test_schr_par_02_the_random_sites_do_plan_work():
    # Guard against vacuous properties: a typical seed has room for jobs.
    crew, jobs = _random_day(0)
    assert passes.solve_passes(crew, jobs).placed
