"""SCHS-43: the break is a soft block in the Exterior pass and a hard block in the Interior pass."""
from datetime import time, timedelta

from sqlalchemy import select

from app.scheduling import passes
from app.scheduling.models import ScheduleFinding
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, solve_day
from tests.scheduling.builders import EXTERNAL, INTERNAL, Scenario
from tests.scheduling.conftest import SUNDAY

EXT, INT = passes.EXTERIOR, "Cleaning-Internal"
BREAK = {"break_block": {"a": (570, 600)}}  # 09:30 to 10:00
ORDER = "placed,break,late,early"
MONDAY = SUNDAY + timedelta(days=1)
SATURDAY = SUNDAY + timedelta(days=6)


def _params():
    return SolverParams(settings={"scheduler.objective_order": ORDER})


def _ext(key, duration=30, **kw):
    return SolverJob(key, f"v{key}", duration, service=EXT, **kw)


def _int(key, duration=30, **kw):
    return SolverJob(key, f"v{key}", duration, service=INT, **kw)


def test_schr_brk_02_an_interior_never_overlaps_a_kept_break():
    crew = [SolverCrew("a", 540, 660)]  # 09:00 to 11:00
    result = solve_day(crew, [_int("i1", 60), _int("i2", 30)], _params(), "interior", BREAK)
    for _key, (_c, start) in result.placed.items():
        assert not (start < 600 and start + (60 if _key == "i1" else 30) > 570)
    assert len(result.placed) == 2  # both fit, one before and one after the break


def test_schr_brk_02_the_interior_that_would_cover_the_break_is_deferred():
    crew = [SolverCrew("a", 540, 600)]  # 09:00 to 10:00: only 09:00 to 09:30 is left
    result = solve_day(crew, [_int("i1"), _int("i2")], _params(), "interior", BREAK)
    assert len(result.placed) == 1 and result.placed[next(iter(result.placed))][1] == 540
    assert len(result.unplaced) == 1


def test_schs_43_the_s35_interior_slot_09_30_to_10_00_only_when_the_break_is_not_due():
    crew = [SolverCrew("a", 570, 630)]
    job = [_int("i")]
    on = solve_day(crew, job, _params(), "interior", BREAK)
    assert on.placed["i"] == ("a", 600)  # a later slot
    off = solve_day(crew, job, _params(), "interior", {})
    assert off.placed["i"] == ("a", 570)


def test_schr_brk_03_exterior_coverage_wins_over_the_soft_break():
    crew = [SolverCrew("a", 540, 600)]  # two 30 minute Exteriors fill the hour
    result = solve_day(crew, [_ext("e1"), _ext("e2")], _params(), "exterior", BREAK)
    assert len(result.placed) == 2


def test_schr_brk_01_an_exterior_avoids_the_break_when_there_is_room():
    crew = [SolverCrew("a", 540, 660)]
    result = solve_day(crew, [_ext("e1"), _ext("e2")], _params(), "exterior", BREAK)
    for _c, start in result.placed.values():
        assert start + 30 <= 570 or start >= 600


def test_schr_brk_03_a_hard_weekday_cutoff_wins_over_the_soft_break():
    crew = [SolverCrew("a", 570, 660)]
    job = _ext("e", 30, finish_by=600, hard_cutoff=True)
    result = solve_day(crew, [job], _params(), "exterior", BREAK)
    assert result.placed["e"] == ("a", 570) and not result.late


def test_schr_hier_05_on_a_weekend_the_break_beats_the_soft_cutoff():
    crew = [SolverCrew("a", 570, 660)]
    job = _int("i", 30, finish_by=600)  # soft cutoff: weekend
    result = passes.solve_passes(crew, [job], _params(), BREAK)
    assert result.placed["i"] == ("a", 600) and result.late == {"i"}


def test_schr_brk_01_no_break_input_changes_nothing():
    crew = [SolverCrew("a", 570, 630)]
    assert solve_day(crew, [_ext("e")], _params(), "exterior", {}).placed["e"] == ("a", 570)


def test_schr_brk_04_a_missed_break_is_stored_with_the_cleaner_the_date_and_the_reason(world, site_cfg):
    site_cfg({"scheduler.rules_version": 2})
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", shift=(570, 600))  # the only half hour is the break itself
    sc.car(interior_day="Sunday", cutoff=time(10, 0))
    sc.run(MONDAY)
    rows = list(sc.db.scalars(select(ScheduleFinding).where(ScheduleFinding.code == "missed_break")))
    assert len(rows) == 1
    assert rows[0].detail == f"Ravi, {MONDAY:%d-%b-%y}: Exterior work needed that time."


def test_schr_brk_04_an_exterior_on_the_break_is_flagged(world, site_cfg):
    site_cfg({"scheduler.rules_version": 2})
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", shift=(540, 630))  # 09:00 to 10:30: 90 minutes, one Exterior takes 60
    cars = sc.cars(2)
    sc.fixed(cars[0], MONDAY, sc.cleaners["Ravi"], 560, service_name=EXTERNAL)  # by hand over the break
    sc.run(MONDAY)
    rows = list(sc.db.scalars(select(ScheduleFinding).where(ScheduleFinding.code == "missed_break")))
    assert len(rows) == 1
    assert "Ravi" in rows[0].detail and "-" in rows[0].detail and "by hand" in rows[0].detail


def test_schr_brk_02_the_run_keeps_the_interior_off_the_break(world, site_cfg):
    site_cfg({"scheduler.rules_version": 2})
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", shift=(540, 660))
    sc.car(interior_day="Monday")
    res = sc.run(MONDAY)
    for p in res.placed:
        if p.service == INTERNAL:
            assert p.start + p.duration <= 570 or p.start >= 600
