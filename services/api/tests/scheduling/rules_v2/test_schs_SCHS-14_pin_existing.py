"""SCHS-14: characterisation tests that pin hard rules the planner already keeps.

SCHR-HARD-01 availability, SCHR-HARD-02 shift end, SCHR-HARD-03 no overlap,
SCHR-HARD-12 one cleaner per car at a time, SCHR-EXT-12 Exterior not carried.
They run on the planner as it is today (default rules version) and change no
application code.
"""
from datetime import time, timedelta

from sqlalchemy import select

from app.directory import lookup
from app.scheduling.models import Job, Visit
from tests.scheduling.builders import EXTERNAL, INTERNAL, Scenario
from tests.scheduling.conftest import SUNDAY

MONDAY = SUNDAY + timedelta(days=1)


def _no_overlap(placed):
    """True when no two of these placements share a minute."""
    spans = sorted((p.start, p.start + p.duration) for p in placed)
    return all(a_end <= b_start for (_, a_end), (b_start, _) in zip(spans, spans[1:], strict=False))


def _external_minutes(world):
    return lookup.durations(world.db)[EXTERNAL]


# ---- SCHR-HARD-01: only available cleaners are used -------------------------


def test_schr_hard_01_sick_cleaner_gets_no_job(world):
    sc = Scenario(world)
    sc.slots()
    sick = sc.cleaner("Sick", shift=(360, 600))
    well = sc.cleaner("Well", shift=(360, 600))
    sc.exception(sick, SUNDAY, "Sick")
    sc.cars(3, cutoff=time(9, 0))
    res = sc.run(SUNDAY)
    assert res.placed and not res.unassigned
    assert {p.crew_id for p in res.placed} == {well.id}


def test_schr_hard_01_cleaner_on_leave_gets_no_job(world):
    sc = Scenario(world)
    sc.slots()
    away = sc.cleaner("Away", shift=(360, 600))
    well = sc.cleaner("Well", shift=(360, 600))
    sc.exception(away, SUNDAY, "Leave")
    sc.cars(3, cutoff=time(9, 0))
    res = sc.run(SUNDAY)
    assert res.placed and {p.crew_id for p in res.placed} == {well.id}


def test_schr_hard_01_only_cleaner_unavailable_leaves_job_unassigned(world):
    sc = Scenario(world)
    sc.slots()
    only = sc.cleaner(shift=(360, 600))
    sc.exception(only, SUNDAY, "Sick")
    sc.car()
    res = sc.run(SUNDAY)
    assert res.placed == [] and len(res.unassigned) == 1


def test_schr_hard_01_late_start_job_starts_no_earlier(world):
    sc = Scenario(world)
    sc.slots()
    late = sc.cleaner(shift=(360, 600))
    sc.exception(late, SUNDAY, "Late start", from_minute=480)
    sc.cars(2, cutoff=time(11, 0))
    res = sc.run(SUNDAY)
    assert res.placed
    assert all(p.start >= 480 for p in res.placed)


def test_schr_hard_01_cleaner_off_that_weekday_gets_no_job(world):
    sc = Scenario(world)
    sc.slots()
    off = sc.cleaner("Off", shift=(360, 600), days=[0, 1, 2, 3, 4, 5])  # not Sunday
    on = sc.cleaner("On", shift=(360, 600))
    sc.cars(2, cutoff=time(9, 0))
    res = sc.run(SUNDAY)
    assert res.placed and off.id not in {p.crew_id for p in res.placed}
    assert {p.crew_id for p in res.placed} == {on.id}


# ---- SCHR-HARD-02: the shift end is never passed ----------------------------


def test_schr_hard_02_no_job_ends_after_shift_end(world):
    sc = Scenario(world)
    sc.slots()
    end = 360 + 2 * _external_minutes(world) + 5  # room for two jobs, not three
    ravi = sc.cleaner(shift=(360, end))
    sc.cars(6)
    res = sc.run(SUNDAY)
    assert res.placed
    assert all(p.crew_id == ravi.id and p.start + p.duration <= end for p in res.placed)


def test_schr_hard_02_job_that_does_not_fit_is_unassigned(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(360, 360 + _external_minutes(world) - 1))  # one minute short
    sc.car()
    res = sc.run(SUNDAY)
    assert res.placed == [] and len(res.unassigned) == 1


def test_schr_hard_02_each_cleaner_uses_own_shift_end(world):
    sc = Scenario(world)
    sc.slots()
    d = _external_minutes(world)
    short = sc.cleaner("Short", shift=(360, 360 + d))
    long = sc.cleaner("Long", shift=(360, 360 + 4 * d))
    ends = {short.id: short.end_minute, long.id: long.end_minute}
    sc.cars(5)
    res = sc.run(SUNDAY)
    assert res.placed
    assert all(p.start + p.duration <= ends[p.crew_id] for p in res.placed)


