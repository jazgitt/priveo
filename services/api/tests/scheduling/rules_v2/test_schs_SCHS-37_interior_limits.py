"""SCHS-37: one Interior per service week and per car per day."""
from datetime import date, timedelta

from sqlalchemy import select

from app.scheduling.codes import ReasonCode
from app.scheduling.models import Job
from app.scheduling.solver import SolverCrew, SolverJob, solve_day
from tests.scheduling.builders import INTERNAL, Scenario

WEEK1 = date(2026, 11, 2)
WEEK2 = WEEK1 + timedelta(days=7)
CREW = [SolverCrew("a", 480, 720)]  # four hours: room for everything below


def _int(key, car="creta", **kw):
    return SolverJob(key, car, 30, interior=True, **kw)


def test_schr_hard_11_a_car_gets_one_interior_in_a_day():
    result = solve_day(CREW, [_int("one", week=WEEK1), _int("two", week=WEEK2)])
    assert len(result.placed) == 1 and len(result.unplaced) == 1
    (loser,) = result.unplaced_codes
    assert result.unplaced_codes[loser] is ReasonCode.ENTITLEMENT_USED


def test_schr_hard_10_one_interior_against_a_service_week():
    result = solve_day(CREW, [_int("a", week=WEEK1), _int("b", week=WEEK1)])
    assert len(result.placed) == 1
    assert list(result.unplaced_codes.values()) == [ReasonCode.ENTITLEMENT_USED]


def test_schr_hard_11_a_kept_interior_takes_the_cars_day():
    kept = _int("kept", week=WEEK1, fixed=("a", 480))
    result = solve_day(CREW, [kept, _int("new", week=WEEK2)])
    assert set(result.placed) == {"kept"}
    assert result.unplaced_codes == {"new": ReasonCode.ENTITLEMENT_USED}


def test_schr_hard_11_two_cars_each_get_their_interior_and_exteriors_are_free():
    jobs = [_int("c1", car="c1"), _int("c2", car="c2"),
            SolverJob("e1", "c1", 30), SolverJob("e2", "c1", 30)]
    result = solve_day(CREW, jobs)
    assert set(result.placed) == {"c1", "c2", "e1", "e2"}


def test_schr_hard_11_a_job_not_marked_interior_is_not_limited():
    # Version 1, an add-on Interior or a Deep Spa carry no flag.
    jobs = [SolverJob("a", "creta", 30), SolverJob("b", "creta", 30)]
    assert len(solve_day(CREW, jobs).placed) == 2


def test_schr_int_18_a_catch_up_week_has_two_interiors_on_separate_days(world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(360, 660))
    car = sc.car(interior_day="Monday")
    sc.entitlement(car, WEEK1)  # week 1 is overdue
    sc.run(WEEK2, days=7)
    rows = sc.db.execute(select(Job.service_week_start, Job.status).where(
        Job.service == INTERNAL).order_by(Job.service_week_start)).all()
    assert [r[0] for r in rows] == [WEEK1, WEEK2]
    days = sc.read().placed
    interior_days = sorted(p.day for p in days if p.service == INTERNAL)
    assert len(interior_days) == 2 and interior_days[0] != interior_days[1]
