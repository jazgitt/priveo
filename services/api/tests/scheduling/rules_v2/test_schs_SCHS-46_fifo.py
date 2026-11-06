"""SCHS-46: oldest service week first, weekdays before the weekend, carry before new."""
from datetime import date, timedelta

from sqlalchemy import select

from app.scheduling import passes
from app.scheduling.models import InteriorEntitlement, Job, Visit
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, solve_day
from app.scheduling.solver.rules import fifo
from tests.scheduling.builders import INTERNAL, Scenario

INT = "Cleaning-Internal"
ORDER = "placed,zone,break,fifo,late,early_capacity,early"
WEEK1 = date(2026, 11, 2)  # Monday
WEEK2 = WEEK1 + timedelta(days=7)
WEEK3 = WEEK2 + timedelta(days=7)


def _params(**weights):
    settings = {"scheduler.objective_order": ORDER}
    settings.update({f"scheduler.weight_{k}": v for k, v in weights.items()})
    return SolverParams(settings=settings)


def _int(key, week, **kw):
    return SolverJob(key, f"v{key}", 30, service=INT, interior=True, week=week, **kw)


def test_schr_int_12_with_capacity_for_one_the_oldest_service_week_is_placed():
    crew = [SolverCrew("a", 360, 390)]
    jobs = [_int("new", WEEK2), _int("old", WEEK1), _int("newest", WEEK3)]
    result = solve_day(crew, jobs, _params(), "interior", {})
    assert list(result.placed) == ["old"]


def test_schr_int_13_an_overdue_interior_goes_ahead_of_the_new_one():
    crew = [SolverCrew("a", 360, 420)]
    jobs = [_int("new1", WEEK2), _int("new2", WEEK2), _int("carry", WEEK1)]
    result = solve_day(crew, jobs, _params(), "interior", {})
    assert "carry" in result.placed and len(result.placed) == 2


def test_schr_int_12_an_older_week_beats_any_number_of_newer_ones():
    crew = [SolverCrew("a", 360, 390)]
    jobs = [_int(f"n{i}", WEEK2) for i in range(8)] + [_int("old", WEEK1)]
    assert list(solve_day(crew, jobs, _params(), "interior", {}).placed) == ["old"]


def test_schr_int_12_in_one_week_the_tighter_cutoff_goes_first():
    crew = [SolverCrew("a", 360, 390)]
    jobs = [_int("loose", WEEK1), _int("tight", WEEK1, finish_by=420)]
    assert list(solve_day(crew, jobs, _params(), "interior", {}).placed) == ["tight"]


def test_schr_int_12_in_one_week_the_longer_wait_goes_first():
    crew = [SolverCrew("a", 360, 390)]
    jobs = [_int("late-row", WEEK1, finish_by=420), _int("early-row", WEEK1)]
    inputs = {"fifo": {"weeks": {}, "created": {"vlate-row": 200.0, "vearly-row": 100.0}}}
    assert list(solve_day(crew, jobs, _params(), "interior", inputs).placed) == ["early-row"]


def test_schr_int_12_the_week_of_the_chosen_ledger_row_is_used_when_the_job_has_none():
    crew = [SolverCrew("a", 360, 390)]
    jobs = [SolverJob("x", "vx", 30, service=INT, interior=True), SolverJob("y", "vy", 30, service=INT, interior=True)]
    inputs = {"fifo": {"weeks": {"vx": WEEK2, "vy": WEEK1}, "created": {}}}
    assert list(solve_day(crew, jobs, _params(), "interior", inputs).placed) == ["y"]


def test_schr_wke_05_a_weekend_day_takes_the_oldest_week_first():
    crew = [SolverCrew("a", 360, 420)]
    jobs = [_int("w3", WEEK3), _int("w1", WEEK1), _int("w2", WEEK2)]
    result = passes.solve_passes(crew, jobs, _params(), {})
    assert set(result.placed) == {"w1", "w2"}


def test_schr_int_12_exteriors_and_a_single_interior_are_untouched():
    crew = [SolverCrew("a", 360, 480)]
    jobs = [_int("only", WEEK1), SolverJob("e", "ve", 30, service=passes.EXTERIOR)]
    assert len(passes.solve_passes(crew, jobs, _params(), {}).placed) == 2


def test_schr_int_12_version_1_settings_add_nothing():
    crew = [SolverCrew("a", 360, 390)]
    jobs = [_int("b", WEEK2), _int("a", WEEK1)]
    result = solve_day(crew, jobs, SolverParams(), "single", {})
    assert len(result.placed) == 1


def test_schr_int_12_tier_values_make_each_tier_outweigh_the_ones_below():
    values = fifo.tier_values(10, 4)
    assert values[3] == 0 and values[2] == 100 and values[1] == 10 * (100 + 10)
    assert values[1] + 1 > 10 * (values[2] + 10) - 1 or values[1] == 10 * (values[2] + 10)
    assert max(fifo.tier_values(100, 12)) <= fifo.VALUE_CAP


def test_schr_int_13_the_catch_up_example_plans_end_to_end(world, rules_v2):
    # Week 1's Interior was missed; the run for week 2 plans it first (Monday 09-Nov)
    # and week 2's own Interior on its day (Thursday 12-Nov). Wednesday is off.
    sc = Scenario(world)
    sc.slots(off=(2,))
    sc.cleaner("Ravi", shift=(360, 660))
    car = sc.car(interior_day="Thursday")
    sc.entitlement(car, WEEK1)
    sc.run(WEEK2, days=7)
    sc.db.expire_all()
    rows = sc.db.execute(
        select(Visit.date, Job.service_week_start).join(Job, Job.visit_id == Visit.id)
        .where(Job.service == INTERNAL, Job.status != "Skipped").order_by(Visit.date)).all()
    assert rows == [(WEEK2, WEEK1), (WEEK2 + timedelta(days=3), WEEK2)]
    done = list(sc.db.scalars(select(InteriorEntitlement).order_by(InteriorEntitlement.service_week_start)))
    assert [r.status for r in done] == ["Planned", "Planned"]


def test_schr_int_10_an_overdue_interior_takes_a_weekday_before_the_weekend(world, rules_v2):
    # The period is Saturday 14-Nov to Tuesday 17-Nov. The week-1 Interior is overdue
    # and goes to Monday, not to the Saturday that is feasible too.
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", shift=(360, 660))
    car = sc.car(interior=True)
    sc.entitlement(car, WEEK1)
    sc.entitlement(car, WEEK2, status="Completed")
    sc.run(WEEK2 + timedelta(days=5), days=4)
    sc.db.expire_all()
    rows = sc.db.execute(
        select(Visit.date, Job.service_week_start).join(Job, Job.visit_id == Visit.id)
        .where(Job.service == INTERNAL, Job.status != "Skipped")).all()
    assert (WEEK3, WEEK1) in rows and all(d.weekday() < 5 for d, w in rows if w == WEEK1)


def test_schr_int_10_a_row_of_the_current_week_prefers_its_own_day_over_a_weekday_fallback(world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", shift=(360, 660))
    sc.car(interior_day="Saturday")
    sc.run(WEEK1, days=7)
    sc.db.expire_all()
    days = [d for d, in sc.db.execute(
        select(Visit.date).join(Job, Job.visit_id == Visit.id)
        .where(Job.service == INTERNAL, Job.status != "Skipped"))]
    assert days == [WEEK1 + timedelta(days=5)]
