"""SCHS-30: the ledger follows job outcomes."""
from datetime import date, timedelta

import pytest

from app.scheduling import entitlements, service
from app.scheduling.models import InteriorEntitlement, Job, Visit
from tests.scheduling.builders import INTERNAL, Scenario

WEEK1 = date(2026, 11, 2)  # Monday
WEEK2 = WEEK1 + timedelta(days=7)


def _planned(sc, car, week, day):
    """An Interior job on `day` held by the row of `week`."""
    row = sc.entitlement(car, week)
    schedule = service.get_or_create_schedule(sc.db, sc.site.id, day, 1)
    visit = Visit(schedule_id=schedule.id, vehicle_id=car.id, date=day)
    sc.db.add(visit)
    sc.db.flush()
    job = Job(visit_id=visit.id, service=INTERNAL, duration_minutes=30)
    sc.db.add(job)
    sc.db.flush()
    entitlements.plan(sc.db, row, job)
    return row, job


def _status(sc, job, status):
    sc.db.commit()
    service.set_job_status(sc.db, job.id, status)
    sc.db.expire_all()


@pytest.fixture
def sc(world, rules_v2):
    return Scenario(world)


def test_schr_int_14_an_overdue_interior_done_in_week_2_completes_week_1(sc):
    car = sc.car()
    row1, job = _planned(sc, car, WEEK1, WEEK2)
    row2 = sc.entitlement(car, WEEK2)
    _status(sc, job, "Completed")
    row1, row2 = sc.db.get(InteriorEntitlement, row1.id), sc.db.get(InteriorEntitlement, row2.id)
    assert (row1.status, row1.job_id, row1.service_week_start) == ("Completed", job.id, WEEK1)
    assert row1.completed_on is not None
    assert sc.db.get(Job, job.id).service_week_start == WEEK1


def test_schr_int_15_week_2_stays_pending_when_week_1_is_done(sc):
    car = sc.car()
    _row1, job = _planned(sc, car, WEEK1, WEEK2)
    row2 = sc.entitlement(car, WEEK2)
    _status(sc, job, "Completed")
    assert sc.db.get(InteriorEntitlement, row2.id).status == "Pending"


def test_schr_int_16_could_not_complete_returns_the_row_to_pending_with_its_week(sc):
    car = sc.car()
    row, job = _planned(sc, car, WEEK1, WEEK1)
    _status(sc, job, "Could not complete")
    row = sc.db.get(InteriorEntitlement, row.id)
    assert (row.status, row.job_id, row.service_week_start) == ("Pending", None, WEEK1)


def test_schr_def_06_a_pending_interior_never_expires(sc):
    car = sc.car()
    row, job = _planned(sc, car, WEEK1, WEEK1)
    _status(sc, job, "Could not complete")
    # Weeks later the row is still owed and is the oldest owed.
    assert entitlements.oldest_owed(sc.db, car.id).id == row.id
    assert entitlements.claim(sc.db, car.id, WEEK1).id == row.id


def test_schr_int_21_an_operations_skip_leaves_the_week_owed(sc):
    car = sc.car()
    row, job = _planned(sc, car, WEEK1, WEEK1)
    _status(sc, job, "Skipped")
    assert sc.db.get(InteriorEntitlement, row.id).status == "Pending"


def test_schr_int_24_a_hand_placed_interior_counts_against_the_oldest_pending_week(sc):
    car = sc.car()
    row1, row2 = sc.entitlement(car, WEEK1), sc.entitlement(car, WEEK2)
    schedule = service.get_or_create_schedule(sc.db, sc.site.id, WEEK2, 1)
    visit = Visit(schedule_id=schedule.id, vehicle_id=car.id, date=WEEK2)
    sc.db.add(visit)
    sc.db.flush()
    job = Job(visit_id=visit.id, service=INTERNAL, duration_minutes=30, manual=True)
    sc.db.add(job)
    sc.db.flush()
    _status(sc, job, "Completed")
    assert sc.db.get(InteriorEntitlement, row1.id).status == "Completed"
    assert sc.db.get(InteriorEntitlement, row1.id).job_id == job.id
    assert sc.db.get(InteriorEntitlement, row2.id).status == "Pending"


def test_schr_int_22_an_exterior_does_not_touch_the_ledger(sc):
    car = sc.car()
    row, job = _planned(sc, car, WEEK1, WEEK1)
    other = Job(visit_id=job.visit_id, service=INTERNAL, duration_minutes=30)
    # An Exterior is not an Interior.
    other.service = "Cleaning-External"
    sc.db.add(other)
    sc.db.flush()
    _status(sc, other, "Completed")
    assert sc.db.get(InteriorEntitlement, row.id).status == "Planned"


def test_schs_30_version_1_leaves_the_ledger_alone(world):
    sc = Scenario(world)  # no rules_v2 fixture: the site is on version 1
    car = sc.car()
    row, job = _planned(sc, car, WEEK1, WEEK1)
    _status(sc, job, "Completed")
    assert sc.db.get(InteriorEntitlement, row.id).status == "Planned"
