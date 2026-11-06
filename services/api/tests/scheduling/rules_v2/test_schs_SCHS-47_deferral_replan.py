"""SCHS-47: a Deferred Interior goes back to Pending and is planned again."""
from datetime import date, timedelta

from sqlalchemy import select

from app.directory.models import CncReason
from app.scheduling.models import InteriorEntitlement, Job, Visit
from app.visits import schemas as s
from app.visits import service as visits
from tests.scheduling.builders import INTERNAL, Scenario

WEEK1 = date(2026, 11, 2)
THURSDAY = WEEK1 + timedelta(days=3)


def _plan_and_defer(world):
    world.db.add(CncReason(key="car_locked", label="Car is locked", defers=True))
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(360, 660))
    car = sc.car(interior_day="Thursday")
    sc.run(WEEK1, days=7)
    job = sc.db.scalar(select(Job).where(Job.service == INTERNAL))
    visits.could_not_complete(
        sc.db, job, s.CouldNotComplete(reason_key="car_locked", note="Locked"),
        world.customer_login.id)
    sc.db.expire_all()
    return sc, car, job.id


def _live(sc):
    return [(d, j) for d, j in sc.db.execute(
        select(Visit.date, Job).join(Job, Job.visit_id == Visit.id)
        .where(Job.service == INTERNAL).order_by(Visit.date)).all() if j.status == "Scheduled"]


def test_schr_def_03_a_deferred_interior_goes_back_to_pending_with_its_week(world, rules_v2):
    sc, car, job_id = _plan_and_defer(world)
    assert sc.db.get(Job, job_id).status == "Deferred"
    (row,) = sc.db.scalars(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == car.id))
    assert (row.status, row.job_id, row.service_week_start) == ("Pending", None, WEEK1)


def test_schr_def_02_the_deferred_job_is_planned_at_the_next_run_in_the_same_week(
        world, rules_v2):
    sc, car, job_id = _plan_and_defer(world)
    sc.run(WEEK1, days=7)
    ((day, job),) = _live(sc)
    assert job.id != job_id and day > THURSDAY
    assert job.service_week_start == WEEK1
    # The deferred job itself is never shown as Completed.
    assert sc.db.get(Job, job_id).status == "Deferred"
    (row,) = sc.db.scalars(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == car.id))
    assert (row.status, row.job_id) == ("Planned", job.id)


def test_schr_def_03_done_on_the_retry_it_completes_the_original_week(world, rules_v2):
    from app.scheduling import service
    sc, car, _job_id = _plan_and_defer(world)
    sc.run(WEEK1, days=7)
    ((_day, job),) = _live(sc)
    service.set_job_status(sc.db, job.id, "Completed")
    sc.db.expire_all()
    (row,) = sc.db.scalars(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == car.id))
    assert (row.status, row.job_id, row.service_week_start) == ("Completed", job.id, WEEK1)


def test_schr_def_02_version_1_does_not_touch_the_ledger(world):
    sc = Scenario(world)
    car = sc.car()
    row = sc.entitlement(car, WEEK1, status="Planned")
    schedule_job = Job(visit_id=_visit(sc, car).id, service=INTERNAL, duration_minutes=30,
                       status="Deferred")
    sc.db.add(schedule_job)
    sc.db.flush()
    row.job_id = schedule_job.id
    from app.scheduling import hooks
    hooks.job_status_changed(sc.db, schedule_job, "crew")
    assert sc.db.get(InteriorEntitlement, row.id).status == "Planned"


def _visit(sc, car):
    from app.scheduling import service
    schedule = service.get_or_create_schedule(sc.db, sc.site.id, WEEK1, 7)
    visit = Visit(schedule_id=schedule.id, vehicle_id=car.id, date=WEEK1)
    sc.db.add(visit)
    sc.db.flush()
    return visit
