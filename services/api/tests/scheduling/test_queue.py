"""The crew's sequential queue (S-13, C-01, C-02, C-04, B-06)."""
import uuid
from datetime import time

from sqlalchemy import select

from app.directory.models import DirectoryAudit
from app.features import service as features
from app.identity.models import Login
from app.notifications.models import Notification
from app.scheduling.models import Job
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login

BASE = "/v1/admin/scheduling"


def _setup(api, admin, world, run_week, cars=3):
    crew_login = world.db.query(Login).filter_by(role="crew").first()
    member = world.add_crew(login_id=crew_login.id, end=600)
    for _ in range(cars):
        world.add_vehicle(cutoff=time(10, 0))
    world.db.commit()
    sid = run_week(days=1)["schedule_id"]
    api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin)
    crew = auth(login(api, "crew")["access_token"])
    return member, sid, crew


def _day(api, crew):
    r = api.get("/v1/crew/day", headers=crew, params={"date": SUNDAY.isoformat()})
    assert r.status_code == 200, r.text
    return r.json()["jobs"]


def test_planner_sets_a_sequence_in_start_order(api, admin, world, run_week):
    _, _, crew = _setup(api, admin, world, run_week)
    jobs = _day(api, crew)
    assert [j["sequence"] for j in jobs] == [1, 2, 3]
    starts = [j["start_time"] for j in jobs]
    assert starts == sorted(starts)


def test_day_marks_current_and_locked(api, admin, world, run_week):
    _, _, crew = _setup(api, admin, world, run_week)
    jobs = _day(api, crew)
    assert [(j["current"], j["locked"]) for j in jobs] == [
        (True, False), (False, True), (False, True)]


def test_locked_job_is_refused_on_every_crew_route(api, admin, world, run_week):
    _, _, crew = _setup(api, admin, world, run_week)
    second = _day(api, crew)[1]["id"]
    for path, body in (
        (f"/v1/crew/jobs/{second}/start", None),
        (f"/v1/crew/jobs/{second}/complete", None),
        (f"/v1/crew/jobs/{second}/could-not-complete",
         {"reason_key": "other", "note": "x"}),
    ):
        r = api.post(path, headers=crew, json=body) if body else api.post(path, headers=crew)
        assert r.status_code == 409 and r.json()["code"] == "queue_locked", r.text
        assert r.json()["message"].startswith("Finish MH12AB000")
    r = api.get("/v1/crew/visits", headers=crew, params={"date": SUNDAY.isoformat()})
    assert [(c["locked"], c["current"]) for c in r.json()["jobs"]][:2] == [
        (False, True), (True, False)]


def test_not_completed_unlocks_the_next_job(api, admin, world, run_week):
    _, _, crew = _setup(api, admin, world, run_week)
    jobs = _day(api, crew)
    assert api.post(f"/v1/crew/jobs/{jobs[0]['id']}/start", headers=crew).status_code == 200
    r = api.post(f"/v1/crew/jobs/{jobs[0]['id']}/could-not-complete", headers=crew,
                 json={"reason_key": "other", "note": "No car"})
    assert r.status_code == 200, r.text
    after = _day(api, crew)
    assert after[1]["current"] and not after[1]["locked"] and after[2]["locked"]
    assert api.post(f"/v1/crew/jobs/{jobs[1]['id']}/start", headers=crew).status_code == 200


def test_flag_off_nothing_locks(api, admin, world, run_week):
    _, _, crew = _setup(api, admin, world, run_week)
    admin_id = world.db.query(Login).filter_by(role="admin").first().id
    features.set_enabled(world.db, admin_id, "crew.sequential_queue", False)
    jobs = _day(api, crew)
    assert not any(j["locked"] for j in jobs)
    assert api.post(f"/v1/crew/jobs/{jobs[2]['id']}/start", headers=crew).status_code == 200


