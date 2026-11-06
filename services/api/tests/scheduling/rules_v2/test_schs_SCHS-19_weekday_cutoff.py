"""SCHS-19: the Customer cutoff is a hard end limit on strict weekdays."""
from datetime import time, timedelta

import pytest

from app.customers.service import read_cutoff
from app.scheduling import passes
from app.scheduling.codes import ReasonCode
from app.scheduling.solver import SolverCrew, SolverJob, solve_day
from tests.scheduling.builders import INTERNAL, Scenario
from tests.scheduling.conftest import SUNDAY

THURSDAY = SUNDAY + timedelta(days=4)
SATURDAY = SUNDAY + timedelta(days=6)
CREW = [SolverCrew("a", 480, 600)]


def _job(key, duration=30, cutoff=510, hard=True):
    return SolverJob(key, f"v{key}", duration, finish_by=cutoff, hard_cutoff=hard)


def test_schr_cut_01_a_job_that_fits_before_the_cutoff_is_placed_on_time():
    result = solve_day(CREW, [_job("e")])
    assert result.placed["e"] == ("a", 480) and not result.late


def test_schr_cut_02_a_job_is_never_scheduled_to_finish_after_the_cutoff():
    result = solve_day(CREW, [_job("e"), _job("i")])  # room for one 30 minute job
    assert len(result.placed) == 1 and not result.late
    ((_, start),) = result.placed.values()
    assert start + 30 <= 510


def test_schr_cut_04_a_job_that_cannot_meet_the_cutoff_is_unassigned_with_its_code():
    result = solve_day(CREW, [_job("e", cutoff=500)])
    assert not result.placed and not result.late
    assert result.unplaced_codes["e"] == ReasonCode.CUSTOMER_CUTOFF
    assert result.unplaced["e"] == ReasonCode.CUSTOMER_CUTOFF.text


def test_schr_cut_04_a_soft_job_left_out_for_capacity_without_a_hard_cutoff_keeps_the_capacity_code():
    crew = [SolverCrew("a", 480, 510)]  # one 30 minute job fits before the cutoff
    result = solve_day(crew, [_job("x", cutoff=600, hard=False), _job("y", cutoff=600, hard=False)])
    assert list(result.unplaced_codes.values()) == [ReasonCode.CAPACITY_SHORT]


def test_schr_par_10_a_soft_job_on_a_weekend_is_still_placed_late():
    result = solve_day(CREW, [_job("e", cutoff=500, hard=False)])
    assert "e" in result.placed and result.late == {"e"}


def test_schr_cut_08_the_late_assignment_after_a_freeze_picks_the_earliest_time_before_the_cutoff():
    job = SolverJob("l", "v", 30, finish_by=540, hard_cutoff=True, windows=((480, 540),))
    result = solve_day(CREW, [job])
    assert result.placed["l"] == ("a", 480) and not result.late


def _thursday(world, site_cfg, version=2, **cfg):
    site_cfg({"scheduler.rules_version": version, **cfg})
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    car = sc.car(cutoff=time(8, 30), interior_day="Thursday")
    return sc, car


def test_s36_a_thursday_job_after_the_cutoff_is_not_planned_and_is_reported(world, site_cfg):
    # One cleaner, one 30 minute slot before 08:30. Which service takes it is
    # the Exterior-first pass order (a later story); the other must not be
    # planned at 08:30 to 09:00.
    sc, car = _thursday(world, site_cfg)
    res = sc.run(THURSDAY)
    assert [(p.start, p.late) for p in res.placed] == [(480, False)]
    assert len(res.unassigned) == 1
    assert res.unassigned[0].note == ReasonCode.CUSTOMER_CUTOFF.text
    assert res.summary.unscheduled == 1


def test_schr_hard_08_weekend_days_are_not_limited_here(world, site_cfg):
    sc, car = _thursday(world, site_cfg)
    res = sc.run(SATURDAY)
    interior = res.placed_on(SATURDAY, car, INTERNAL)
    assert res.unassigned == [] or interior  # the weekend stays soft (SCHS-20)
    assert all(u.note != ReasonCode.CUSTOMER_CUTOFF.text for u in res.unassigned)


def test_schr_par_11_the_strict_setting_off_leaves_the_cutoff_soft(world, site_cfg):
    sc, car = _thursday(world, site_cfg, **{"site.weekday_cutoff_hard": False})
    res = sc.run(THURSDAY)
    assert len(res.placed) == 2 and [p.late for p in res.placed].count(True) == 1


def test_schr_par_10_the_weekend_days_come_from_the_setting(world, site_cfg):
    sc, car = _thursday(world, site_cfg, **{"site.weekend_weekdays": [3, 4]})
    res = sc.run(THURSDAY)  # Thursday is a weekend day at this site
    assert len(res.placed) == 2 and [p.late for p in res.placed].count(True) == 1


def test_kill_switch_version_1_keeps_the_soft_cutoff(world, site_cfg):
    sc, car = _thursday(world, site_cfg, version=1)
    res = sc.run(THURSDAY)
    assert len(res.placed) == 2 and [p.late for p in res.placed].count(True) == 1


# ---- SCHR-CUT-03 and SCHR-CUT-07 (gap check, 06-Nov-26) --------------------


def test_schr_cut_03_an_interior_that_misses_its_cutoff_is_left_out_and_the_exterior_keeps_its_place():
    # Room for one 30 minute job before the 08:30 cutoff. The Exterior is planned
    # first (Pass A), so the Interior is the one that cannot fit and stays out.
    crew = [SolverCrew("a", 480, 510)]
    exterior = SolverJob("e", "ve", 30, service=passes.EXTERIOR, finish_by=510, hard_cutoff=True)
    interior = SolverJob("i", "vi", 30, service=INTERNAL, finish_by=510, hard_cutoff=True,
                         interior=True)
    for jobs in ([interior, exterior], [exterior, interior]):  # list order must not matter
        result = passes.solve_passes(crew, jobs)
        assert set(result.placed) == {"e"}
        assert set(result.unplaced) == {"i"}
        assert result.unplaced_codes["i"] in {ReasonCode.CUSTOMER_CUTOFF, ReasonCode.CAPACITY_SHORT}


@pytest.mark.parametrize("hour, minute", [(h, m) for h in range(24) for m in (0, 30)])
def test_schr_cut_07_every_half_hour_step_is_a_cutoff_the_customer_can_choose(hour, minute):
    assert read_cutoff(f"{hour:02d}:{minute:02d}") == time(hour, minute)


@pytest.mark.parametrize("text", ["08:15", "08:45", "8:30", "24:00", "soon"])
def test_schr_cut_07_other_times_are_not_a_cutoff_choice(text):
    assert read_cutoff(text) is None


def test_schr_cut_07_a_cutoff_before_the_first_job_plus_duration_is_unassigned_and_reported():
    # The first job starts at 05:30 and takes 30 minutes, so it cannot finish by
    # the 05:30 cutoff. Nothing warns the customer; the planner reports the car.
    crew = [SolverCrew("a", 330, 600)]
    result = solve_day(crew, [SolverJob("e", "ve", 30, finish_by=330, hard_cutoff=True)])
    assert not result.placed
    assert result.unplaced_codes["e"] == ReasonCode.CUSTOMER_CUTOFF
