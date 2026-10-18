"""The crew directory and the scheduler are one record: onboarding, weekday
hours, exceptions, pairing, role change, deactivation and sessions
(ADM-CRW-03, -05, -08 to -15, -19, -21, CRW-ACC-08, -11, CRW-SCH-01, -10)."""
import uuid
from datetime import date, time, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
from app.platform.clock import today_ist
from app.scheduling import rules, service
from app.scheduling.models import Job, SchedulingCrew, SchedulingCrewException
from tests.test_api import auth

CREW = "/v1/admin/crew"
SCHED = "/v1/admin/scheduling"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def hours(start="06:00", end="11:00", off=()):
    return [{"day": d, "working": d not in off, "start": "" if d in off else start,
             "end": "" if d in off else end} for d in DAYS]


@pytest.fixture
def directory(api, admin, world):
    """Helpers that onboard crew through the API, in the world's society."""
    n = {"i": 0}

    def make(role="Member", name="Ravi Kumar", paired=None, working=None):
        n["i"] += 1
        body = {"name": name, "mobile": f"98000{n['i']:05d}", "role": role,
                "society_id": str(world.society.id),
                "working_hours": working or hours()}
        if paired:
            body["paired_member_id"] = paired
        r = api.post(CREW, headers=admin, json=body)
        assert r.status_code == 201, r.text
        return r.json()

    return make


def sc_of(db: Session, crew_id: str) -> SchedulingCrew:
    db.expire_all()
    member = db.get(CrewMember, uuid.UUID(crew_id))
    return db.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == member.login_id))


def run_and_freeze(api, admin, world, days=3):
    start = today_ist() + timedelta(days=1)
    r = api.post(f"{SCHED}/run", headers=admin, json={
        "society_id": str(world.society.id), "start_date": start.isoformat(), "days": days})
    assert r.status_code == 200, r.text
    schedule_id = r.json()["schedules"][0]["schedule_id"]
    f = api.post(f"{SCHED}/schedules/{schedule_id}/freeze", headers=admin)
    assert f.status_code == 200, f.text
    return start, schedule_id


def needs(api, admin, world):
    r = api.get(f"{SCHED}/needs-scheduling", headers=admin,
                params={"society_id": str(world.society.id)})
    return r.json()["jobs"]


def sign_in(api, created):
    return api.post("/v1/auth/login", json={"login_id": created["login_id"],
                                            "password": created["password"]})


def test_an_onboarded_crew_member_gets_jobs(api, admin, world, directory):
    created = directory()
    sc = sc_of(world.db, created["crew"]["id"])
    assert sc is not None and sc.role == "Member" and sc.active
    assert sc.society_id == world.society.id and sc.working_hours[0]["start"] == "06:00"
    assert (sc.start_minute, sc.end_minute) == (360, 660)

    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    start, _ = run_and_freeze(api, admin, world, days=1)
    jobs = world.db.scalars(select(Job).where(Job.crew_id == sc.id)).all()
    assert len(jobs) == 1 and jobs[0].start_minute is not None

    token = sign_in(api, created).json()["access_token"]
    r = api.get("/v1/crew/visits", headers=auth(token), params={"date": start.isoformat()})
    assert r.status_code == 200, r.text
    assert len(r.json()["jobs"]) == 1


def test_weekday_hours_and_exceptions_shape_the_window(world):
    crew = world.add_crew()
    crew.working_hours = hours("07:00", "09:00", off=("Tuesday",))
    world.db.flush()
    monday, tuesday = date(2026, 10, 12), date(2026, 10, 13)
    assert monday.weekday() == 0
    out = service.availability(world.db, {crew.id: crew}, [monday, tuesday])
    assert out[monday][crew.id] == [(420, 540)]
    assert crew.id not in out[tuesday]

    world.db.add(SchedulingCrewException(crew_id=crew.id, on_date=monday, kind="Late start",
                                         from_minute=480))
    world.db.flush()
    assert service.availability(world.db, {crew.id: crew}, [monday])[monday][crew.id] == [
        (480, 540)]
    world.db.add(SchedulingCrewException(crew_id=crew.id, on_date=date(2026, 10, 14),
                                         kind="Leave"))
    world.db.flush()
    wednesday = date(2026, 10, 14)
    assert crew.id not in service.availability(world.db, {crew.id: crew}, [wednesday])[wednesday]


