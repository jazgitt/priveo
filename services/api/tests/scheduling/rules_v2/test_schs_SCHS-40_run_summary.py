"""SCHS-40: the run summary and the schedule history carry the new counts."""
from sqlalchemy import select

from app.scheduling import run_counts, service
from app.scheduling.models import Job, SchedulingEvent
from tests.scheduling.builders import EXTERNAL, INTERNAL, Scenario
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login


def _post_run(api, world):
    admin = auth(login(api, "admin")["access_token"])
    r = api.post("/v1/admin/scheduling/run", headers=admin, json={
        "society_id": str(world.society.id), "start_date": SUNDAY.isoformat(), "days": 1})
    assert r.status_code == 200, r.text
    return r.json()["schedules"][0]


def _short_day(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 540))  # room for two 30 minute jobs
    return sc


def test_schr_out_07_the_summary_counts_unassigned_exteriors_and_unplanned_interiors(
        api, world):
    sc = _short_day(world)
    sc.cars(2)
    sc.car(interior=True)  # its Interior has no room left
    sc.db.commit()
    run = _post_run(api, world)
    # Four jobs, room for two: which two lose is the solver's choice.
    assert run["unscheduled"] == 2
    assert run["unassigned_exteriors"] + run["deferred_interiors"] == 2
    assert run["deferred_interiors"] in (0, 1)
    assert run["cross_zone_jobs"] == 0 and run["missed_breaks"] == 0


def test_schr_out_07_deferred_jobs_and_cross_zone_jobs_are_counted(world):
    sc = _short_day(world)
    car = sc.car(interior=True)
    sc.db.commit()
    summary = service.run(sc.db, sc.site.id, SUNDAY, 1, None)[0]
    interior = sc.db.scalar(select(Job).where(Job.service == INTERNAL))
    interior.status = "Deferred"
    exterior = sc.db.scalar(select(Job).where(Job.service == EXTERNAL))
    exterior.cross_zone_reason = "Zone B had no cleaner"
    sc.db.flush()
    ctx = type("Ctx", (), {"active": True, "findings": [{"code": "break_missed"}]})()
    found = run_counts.counts(ctx, [interior, exterior])
    assert found == {"deferred_interiors": 1, "cross_zone_jobs": 1, "missed_breaks": 1}
    assert car and summary.placed >= 1


def test_schr_out_07_the_run_is_recorded_in_the_history_with_the_counts(world):
    sc = _short_day(world)
    sc.cars(3)
    sc.db.commit()
    summary = service.run(sc.db, sc.site.id, SUNDAY, 1, None)[0]
    event = sc.db.scalar(select(SchedulingEvent).where(
        SchedulingEvent.schedule_id == summary.schedule_id, SchedulingEvent.kind == "rerun"))
    assert "unassigned exteriors 1" in event.detail
    assert "deferred interiors 0" in event.detail and "missed breaks 0" in event.detail

