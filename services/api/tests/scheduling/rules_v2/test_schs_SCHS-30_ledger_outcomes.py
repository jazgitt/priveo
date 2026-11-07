"""SCHS-30: the ledger follows job outcomes."""
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.customers.models import Subscription
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
def sc(world):
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


# ---- ledger and link paths (gap check, 06-Nov-26) ---------------------------


def _unplanned_interior(sc, car, day, status="Scheduled"):
    visit = Visit(schedule_id=service.get_or_create_schedule(sc.db, sc.site.id, day, 1).id,
                  vehicle_id=car.id, date=day)
    sc.db.add(visit)
    sc.db.flush()
    job = Job(visit_id=visit.id, service=INTERNAL, duration_minutes=30, status=status)
    sc.db.add(job)
    sc.db.flush()
    return visit, job


def test_schr_int_24_a_completed_interior_with_nothing_owed_is_not_against_the_ledger(sc):
    car = sc.car()
    _visit, job = _unplanned_interior(sc, car, WEEK1)
    sc.db.commit()
    _status(sc, job, "Completed")  # the car owes nothing: no row is made for it
    assert sc.db.scalar(select(func.count()).select_from(InteriorEntitlement)
                        .where(InteriorEntitlement.vehicle_id == car.id)) == 0


def test_schr_int_24_a_planned_interior_that_is_skipped_returns_its_row_to_pending(sc):
    car = sc.car()
    row, job = _planned(sc, car, WEEK1, WEEK1)
    _status(sc, job, "Skipped")
    row = sc.db.get(InteriorEntitlement, row.id)
    assert (row.status, row.job_id) == (entitlements.PENDING, None)


def test_schr_int_14_the_link_falls_back_to_the_oldest_owed_row_when_the_chosen_row_is_not_pending(sc):
    from types import SimpleNamespace

    from app.scheduling.post_solve import entitlement_link

    car = sc.car()
    done = sc.entitlement(car, WEEK1, status="Completed")  # chosen, but already used
    owed = sc.entitlement(car, WEEK2)                      # the oldest row still owed
    visit, job = _unplanned_interior(sc, car, WEEK2 + timedelta(days=1))
    sc.db.commit()
    ctx = SimpleNamespace(db=sc.db, interior_rows={(car.id, visit.date): done.id})
    entitlement_link.after_solve(ctx, visit.date, [(job, visit)], None)
    sc.db.expire_all()
    assert sc.db.get(InteriorEntitlement, owed.id).job_id == job.id
    assert sc.db.get(InteriorEntitlement, done.id).job_id is None


def test_schr_int_12_the_owed_check_and_the_week_rows_read_the_ledger(sc):
    car = sc.car(interior=True)  # an Exterior-only car owes no Interior
    row = sc.entitlement(car, WEEK1)
    sub = sc.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    assert entitlements.owes(sc.db, sub, WEEK1) is True
    assert [r.id for r in entitlements.rows_for_week(sc.db, car.id, WEEK1)] == [row.id]
    assert entitlements.rows_for_week(sc.db, car.id, WEEK2) == []


def test_schr_dur_01_a_service_without_a_configured_duration_keeps_its_own(world):
    from types import SimpleNamespace

    from app.scheduling.job_sync import duration

    job = SimpleNamespace(status="Scheduled", service="No such service", duration_minutes=45)
    duration.sync(SimpleNamespace(frozen=False, db=world.db), job, None)
    assert job.duration_minutes == 45


def test_schr_int_16_a_planned_interior_whose_job_is_gone_goes_back_to_pending(sc):
    # The planner finds the row planned but holds no job for it. The row is put
    # back to pending and planned again in the same run: it is not lost.
    car = sc.car(interior=True)
    row, _job = _planned(sc, car, WEEK1, WEEK1)
    sc.db.commit()
    row = sc.db.get(InteriorEntitlement, row.id)
    row.job_id = None
    sc.db.commit()
    sc.run(WEEK1, days=7)
    row = sc.db.get(InteriorEntitlement, row.id)
    assert row.status == entitlements.PLANNED and row.job_id is not None