# ---- SCHR-HARD-03: no overlapping jobs for a cleaner ------------------------


def test_schr_hard_03_one_cleaner_jobs_do_not_overlap(world):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner(shift=(300, 660))
    sc.cars(5)
    res = sc.run(SUNDAY)
    mine = [p for p in res.placed if p.crew_id == ravi.id]
    assert len(mine) >= 2 and _no_overlap(mine)


def test_schr_hard_03_no_overlap_for_any_cleaner_across_days(world):
    sc = Scenario(world)
    sc.slots()
    cleaners = [sc.cleaner(f"C{i}", shift=(300, 660)) for i in range(2)]
    sc.cars(6, interior_day="Monday")
    res = sc.run(SUNDAY, days=2)
    for day in (SUNDAY, MONDAY):
        for c in cleaners:
            mine = [p for p in res.placed_on(day) if p.crew_id == c.id]
            assert _no_overlap(mine)
    assert res.placed_on(SUNDAY) and res.placed_on(MONDAY)


def test_schr_hard_03_manual_job_is_not_overlapped_by_planned_jobs(world):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner(shift=(300, 660))
    held = sc.car()
    sc.cars(3)
    sc.fixed(held, SUNDAY, ravi, 360)
    res = sc.run(SUNDAY)
    mine = [p for p in res.placed_on(SUNDAY) if p.crew_id == ravi.id]
    assert any(p.manual and p.start == 360 for p in mine) and len(mine) > 1
    assert _no_overlap(mine)


# ---- SCHR-HARD-12: one car, one cleaner at a time ---------------------------


def test_schr_hard_12_cars_two_services_same_day_never_overlap(world):
    sc = Scenario(world)
    sc.slots()
    for i in range(3):
        sc.cleaner(f"C{i}", shift=(300, 660))
    cars = sc.cars(3, interior_day="Sunday")
    for car in cars:
        sc.entitlement(car, SUNDAY)
    res = sc.run(SUNDAY)
    both = 0
    for car in cars:
        jobs = res.placed_on(SUNDAY, car)
        both += len(jobs) > 1
        assert _no_overlap(jobs)
    assert both, "the scenario must put two jobs on at least one car"


def test_schr_hard_12_car_with_two_jobs_does_not_double_book_cleaners(world):
    sc = Scenario(world)
    sc.slots()
    cleaners = [sc.cleaner(f"C{i}", shift=(300, 660)) for i in range(2)]
    car = sc.car(interior_day="Sunday")
    sc.entitlement(car, SUNDAY)
    res = sc.run(SUNDAY)
    jobs = res.placed_on(SUNDAY, car)
    assert len(jobs) == 2 and {p.service for p in jobs} == {EXTERNAL, INTERNAL}
    assert _no_overlap(jobs)
    assert {p.crew_id for p in jobs} <= {c.id for c in cleaners}


# ---- SCHR-EXT-12: a missed Exterior is not carried forward ------------------


def _jobs(world, service_name):
    world.db.expire_all()
    return world.db.execute(
        select(Job, Visit).join(Visit, Visit.id == Job.visit_id)
        .where(Job.service == service_name)).all()


def test_schr_ext_12_missed_exterior_adds_no_job_the_next_day(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(360, 600))
    car = sc.car(cutoff=time(9, 0))
    first = sc.run(SUNDAY)
    assert len(first.placed_on(SUNDAY, car, EXTERNAL)) == 1
    job, _ = _jobs(world, EXTERNAL)[0]
    job.status = "Could not complete"  # the Exterior was missed
    world.db.commit()
    nxt = sc.run(MONDAY)
    assert len(nxt.placed_on(MONDAY, car, EXTERNAL)) == 1  # the regular one only
    assert nxt.unassigned == []
    external_by_day = [(v.date, j.status) for j, v in _jobs(world, EXTERNAL)]
    assert sorted(d for d, _ in external_by_day) == [SUNDAY, MONDAY]
    assert (SUNDAY, "Could not complete") in external_by_day


def test_schr_ext_12_missed_exterior_is_not_replanned_on_its_own_day(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(360, 600))
    car = sc.car(cutoff=time(9, 0))
    sc.run(SUNDAY)
    job, _ = _jobs(world, EXTERNAL)[0]
    job.status = "Could not complete"
    world.db.commit()
    sc.run(MONDAY)
    # still one Exterior per day, none extra on Sunday or later
    days = sorted(v.date for _, v in _jobs(world, EXTERNAL) if v.vehicle_id == car.id)
    assert days == [SUNDAY, MONDAY]
