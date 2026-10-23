"""S-05 move to a date, S-09 bulk reassign, S-12 bulk skip."""
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.directory.models import DirectoryAudit
from app.notifications.models import Notification
from app.scheduling.models import Job, Visit
from app.visits.models import JobReassignment
from tests.scheduling.conftest import PINNED_NOW, SUNDAY
from tests.scheduling.test_operations import setup


@pytest.fixture(autouse=True)
def pinned_today(monkeypatch):
    monkeypatch.setattr("app.visits.operations.today_ist", lambda: PINNED_NOW.date())


def audits(db, action):
    db.expire_all()
    return list(db.scalars(select(DirectoryAudit).where(DirectoryAudit.action == action)))


# ---- S-05 --------------------------------------------------------------------

def test_move_to_date_keeps_both_dates_and_plans_the_new_day(world, api, admin):
    _, _, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-Internal"]
    target = SUNDAY + timedelta(days=2)
    r = api.post(f"/v1/admin/scheduling/jobs/{job.id}/move-date", headers=admin,
                 json={"date": target.isoformat(), "reason": "Customer travelling"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["original"]["status"] == "Skipped"
    assert body["original"]["moved_to_date"] == target.isoformat()
    assert body["moved"]["date"] == target.isoformat()
    assert body["moved"]["moved_from_date"] == SUNDAY.isoformat()
    assert body["moved"]["crew_id"] is not None  # the normal planner placed it
    world.db.expire_all()
    assert str(world.db.get(Job, uuid.UUID(body["moved"]["id"])).source_job_id) == str(job.id)
    assert audits(world.db, "move-date")[0].detail["reason"] == "Customer travelling"
    # The original is closed, so it is not planned twice and cannot move again.
    again = api.post(f"/v1/admin/scheduling/jobs/{job.id}/move-date", headers=admin,
                     json={"date": target.isoformat(), "reason": "x"})
    assert again.status_code == 409


@pytest.mark.parametrize("payload,status", [
    ({"date": (PINNED_NOW.date() - timedelta(days=1)).isoformat(), "reason": "x"}, 422),
    ({"date": "2026-10-20", "reason": ""}, 422),
    ({"date": "2026-10-20", "reason": "   "}, 422),
    ({"date": SUNDAY.isoformat(), "reason": "x"}, 409),
])
def test_move_to_date_rules(world, api, admin, payload, status):
    _, _, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-Internal"]
    r = api.post(f"/v1/admin/scheduling/jobs/{job.id}/move-date", headers=admin, json=payload)
    assert r.status_code == status, r.text
    world.db.expire_all()
    assert world.db.get(Job, job.id).status == "Scheduled"


def test_move_to_date_refuses_a_duplicate_service(world, api, admin):
    _, _, _, jobs = setup(world, api, admin)
    r = api.post(f"/v1/admin/scheduling/jobs/{jobs['Cleaning-External'].id}/move-date",
                 headers=admin,
                 json={"date": (SUNDAY + timedelta(days=1)).isoformat(), "reason": "x"})
    assert r.status_code == 409
    assert r.json()["code"] == "duplicate_service"


def test_move_to_date_requires_admin(world, api, admin):
    _, _, _, jobs = setup(world, api, admin)
    r = api.post(f"/v1/admin/scheduling/jobs/{jobs['Cleaning-Internal'].id}/move-date",
                 json={"date": "2026-10-25", "reason": "x"})
    assert r.status_code == 401


# ---- S-09 --------------------------------------------------------------------

def two_crew(world, api, admin):
    a = world.add_crew(start=360, end=840, name="Ravi")
    b = world.add_crew(start=360, end=840, name="Sunil")
    vehicle = world.add_vehicle(interior_day="Sunday")
    world.db.commit()
    r = api.post("/v1/admin/scheduling/run", headers=admin, json={
        "society_id": str(world.society.id), "start_date": SUNDAY.isoformat(), "days": 7})
    assert r.status_code == 200, r.text
    world.db.expire_all()
    jobs = list(world.db.scalars(
        select(Job).join(Visit, Visit.id == Job.visit_id)
        .where(Visit.vehicle_id == vehicle.id, Visit.date == SUNDAY)))
    mine = a if jobs[0].crew_id == a.id else b
    return mine, (b if mine is a else a), jobs


def test_bulk_reassign_a_crew_day_writes_history_and_notifies(world, api, admin):
    mine, other, jobs = two_crew(world, api, admin)
    mine_jobs = [j for j in jobs if j.crew_id == mine.id]
    r = api.post("/v1/admin/scheduling/reassign", headers=admin, json={
        "from_crew_id": str(mine.id), "date": SUNDAY.isoformat(),
        "to_crew_id": str(other.id), "reason": "Ravi is unwell"})
    assert r.status_code == 200, r.text
    assert r.json()["reassigned"] == len(mine_jobs)
    assert all(x["ok"] for x in r.json()["results"])
    world.db.expire_all()
    assert all(world.db.get(Job, j.id).crew_id == other.id for j in mine_jobs)
    history = list(world.db.scalars(select(JobReassignment)))
    assert len(history) == len(mine_jobs)
    assert {h.to_crew_id for h in history} == {other.id}
    assert audits(world.db, "bulk-reassign")[0].detail["reason"] == "Ravi is unwell"
    events = {n.event for n in world.db.scalars(select(Notification))}
    assert "crew_job_reassigned" in events


def test_bulk_reassign_is_all_or_nothing(world, api, admin):
    mine, other, jobs = two_crew(world, api, admin)
    good = next(j for j in jobs if j.crew_id == mine.id)
    # A second job that cannot move: it has already started.
    stuck = Job(visit_id=good.visit_id, service="Deep Spa", duration_minutes=20,
                crew_id=mine.id, start_minute=700, status="In progress")
    world.db.add(stuck)
    world.db.commit()
    r = api.post("/v1/admin/scheduling/reassign", headers=admin, json={
        "job_ids": [str(good.id), str(stuck.id)],
        "to_crew_id": str(other.id), "reason": "Cover"})
    assert r.status_code == 409
    assert r.json()["code"] == "reassign_failed"
    assert r.json()["fields"] == {str(stuck.id): "job_not_open"}
    world.db.expire_all()
    assert world.db.get(Job, good.id).crew_id == mine.id
    assert list(world.db.scalars(select(JobReassignment))) == []
    assert audits(world.db, "bulk-reassign") == []


@pytest.mark.parametrize("patch", [{"reason": ""}, {"reason": "  "}, {"job_ids": []}])
def test_bulk_reassign_validates(world, api, admin, patch):
    _, other, jobs = two_crew(world, api, admin)
    body = {"job_ids": [str(jobs[0].id)], "to_crew_id": str(other.id), "reason": "x", **patch}
    assert api.post("/v1/admin/scheduling/reassign", headers=admin, json=body).status_code == 422


def test_bulk_reassign_needs_one_way_to_pick_jobs(world, api, admin):
    _, other, _ = two_crew(world, api, admin)
    r = api.post("/v1/admin/scheduling/reassign", headers=admin,
                 json={"to_crew_id": str(other.id), "reason": "x"})
    assert r.status_code == 422


# ---- S-12 --------------------------------------------------------------------

def test_bulk_skip_a_society_day(world, api, admin):
    _, _, visit, jobs = setup(world, api, admin)
    r = api.post("/v1/admin/operations/bulk-skip", headers=admin, json={
        "society_id": str(world.society.id), "date": SUNDAY.isoformat(),
        "reason": "Water shut-off", "note": "Society notice"})
    assert r.status_code == 200, r.text
    assert r.json()["visits_skipped"] == 1 and r.json()["jobs_skipped"] == len(jobs)
    world.db.expire_all()
    assert all(world.db.get(Job, j.id).status == "Skipped" for j in jobs.values())
    assert len(audits(world.db, "bulk-skip-visit")) == 1
    assert audits(world.db, "bulk-skip")[0].detail["visits"] == 1
    # Nothing is left open on the visit, so a second call is refused.
    again = api.post("/v1/admin/operations/bulk-skip", headers=admin, json={
        "visit_ids": [str(visit.id)], "reason": "Water shut-off"})
    assert again.status_code == 409


def test_bulk_skip_needs_a_reason_and_is_all_or_nothing(world, api, admin):
    _, _, visit, jobs = setup(world, api, admin)
    blank = api.post("/v1/admin/operations/bulk-skip", headers=admin,
                     json={"visit_ids": [str(visit.id)], "reason": " "})
    assert blank.status_code == 422
    missing = api.post("/v1/admin/operations/bulk-skip", headers=admin, json={
        "visit_ids": [str(visit.id), "00000000-0000-0000-0000-000000000001"], "reason": "Rain"})
    assert missing.status_code == 404
    both = api.post("/v1/admin/operations/bulk-skip", headers=admin, json={
        "visit_ids": [str(visit.id)], "society_id": str(world.society.id),
        "date": SUNDAY.isoformat(), "reason": "Rain"})
    assert both.status_code == 422
    world.db.expire_all()
    assert all(world.db.get(Job, j.id).status == "Scheduled" for j in jobs.values())
    assert audits(world.db, "bulk-skip") == []


def test_bulk_skip_takes_a_reason_key(world, api, admin):
    _, _, visit, _ = setup(world, api, admin)
    r = api.post("/v1/admin/operations/bulk-skip", headers=admin,
                 json={"visit_ids": [str(visit.id)], "reason_key": "bad_weather"})
    assert r.status_code == 200, r.text
    assert audits(world.db, "bulk-skip")[0].detail["reason"] == "Bad weather"


def test_customer_calendar_shows_the_moved_service_on_the_new_date(world, api, admin):
    from tests.test_api import auth, login

    vehicle, _, _, jobs = setup(world, api, admin)
    target = SUNDAY + timedelta(days=2)
    moved = api.post(f"/v1/admin/scheduling/jobs/{jobs['Cleaning-Internal'].id}/move-date",
                     headers=admin, json={"date": target.isoformat(), "reason": "Away"}).json()
    customer = auth(login(api, "customer")["access_token"])
    cal = api.get(f"/v1/customer/calendar?month=2026-10&vehicle_id={vehicle.id}",
                  headers=customer).json()
    shown = next(v for v in cal["visits"] if v["visit_id"] == moved["moved"]["visit_id"])
    assert shown["date"] == target.isoformat()
    assert "Cleaning-Internal" in str(shown["services"])
