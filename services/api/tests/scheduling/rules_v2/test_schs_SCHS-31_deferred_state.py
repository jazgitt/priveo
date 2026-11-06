"""SCHS-31: a reason marked "defers" gives the Deferred state."""
from datetime import date

import pytest
from sqlalchemy import select

from app.directory.models import CncReason
from app.scheduling import outcomes, rules
from app.scheduling.models import JOB_STATUSES, Job, Visit
from app.visits import schemas as s
from app.visits import service as visits
from tests.scheduling.builders import EXTERNAL, INTERNAL, Scenario
from tests.test_api import auth, login

DAY = date(2026, 11, 3)


@pytest.fixture
def reasons(world):
    world.db.add_all([
        CncReason(key="car_locked", label="Car is locked", sort_order=0, defers=True),
        CncReason(key="other", label="Other", sort_order=1, defers=False),
    ])
    world.db.flush()


def _visit_jobs(sc, services=(EXTERNAL, INTERNAL)):
    from app.scheduling import service
    car = sc.car()
    schedule = service.get_or_create_schedule(sc.db, sc.site.id, DAY, 1)
    visit = Visit(schedule_id=schedule.id, vehicle_id=car.id, date=DAY)
    sc.db.add(visit)
    sc.db.flush()
    jobs = {}
    for name in services:
        jobs[name] = Job(visit_id=visit.id, service=name, duration_minutes=30)
        sc.db.add(jobs[name])
    sc.db.flush()
    return visit, jobs


def _not_done(sc, job, key):
    sc.db.commit()
    return visits.could_not_complete(
        sc.db, job, s.CouldNotComplete(reason_key=key, note="Car locked"), sc.world.customer_login.id)


def test_schr_def_01_a_reason_that_defers_gives_deferred_never_completed(world, reasons, rules_v2):
    sc = Scenario(world)
    visit, jobs = _visit_jobs(sc)
    job = _not_done(sc, jobs[INTERNAL], "car_locked")
    assert job.status == "Deferred" and "Deferred" in JOB_STATUSES
    sc.db.refresh(visit)
    assert visit.status != "Completed"


def test_schr_def_04_the_reasons_are_read_from_the_table(world, reasons, rules_v2):
    sc = Scenario(world)
    _visit, jobs = _visit_jobs(sc)
    assert _not_done(sc, jobs[INTERNAL], "other").status == "Could not complete"
    # Flip the switch in the table: the same reason now defers.
    world.db.execute(CncReason.__table__.update().where(CncReason.key == "other").values(defers=True))
    world.db.commit()
    _visit, jobs = _visit_jobs(sc)
    assert _not_done(sc, jobs[INTERNAL], "other").status == "Deferred"


def test_schr_def_05_version_1_keeps_could_not_complete(world, reasons):
    sc = Scenario(world)
    _visit, jobs = _visit_jobs(sc)
    assert _not_done(sc, jobs[INTERNAL], "car_locked").status == "Could not complete"


def test_schr_def_05_a_partial_visit_still_offers_the_next_day_decision(world, reasons, rules_v2):
    """Partial completion (ADM-CNC-10) is the Could not complete path: a reason
    that does not defer leaves the job open to the admin's resolve."""
    sc = Scenario(world)
    visit, jobs = _visit_jobs(sc)
    from app.scheduling import service
    service.set_job_status(sc.db, jobs[EXTERNAL].id, "Completed")
    job = _not_done(sc, jobs[INTERNAL], "other")
    assert job.status == "Could not complete"
    assert outcomes.outcome_of_visit(sc.db, visit).outcome == "Partially Completed"


def test_schr_def_01_a_deferred_job_is_not_done_in_the_visit_outcome():
    assert outcomes.outcome_of(["Completed", "Deferred"]) == "Partially Completed"
    assert outcomes.outcome_of(["Deferred"]) == "Not Completed"
    assert rules.visit_status(["Completed", "Deferred"]) == "Could not complete"
    assert rules.visit_status(["Deferred"]) != "Completed"


def test_schr_def_01_the_deferred_job_is_closed_to_the_crew(world, reasons, rules_v2):
    from app.platform.errors import ApiError
    sc = Scenario(world)
    _visit, jobs = _visit_jobs(sc)
    _not_done(sc, jobs[INTERNAL], "car_locked")
    with pytest.raises(ApiError) as err:
        visits._open_job(sc.db.get(Job, jobs[INTERNAL].id))
    assert err.value.code == "job_closed"


def test_schr_def_04_the_admin_marks_a_reason_as_deferring(api, world):
    admin = auth(login(api, "admin")["access_token"])
    r = api.post("/v1/admin/directory/reasons", headers=admin,
                 json={"label": "Keys not given", "defers": True})
    assert r.status_code == 201 and r.json()["defers"] is True
    rid = r.json()["id"]
    r = api.patch(f"/v1/admin/directory/reasons/{rid}", headers=admin,
                  json={"label": "Keys not given", "defers": False})
    assert r.json()["defers"] is False
    r = api.patch(f"/v1/admin/directory/reasons/{rid}", headers=admin, json={"label": "Keys missing"})
    assert r.json()["defers"] is False and r.json()["label"] == "Keys missing"
    world.db.expire_all()
    row = world.db.scalar(select(CncReason).where(CncReason.key == r.json()["key"]))
    assert row.defers is False