def test_the_single_window_still_applies_without_weekday_hours():
    assert rules.hours_window(None, 3, 360, 420) == (360, 420)
    assert rules.hours_window([], 3, 360, 420) == (360, 420)
    assert rules.hours_window([{"working": False}] * 7, 3, 360, 420) is None


def test_a_day_off_in_new_hours_sends_open_jobs_to_needs_scheduling(
        api, admin, world, directory):
    created = directory()
    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    start, _ = run_and_freeze(api, admin, world, days=1)
    assert needs(api, admin, world) == []

    day = DAYS[start.weekday()]
    r = api.put(f"{CREW}/{created['crew']['id']}/working-hours", headers=admin,
                json={"working_hours": hours(off=(day,))})
    assert r.status_code == 200, r.text
    assert len(r.json()["released_jobs"]) == 1
    assert len(needs(api, admin, world)) == 1


def test_an_exception_releases_jobs_and_can_be_edited_and_removed(
        api, admin, world, directory):
    created = directory()
    crew_id = created["crew"]["id"]
    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    start, _ = run_and_freeze(api, admin, world, days=1)

    r = api.post(f"{CREW}/{crew_id}/exceptions", headers=admin,
                 json={"kind": "Sick", "from_date": start.isoformat()})
    assert r.status_code == 201, r.text
    body = r.json()
    assert [e["kind"] for e in body["exceptions"]] == ["Sick"]
    assert len(body["released_jobs"]) == 1
    assert len(needs(api, admin, world)) == 1
    ex_id = body["exceptions"][0]["id"]

    again = api.post(f"{CREW}/{crew_id}/exceptions", headers=admin,
                     json={"kind": "Leave", "from_date": start.isoformat()})
    assert again.status_code == 409

    edited = api.patch(f"{CREW}/{crew_id}/exceptions/{ex_id}", headers=admin,
                       json={"kind": "Late start", "start": "08:00"})
    assert edited.status_code == 200
    assert edited.json()["exceptions"][0]["start"] == "08:00"
    needs_start = api.patch(f"{CREW}/{crew_id}/exceptions/{ex_id}", headers=admin,
                            json={"kind": "Late start", "start": ""})
    assert needs_start.status_code == 422

    removed = api.delete(f"{CREW}/{crew_id}/exceptions/{ex_id}", headers=admin)
    assert removed.status_code == 200 and removed.json()["exceptions"] == []
    listed = api.get(f"{CREW}/{crew_id}", headers=admin).json()
    assert listed["exceptions"] == []


def test_a_range_of_exceptions_and_past_dates(api, admin, directory):
    crew_id = directory()["crew"]["id"]
    today = today_ist()
    r = api.post(f"{CREW}/{crew_id}/exceptions", headers=admin, json={
        "kind": "Leave", "from_date": (today + timedelta(days=2)).isoformat(),
        "to_date": (today + timedelta(days=4)).isoformat()})
    assert r.status_code == 201 and len(r.json()["exceptions"]) == 3
    assert [e["kind"] for e in api.get(f"{CREW}/{crew_id}", headers=admin
                                       ).json()["exceptions"]] == ["Leave"] * 3
    past = api.post(f"{CREW}/{crew_id}/exceptions", headers=admin, json={
        "kind": "Sick", "from_date": (today - timedelta(days=1)).isoformat()})
    assert past.status_code == 422