def test_unlock_needs_a_reason_and_allows_out_of_turn(api, admin, world, run_week):
    member, _, crew = _setup(api, admin, world, run_week)
    third = _day(api, crew)[2]["id"]
    for bad in ({"reason": "  "}, {}):
        assert api.post(f"{BASE}/jobs/{third}/unlock", headers=admin, json=bad
                        ).status_code == 422
    r = api.post(f"{BASE}/jobs/{third}/unlock", headers=admin, json={"reason": "Owner waiting"})
    assert r.status_code == 200, r.text
    assert not _day(api, crew)[2]["locked"]
    assert api.post(f"/v1/crew/jobs/{third}/start", headers=crew).status_code == 200
    row = world.db.scalar(select(DirectoryAudit).where(
        DirectoryAudit.entity == "queue", DirectoryAudit.action == "unlock"))
    assert row.detail["reason"] == "Owner waiting" and row.admin_login_id is not None
    note = world.db.scalar(select(Notification).where(
        Notification.event == "crew_queue_changed", Notification.login_id == member.login_id))
    assert note is not None and "Asha" not in note.body


def test_unlock_needs_admin(api, world, admin, run_week):
    _, _, crew = _setup(api, admin, world, run_week)
    third = _day(api, crew)[2]["id"]
    assert api.post(f"{BASE}/jobs/{third}/unlock", headers=crew,
                    json={"reason": "x"}).status_code == 403


def test_reorder_audits_notifies_and_changes_the_queue(api, admin, world, run_week):
    member, _, crew = _setup(api, admin, world, run_week)
    ids = [j["id"] for j in _day(api, crew)]
    new = [ids[2], ids[0], ids[1]]
    body = {"crew_id": str(member.id), "date": SUNDAY.isoformat(),
            "ordered_job_ids": new, "reason": "Customer asked"}
    assert api.post(f"{BASE}/queue/reorder", headers=admin,
                    json={**body, "reason": ""}).status_code == 422
    assert api.post(f"{BASE}/queue/reorder", headers=admin,
                    json={**body, "ordered_job_ids": new[:2]}).status_code == 422
    r = api.post(f"{BASE}/queue/reorder", headers=admin, json=body)
    assert r.status_code == 200, r.text
    jobs = _day(api, crew)
    assert [j["id"] for j in jobs] == new and jobs[0]["current"] and jobs[1]["locked"]
    row = world.db.scalar(select(DirectoryAudit).where(
        DirectoryAudit.entity == "queue", DirectoryAudit.action == "reorder"))
    assert row.detail["old_order"] == ids and row.detail["new_order"] == new
    assert row.detail["reason"] == "Customer asked"
    assert world.db.scalar(select(Notification).where(
        Notification.event == "crew_queue_changed")) is not None


def test_taking_a_job_off_keeps_the_sequence_consistent(api, admin, world, run_week):
    _, _, crew = _setup(api, admin, world, run_week)
    jobs = _day(api, crew)
    r = api.post(f"{BASE}/jobs/{jobs[1]['id']}/move", headers=admin, json={"crew_id": None})
    assert r.status_code == 200
    assert [j["sequence"] for j in _day(api, crew)] == [1, 2]
    world.db.expire_all()
    assert world.db.get(Job, uuid.UUID(jobs[1]["id"])).sequence is None


def test_moving_a_job_to_another_crew_member_renumbers_both(api, admin, world, run_week):
    member, sid, crew = _setup(api, admin, world, run_week)
    other = world.add_crew(end=600, name="Sita")
    world.db.commit()
    jobs = _day(api, crew)
    r = api.post(f"{BASE}/schedules/{sid}/unfreeze", headers=admin, json={"code": "unfreeze"})
    assert r.status_code == 200, r.text
    r = api.post(f"{BASE}/jobs/{jobs[0]['id']}/move", headers=admin,
                 json={"crew_id": str(other.id), "start_minute": 400})
    assert r.status_code == 200, r.text
    world.db.expire_all()
    moved = world.db.get(Job, uuid.UUID(jobs[0]["id"]))
    assert moved.crew_id == other.id and moved.sequence == 1
    rest = [world.db.get(Job, uuid.UUID(j["id"])).sequence for j in jobs[1:]]
    assert rest == [1, 2]
