"""SCHS-36: Interior jobs come from pending entitlements."""
from datetime import date, timedelta

from sqlalchemy import select

from app.customers.models import SchedulePattern, Subscription
from app.directory.models import WorkingSlot
from app.scheduling.models import InteriorEntitlement, Job, Visit
from tests.scheduling.builders import INTERNAL, Scenario

WEEK1 = date(2026, 11, 2)  # Monday
WEEK2 = WEEK1 + timedelta(days=7)
THURSDAY = WEEK1 + timedelta(days=3)


def _scenario(world, off=(), **car):
    sc = Scenario(world)
    sc.slots(off=off)
    sc.cleaner(shift=(360, 660))
    return sc, sc.car(**car)


def _interiors(sc):
    sc.db.expire_all()
    return sc.db.execute(
        select(Visit.date, Job).join(Job, Job.visit_id == Visit.id)
        .where(Job.service == INTERNAL, Job.status != "Skipped").order_by(Visit.date)).all()


def _rows(sc, car):
    return list(sc.db.scalars(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == car.id).order_by(InteriorEntitlement.service_week_start)))


def test_schr_int_01_an_interior_is_planned_for_the_pending_entitlement_of_the_week(
        world):
    sc, car = _scenario(world, interior_day="Thursday")
    sc.run(WEEK1, days=7)
    ((day, job),) = _interiors(sc)
    assert day == THURSDAY and job.service_week_start == WEEK1
    (row,) = _rows(sc, car)
    assert (row.status, row.job_id) == ("Planned", job.id)


def test_schr_int_01_no_entitlement_means_no_interior(world):
    sc, car = _scenario(world, interior_day="Thursday")
    sc.entitlement(car, WEEK1, status="Completed")
    sc.run(WEEK1, days=7)
    assert _interiors(sc) == []


def test_schr_int_05_the_preferred_day_is_a_tie_break_only(world):
    # Thursday is the car's day, but the site has no Interior slot on Thursday (3).
    sc, car = _scenario(world, interior_day="Thursday")
    sc.db.query(WorkingSlot).filter_by(service=INTERNAL).update({"days": [0, 1, 2, 4, 5, 6]})
    sc.run(WEEK1, days=7)
    ((day, _job),) = _interiors(sc)
    assert day != THURSDAY and WEEK1 <= day < WEEK2  # still planned, on another day
    assert _rows(sc, car)[0].status == "Planned"


def test_schr_int_05_without_a_preference_the_first_feasible_day_is_used(world):
    sc, _car = _scenario(world, interior=True)
    sc.run(WEEK1, days=7)
    ((day, _job),) = _interiors(sc)
    assert day == WEEK1


def test_schr_int_26_a_weekly_pattern_feeds_the_preference(world):
    sc, car = _scenario(world, interior=True)
    sub = sc.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    sc.db.add(SchedulePattern(subscription_id=sub.id, kind="Weekly",
                              exterior_weekdays=["Monday", "Friday"],
                              interior_weekdays=["Friday"]))
    sc.run(WEEK1, days=7)
    ((day, _job),) = _interiors(sc)
    assert day == WEEK1 + timedelta(days=4)  # Friday
    assert len(_rows(sc, car)) == 1  # the pattern did not add a second entitlement


def test_schr_int_13_an_overdue_week_is_planned_before_the_new_week(world):
    sc, car = _scenario(world, interior_day="Monday")
    sc.entitlement(car, WEEK1)  # week 1 was missed and is still owed
    sc.run(WEEK2, days=7)
    found = _interiors(sc)
    assert [d for d, _j in found] == [WEEK2, WEEK2 + timedelta(days=1)]  # separate days
    assert [j.service_week_start for _d, j in found] == [WEEK1, WEEK2]
    assert {r.status for r in _rows(sc, car)} == {"Planned"}


def test_schr_hard_11_one_interior_for_a_car_on_a_day(world):
    sc, car = _scenario(world, interior_day="Monday")
    sc.entitlement(car, WEEK1)
    sc.entitlement(car, WEEK1 - timedelta(days=7))
    sc.run(WEEK2, days=7)
    days = [d for d, _j in _interiors(sc)]
    assert len(days) == len(set(days)) == 3


def test_schr_int_06_a_rerun_keeps_the_planned_interior_and_adds_none(world):
    sc, car = _scenario(world, interior_day="Thursday")
    sc.run(WEEK1, days=7)
    first = _interiors(sc)
    sc.run(WEEK1, days=7)
    again = _interiors(sc)
    assert [(d, j.id) for d, j in first] == [(d, j.id) for d, j in again]
    assert len(_rows(sc, car)) == 1


def test_schr_def_03_a_deferred_interior_is_planned_again_on_a_later_day(world):
    sc, car = _scenario(world, interior_day="Thursday")
    sc.run(WEEK1, days=7)
    ((_day, job),) = _interiors(sc)
    from app.scheduling import service
    service.set_job_status(sc.db, job.id, "Could not complete")
    sc.run(WEEK1, days=7)
    live = [(d, j) for d, j in _interiors(sc) if j.status == "Scheduled"]
    assert len(live) == 1 and live[0][0] > THURSDAY
    assert live[0][1].service_week_start == WEEK1


def test_schr_ext_11_the_exterior_is_planned_each_day_and_is_not_ledger_demand(world):
    sc, car = _scenario(world, interior_day="Thursday")
    sc.run(WEEK1, days=7)
    sc.db.expire_all()
    days = sc.db.scalars(select(Visit.date).join(Job, Job.visit_id == Visit.id).where(
        Visit.vehicle_id == car.id, Job.service == "Cleaning-External")).all()
    assert sorted(set(days)) == [WEEK1 + timedelta(days=i) for i in range(7)]
    assert all(r.service_week_start.weekday() == 0 for r in _rows(sc, car))