def test_a_deactivated_crew_member_is_not_scheduled_and_cannot_sign_in(
        api, admin, world, directory):
    created = directory()
    crew_id = created["crew"]["id"]
    token = sign_in(api, created).json()["access_token"]
    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    run_and_freeze(api, admin, world, days=1)

    refused = api.post(f"{CREW}/{crew_id}/deactivate", headers=admin, json={})
    assert refused.status_code == 409 and refused.json()["code"] == "has_open_jobs"

    r = api.post(f"{CREW}/{crew_id}/deactivate", headers=admin,
                 json={"release_jobs": True})
    assert r.status_code == 200, r.text
    assert r.json()["crew"]["active"] is False and len(r.json()["released_jobs"]) == 1
    assert len(needs(api, admin, world)) == 1
    assert sc_of(world.db, crew_id).active is False

    assert sign_in(api, created).status_code in (401, 403)
    assert api.get("/v1/crew/profile", headers=auth(token)).status_code == 401

    # A re-run does not give the job back to them.
    start = today_ist() + timedelta(days=1)
    api.post(f"{SCHED}/run", headers=admin, json={
        "society_id": str(world.society.id), "start_date": start.isoformat(), "days": 1})
    assert len(needs(api, admin, world)) == 1

    back = api.post(f"{CREW}/{crew_id}/reactivate", headers=admin)
    assert back.status_code == 200 and back.json()["active"] is True
    assert sc_of(world.db, crew_id).active is True
    assert sign_in(api, created).status_code == 200


def test_a_job_in_progress_stops_deactivation(api, admin, world, directory):
    created = directory()
    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    run_and_freeze(api, admin, world, days=1)
    mine = sc_of(world.db, created["crew"]["id"])
    job = world.db.scalars(select(Job).where(Job.crew_id == mine.id)).one()
    job.status = "In progress"
    world.db.commit()
    r = api.post(f"{CREW}/{created['crew']['id']}/deactivate", headers=admin,
                 json={"release_jobs": True})
    assert r.status_code == 409 and r.json()["code"] == "job_in_progress"


def test_a_trainee_is_paired_with_a_member_and_gets_their_jobs(
        api, admin, world, directory):
    member = directory()
    no_pair = api.post(CREW, headers=admin, json={
        "name": "Asha", "mobile": "9811111111", "role": "Trainee",
        "society_id": str(world.society.id), "working_hours": hours()})
    assert no_pair.status_code == 422

    trainee = directory(role="Trainee", name="Asha Rao", paired=member["crew"]["id"])
    assert trainee["crew"]["paired_member_id"] == member["crew"]["id"]
    assert trainee["crew"]["paired_member"] == "Ravi Kumar"
    assert sc_of(world.db, trainee["crew"]["id"]).paired_member_id == sc_of(
        world.db, member["crew"]["id"]).id

    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    start, _ = run_and_freeze(api, admin, world, days=1)
    token = sign_in(api, trainee).json()["access_token"]
    r = api.get("/v1/crew/visits", headers=auth(token), params={"date": start.isoformat()})
    assert r.status_code == 200 and len(r.json()["jobs"]) == 1

    # The Member's role is fixed while a Trainee is paired (ADM-CRW-19).
    blocked = api.put(f"{CREW}/{member['crew']['id']}/role", headers=admin,
                      json={"role": "Manager"})
    assert blocked.status_code == 409 and blocked.json()["code"] == "trainees_paired"
    gone = api.post(f"{CREW}/{member['crew']['id']}/deactivate", headers=admin,
                    json={"release_jobs": True})
    assert gone.status_code == 409 and gone.json()["code"] == "trainees_paired"

    other = directory(name="Sunil Das")
    moved = api.put(f"{CREW}/{trainee['crew']['id']}/pair", headers=admin,
                    json={"paired_member_id": other["crew"]["id"]})
    assert moved.status_code == 200
    assert moved.json()["paired_member"] == "Sunil Das"
    ok = api.put(f"{CREW}/{member['crew']['id']}/role", headers=admin,
                 json={"role": "Manager"})
    assert ok.status_code == 200 and ok.json()["crew"]["role"] == "Manager"
    assert sc_of(world.db, member["crew"]["id"]).role == "Manager"


