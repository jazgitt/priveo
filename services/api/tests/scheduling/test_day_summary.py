"""A-02 the admin day summary, C-06 missed and partial visits are never dropped,
A-04 audit rows for moves, freeze and unfreeze."""
from sqlalchemy import select

from app.directory.models import DirectoryAudit
from app.scheduling import service
from app.scheduling.models import Job
from tests.scheduling.conftest import SUNDAY
from tests.scheduling.test_operations import missed, pinned_today, resolve, setup  # noqa: F401
from tests.scheduling.test_partial_outcomes import queue

STATES = ("completed", "pending", "missed", "partially_completed", "skipped",
          "rescheduled", "cancelled")


def summary(api, admin, **params):
    r = api.get("/v1/admin/home/day-summary", headers=admin,
                params={"date": SUNDAY.isoformat(), **params})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_partial_visit_is_counted_listed_and_kept_after_follow_up(world, api, admin):
    vehicle, _, visit, jobs = setup(world, api, admin)
    before = summary(api, admin)
    assert before["total"] == 1 and before["pending"]["count"] == 1
    service.set_job_status(world.db, jobs["Cleaning-External"].id, "Completed")
    missed(world, jobs["Cleaning-Internal"])

    day = summary(api, admin)
    assert day["partially_completed"]["count"] == 1 and day["pending"]["count"] == 0
    item = day["partially_completed"]["items"][0]
    assert item["id"] == str(visit.id) and item["registration"] == vehicle.registration
    assert item["reason"] and item["crew"] and item["time"]
    # C-06: in the Operations queue, and still there after the admin reschedules it.
    assert any(r["id"] == str(jobs["Cleaning-Internal"].id) for r in queue(api, admin))
    assert resolve(api, admin, jobs["Cleaning-Internal"], "Reschedule").status_code == 200
    assert any(r["id"] == str(jobs["Cleaning-Internal"].id) for r in queue(api, admin, "history"))
    assert summary(api, admin)["partially_completed"]["count"] == 1
    world.db.expire_all()
    assert world.db.get(Job, jobs["Cleaning-Internal"].id) is not None
    assert "Asha" not in str(day) and "9876543210" not in str(day)


def test_a_missed_visit_is_counted_and_the_filters_apply(world, api, admin):
    vehicle, _, visit, jobs = setup(world, api, admin)
    missed(world, jobs["Cleaning-External"])
    missed(world, jobs["Cleaning-Internal"])
    assert any(r["id"] == str(jobs["Cleaning-External"].id) for r in queue(api, admin))
    day = summary(api, admin)
    assert day["missed"]["count"] == 1 and day["missed"]["more"] == 0
    assert sum(day[k]["count"] for k in STATES) == day["total"]
    crew_id = str(jobs["Cleaning-External"].crew_id)
    assert summary(api, admin, crew_id=crew_id)["missed"]["count"] == 1
    assert summary(api, admin, vehicle_id=str(vehicle.id))["total"] == 1
    assert summary(api, admin, vehicle_id=crew_id)["total"] == 0  # a crew id is not a vehicle
    assert summary(api, admin, crew_id=str(vehicle.id))["total"] == 0


def test_an_all_skipped_visit_is_listed_as_skipped(world, api, admin):
    _, _, _, jobs = setup(world, api, admin)
    for j in jobs.values():
        service.set_job_status(world.db, j.id, "Skipped")
    day = summary(api, admin)
    assert day["skipped"]["count"] == 1 and day["total"] == 1


def test_an_empty_day_and_the_default_date(world, api, admin):
    assert summary(api, admin, date="2030-01-01")["total"] == 0
    assert api.get("/v1/admin/home/day-summary", headers=admin).status_code == 200


def test_the_day_summary_is_admin_only(api, world):
    assert api.get("/v1/admin/home/day-summary").status_code == 401


def test_taking_a_job_off_audits_crew_and_time_and_freeze_is_audited(world, api, admin):
    _, sid, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-External"]
    old = (str(job.crew_id), job.start_minute)
    r = api.post(f"/v1/admin/scheduling/jobs/{job.id}/move", headers=admin,
                 json={"crew_id": None})
    assert r.status_code == 200, r.text
    world.db.expire_all()
    audits = world.db.scalars(select(DirectoryAudit).where(
        DirectoryAudit.entity == "schedule")).all()
    move = next(a for a in audits if a.action == "move")
    assert move.admin_login_id is not None and len(move.entity) <= 24
    assert move.detail["crew_id"] == [old[0], None]
    assert move.detail["start_minute"] == [old[1], None]
    freeze = next(a for a in audits if a.action == "freeze")
    assert freeze.admin_login_id is not None
    r = api.post(f"/v1/admin/scheduling/schedules/{sid}/unfreeze", headers=admin,
                 json={"code": "unfreeze"})
    assert r.status_code == 200, r.text
    world.db.expire_all()
    assert world.db.scalar(select(DirectoryAudit).where(
        DirectoryAudit.entity == "schedule", DirectoryAudit.action == "unfreeze")) is not None
