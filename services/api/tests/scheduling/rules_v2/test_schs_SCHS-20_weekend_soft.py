"""SCHS-20: on a weekend the Customer cutoff stays soft."""
from datetime import timedelta
from types import SimpleNamespace

from app.scheduling.solver import SolverCrew, SolverJob, solve_day
from app.scheduling.solver.rules.weekend_late import is_flexible_day
from tests.scheduling.conftest import SUNDAY

SATURDAY = SUNDAY + timedelta(days=6)
THURSDAY = SUNDAY + timedelta(days=4)
CREW = [SolverCrew("a", 480, 600)]


def _ctx(active=True, flexible=True):
    values = {"site.weekend_cutoff_flexible": flexible, "site.weekend_weekdays": [5, 6]}
    return SimpleNamespace(active=active, setting=values.__getitem__)


def _job(key, cutoff=510, **kw):
    return SolverJob(key, "creta", 30, finish_by=cutoff, **kw)


def test_schr_wke_01_the_cutoff_is_flexible_only_on_weekend_days_at_version_2():
    assert is_flexible_day(_ctx(), SATURDAY) and is_flexible_day(_ctx(), SUNDAY)
    assert not is_flexible_day(_ctx(), THURSDAY)
    assert not is_flexible_day(_ctx(active=False), SATURDAY)
    assert not is_flexible_day(_ctx(flexible=False), SATURDAY)


def test_schr_wke_01_s34_exterior_and_interior_both_run_and_the_interior_is_late():
    # Cutoff 08:30, Exterior and Interior 30 minutes each, one cleaner.
    result = solve_day(CREW, [_job("ext"), _job("int")])
    assert set(result.placed) == {"ext", "int"}
    starts = sorted(start for _, start in result.placed.values())
    assert starts == [480, 510]
    assert len(result.late) == 1


def test_schr_wke_01_s35_the_exterior_may_end_after_the_cutoff_when_nine_is_the_earliest_slot():
    result = solve_day(CREW, [_job("ext", windows=((540, 600),))])
    assert result.placed["ext"] == ("a", 540) and result.late == {"ext"}


def test_schr_wke_03_a_late_weekend_job_must_still_end_inside_the_shift():
    crew = [SolverCrew("a", 480, 540)]
    result = solve_day(crew, [_job("a1"), _job("a2"), _job("a3")])
    assert len(result.placed) == 2 and len(result.unplaced) == 1
    assert all(start + 30 <= 540 for _, start in result.placed.values())


def test_schr_wke_04_the_car_is_assumed_available_so_a_late_job_is_placed_not_dropped():
    result = solve_day(CREW, [_job("ext", cutoff=480)])
    assert "ext" in result.placed and result.late == {"ext"}