def test_pairing_rules(api, admin, world, directory):
    member = directory()
    manager = directory(role="Manager", name="Mona Das")
    trainee = directory(role="Trainee", name="Asha Rao", paired=member["crew"]["id"])
    tid = trainee["crew"]["id"]
    # Only a Member can be paired with, and only a Trainee is paired.
    assert api.put(f"{CREW}/{tid}/pair", headers=admin,
                   json={"paired_member_id": manager["crew"]["id"]}).status_code == 422
    assert api.put(f"{CREW}/{member['crew']['id']}/pair", headers=admin,
                   json={"paired_member_id": member["crew"]["id"]}).status_code == 409
    # A Member becomes a Trainee only with a Member to pair with.
    other = directory(name="Sunil Das")
    oid = other["crew"]["id"]
    assert api.put(f"{CREW}/{oid}/role", headers=admin,
                   json={"role": "Trainee"}).status_code == 422
    r = api.put(f"{CREW}/{oid}/role", headers=admin,
                json={"role": "Trainee", "paired_member_id": member["crew"]["id"]})
    assert r.status_code == 200 and r.json()["crew"]["paired_member"] == "Ravi Kumar"
    # And back: the pairing is cleared.
    back = api.put(f"{CREW}/{oid}/role", headers=admin, json={"role": "Member"})
    assert back.status_code == 200 and back.json()["crew"]["paired_member_id"] is None


def test_a_member_made_trainee_loses_open_jobs(api, admin, world, directory):
    keep = directory()
    mate = directory(name="Sunil Das")
    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    run_and_freeze(api, admin, world, days=1)
    holder = world.db.scalars(select(Job)).one().crew_id
    holder_crew = keep if sc_of(world.db, keep["crew"]["id"]).id == holder else mate
    other = mate if holder_crew is keep else keep
    r = api.put(f"{CREW}/{holder_crew['crew']['id']}/role", headers=admin,
                json={"role": "Trainee", "paired_member_id": other["crew"]["id"]})
    assert r.status_code == 200, r.text
    assert len(r.json()["released_jobs"]) == 1
    assert len(needs(api, admin, world)) == 1


def test_edit_details_and_login_id(api, admin, directory):
    created = directory()
    crew_id = created["crew"]["id"]
    token_resp = sign_in(api, created)
    assert token_resp.status_code == 200
    r = api.patch(f"{CREW}/{crew_id}", headers=admin,
                  json={"name": "Ravi K", "mobile": "9899999999"})
    assert r.status_code == 200 and r.json()["mobile"] == "9899999999"
    # The old login ID is gone, the signed-in phone is out.
    assert api.post("/v1/auth/login", json={
        "login_id": created["login_id"], "password": created["password"]}).status_code == 401
    assert api.post("/v1/auth/login", json={
        "login_id": "9899999999", "password": created["password"]}).status_code == 200
    taken = api.patch(f"{CREW}/{crew_id}", headers=admin, json={"mobile": "9000000002"})
    assert taken.status_code == 409


def test_admin_lists_and_ends_a_crew_members_sessions(api, admin, directory):
    created = directory()
    crew_id = created["crew"]["id"]
    first = sign_in(api, created).json()
    sign_in(api, created)
    listed = api.get(f"{CREW}/{crew_id}/sessions", headers=admin)
    assert listed.status_code == 200 and len(listed.json()) == 2

    one = api.post(f"{CREW}/{crew_id}/sessions/{listed.json()[0]['id']}/logout",
                   headers=admin)
    assert one.status_code == 200 and one.json()["ended"] == 1
    assert len(api.get(f"{CREW}/{crew_id}/sessions", headers=admin).json()) == 1

    allgone = api.post(f"{CREW}/{crew_id}/sessions/logout", headers=admin)
    assert allgone.json()["ended"] == 1
    assert api.get(f"{CREW}/{crew_id}/sessions", headers=admin).json() == []
    assert api.get("/v1/crew/profile",
                   headers=auth(first["access_token"])).status_code == 401


def test_only_the_admin_changes_crew(api, directory):
    from tests.test_api import login
    nobody = "00000000-0000-0000-0000-000000000000"
    for role in ("crew", "customer"):
        token = login(api, role)["access_token"]
        for method, path, body in (
            ("patch", f"{CREW}/{nobody}", {}),
            ("put", f"{CREW}/{nobody}/role", {"role": "Member"}),
            ("post", f"{CREW}/{nobody}/deactivate", {}),
            ("post", f"{CREW}/{nobody}/sessions/logout", {}),
        ):
            assert getattr(api, method)(path, headers=auth(token), json=body).status_code == 403
