from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import AddonRequest
from app.identity.models import Login
from app.platform.clock import IST
from app.scheduling import service
from app.scheduling.models import Job, Schedule, SchedulingCrewException, Visit
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login

BASE = "/v1/admin/scheduling"


def board(api, admin, schedule_id):
    r = api.get(f"{BASE}/board", headers=admin, params={"schedule_id": schedule_id})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_run_makes_a_draft_and_respects_capacity(api, admin, world, run_week):
    # Two crew members with 60 minutes each fit six 20-minute cleans a day.
    world.add_crew()
    world.add_crew()
    for _ in range(8):
        world.add_vehicle(cutoff=time(8, 0))
    world.db.commit()

    summary = run_week(days=1)
    assert summary["status"] == "Draft"
    assert summary["placed"] == 6 and summary["unscheduled"] == 2

    b = board(api, admin, summary["schedule_id"])
    assert b["days"][0]["capacity_minutes"] == 120
    assert b["days"][0]["demand_minutes"] == 160 and b["days"][0]["over_capacity"]
    placed = [j for j in b["jobs"] if j["crew_id"]]
    for crew_id in {j["crew_id"] for j in placed}:
        spans = sorted((j["start_minute"], j["start_minute"] + j["duration_minutes"])
                       for j in placed if j["crew_id"] == crew_id)
        assert spans[0][0] >= 360 and spans[-1][1] <= 420
        assert all(a[1] <= b_[0] for a, b_ in zip(spans, spans[1:], strict=False))

    r = api.get(f"{BASE}/needs-scheduling", headers=admin,
                params={"society_id": str(world.society.id)})
    assert len(r.json()["jobs"]) == 2
    assert all(j["reason"] for j in r.json()["jobs"])


def test_a_manual_change_survives_a_rerun(api, admin, world, run_week):
    a = world.add_crew(end=480)
    world.add_crew(end=480)
    for _ in range(4):
        world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    first = run_week(days=1)
    jobs = board(api, admin, first["schedule_id"])["jobs"]
    target = jobs[-1]

    r = api.post(f"{BASE}/jobs/{target['id']}/move", headers=admin,
                 json={"crew_id": str(a.id), "start_minute": 450})
    assert r.status_code == 200, r.text
    assert r.json()["manual"] and r.json()["start_time"] == "07:30"

    second = run_week(days=1)
    assert second["schedule_id"] == first["schedule_id"]
    after = {j["id"]: j for j in board(api, admin, second["schedule_id"])["jobs"]}
    assert after[target["id"]]["crew_id"] == str(a.id)
    assert after[target["id"]]["start_minute"] == 450
    assert len(after) == 4 and all(j["crew_id"] for j in after.values())


def test_taking_a_job_off_is_kept_on_a_rerun(api, admin, world, run_week):
    world.add_crew(end=480)
    world.add_vehicle()
    world.db.commit()
    first = run_week(days=1)
    job = board(api, admin, first["schedule_id"])["jobs"][0]
    r = api.post(f"{BASE}/jobs/{job['id']}/move", headers=admin, json={"crew_id": None})
    assert r.status_code == 200 and r.json()["crew_id"] is None

    again = run_week(days=1)
    assert again["placed"] == 0 and again["unscheduled"] == 1


def test_a_move_that_overlaps_or_leaves_the_hours_is_refused(api, admin, world, run_week):
    a = world.add_crew(end=480)
    world.add_vehicle()
    world.add_vehicle()
    world.db.commit()
    first = run_week(days=1)
    jobs = board(api, admin, first["schedule_id"])["jobs"]
    one, two = jobs[0], jobs[1]
    r = api.post(f"{BASE}/jobs/{two['id']}/move", headers=admin,
                 json={"crew_id": str(a.id), "start_minute": one["start_minute"] + 10})
    assert r.status_code == 409 and r.json()["code"] == "overlap"
    r = api.post(f"{BASE}/jobs/{two['id']}/move", headers=admin,
                 json={"crew_id": str(a.id), "start_minute": 470})
    assert r.status_code == 409 and r.json()["code"] == "outside_hours"


def test_interior_day_and_deep_spa_are_jobs_of_their_own(api, admin, world, run_week):
    world.add_crew(end=600)
    car = world.add_vehicle(cutoff=time(9, 0), interior_day="Wednesday")
    world.db.add(AddonRequest(customer_id=world.customer.id, vehicle_id=car.id,
                              service="Deep Spa", service_date=date(2026, 10, 20)))
    world.db.commit()
    summary = run_week()
    jobs = board(api, admin, summary["schedule_id"])["jobs"]
    by_day = {}
    for j in jobs:
        by_day.setdefault(j["date"], []).append(j["service"])
    assert len(jobs) == 7 + 1 + 1
    assert sorted(by_day["2026-10-21"]) == ["Cleaning-External", "Cleaning-Internal"]
    assert sorted(by_day["2026-10-20"]) == ["Cleaning-External", "Deep Spa"]
    spa = next(j for j in jobs if j["service"] == "Deep Spa")
    assert spa["duration_minutes"] == 120 and spa["crew_id"]


def test_inactive_and_trainee_do_not_count(api, admin, world, run_week):
    world.add_crew(end=480)
    world.add_crew(role="Trainee", end=480)
    world.add_vehicle()
    world.add_vehicle(status="Inactive")
    world.db.commit()
    summary = run_week(days=1)
    b = board(api, admin, summary["schedule_id"])
    assert len(b["jobs"]) == 1
    assert b["days"][0]["capacity_minutes"] == 120


def test_a_crew_exception_removes_that_days_capacity(api, admin, world, run_week):
    crew = world.add_crew(end=480)
    world.add_vehicle()
    world.db.add(SchedulingCrewException(crew_id=crew.id, on_date=SUNDAY, kind="Sick"))
    world.db.commit()
    summary = run_week(days=1)
    assert summary["placed"] == 0 and summary["unscheduled"] == 1


def test_freeze_and_unfreeze_with_the_code(api, admin, world, run_week):
    a = world.add_crew(end=480)
    world.add_vehicle()
    world.db.commit()
    summary = run_week(days=1)
    sid = summary["schedule_id"]
    job = board(api, admin, sid)["jobs"][0]

    r = api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "Frozen"
    assert r.json()["freeze_deadline"].startswith("2026-10-17T20:00:00+05:30")
    assert api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin).status_code == 409

    # Adding or moving work needs the code (ADM-SCH-17).
    r = api.post(f"{BASE}/jobs/{job['id']}/move", headers=admin,
                 json={"crew_id": str(a.id), "start_minute": 400})
    assert r.status_code == 409 and r.json()["code"] == "schedule_frozen"

    r = api.post(f"{BASE}/schedules/{sid}/unfreeze", headers=admin, json={"code": "nope"})
    assert r.status_code == 403 and r.json()["code"] == "wrong_code"
    assert board(api, admin, sid)["schedule"]["status"] == "Frozen"

    r = api.post(f"{BASE}/schedules/{sid}/unfreeze", headers=admin, json={"code": "unfreeze"})
    assert r.status_code == 200 and r.json()["status"] == "Draft"
    r = api.post(f"{BASE}/jobs/{job['id']}/move", headers=admin,
                 json={"crew_id": str(a.id), "start_minute": 400})
    assert r.status_code == 200


def test_removing_from_a_frozen_schedule_needs_no_code(api, admin, world, run_week):
    world.add_crew(end=480)
    world.add_vehicle()
    world.db.commit()
    sid = run_week(days=1)["schedule_id"]
    api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin)
    job = board(api, admin, sid)["jobs"][0]
    r = api.post(f"{BASE}/jobs/{job['id']}/move", headers=admin, json={"crew_id": None})
    assert r.status_code == 200 and r.json()["crew_id"] is None
    needs = api.get(f"{BASE}/needs-scheduling", headers=admin).json()["jobs"]
    assert [j["id"] for j in needs] == [job["id"]]
    assert needs[0]["schedule_status"] == "Frozen"


def test_a_late_visit_is_placed_on_a_frozen_schedule_without_moving_others(
        api, admin, world, run_week):
    world.add_crew(end=480)
    world.add_vehicle()
    world.db.commit()
    sid = run_week(days=1)["schedule_id"]
    before = {j["id"]: (j["crew_id"], j["start_minute"])
              for j in board(api, admin, sid)["jobs"]}
    api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin)

    world.add_vehicle()  # a new customer vehicle after the freeze (ADM-SCH-27)
    world.db.commit()
    summary = run_week(days=1)
    assert summary["status"] == "Frozen" and summary["placed"] == 2
    after = {j["id"]: (j["crew_id"], j["start_minute"])
             for j in board(api, admin, sid)["jobs"]}
    for job_id, placement in before.items():
        assert after[job_id] == placement


def test_the_freeze_cutoff_time_freezes_drafts(api, admin, world, run_week, engine):
    world.add_crew()
    world.add_vehicle()
    world.db.commit()
    run_week(days=1)
    with Session(engine) as db:
        early = datetime(2026, 10, 17, 19, 59, tzinfo=IST)
        assert service.freeze_due(db, early) == []
        ids = service.freeze_due(db, datetime(2026, 10, 17, 20, 0, tzinfo=IST))
        assert len(ids) == 1
        assert db.get(Schedule, ids[0]).status == "Frozen"


def test_the_crew_day_shows_only_frozen_work_and_no_customer_details(
        api, world, admin, run_week):
    crew_login = db_login(world, "crew")
    world.add_crew(login_id=crew_login.id, end=480)
    world.add_vehicle(cutoff=time(8, 0))
    world.db.commit()
    sid = run_week(days=1)["schedule_id"]
    crew = auth(login(api, "crew")["access_token"])

    r = api.get("/v1/crew/day", headers=crew, params={"date": SUNDAY.isoformat()})
    assert r.status_code == 200 and r.json()["jobs"] == []  # still a draft (CRW-SCH-11)

    api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin)
    r = api.get("/v1/crew/day", headers=crew, params={"date": SUNDAY.isoformat()})
    day = r.json()
    assert day["total"] == 1 and day["left"] == 1 and day["society"] == "DLF Meadows"
    card = day["jobs"][0]
    assert card["service"] == "Cleaning-External" and card["status"] == "Scheduled"
    assert card["registration"] == "MH12AB0001" and card["start_time"] == "06:00"
    assert card["end_time"] == "06:20" and card["finish_by"] == "08:00"
    text = r.text
    assert "Asha" not in text and "9876543210" not in text and "customer" not in text


def test_a_trainee_sees_the_paired_members_jobs(api, world, admin, run_week):
    member = world.add_crew(end=480)
    crew_login = db_login(world, "crew")
    world.add_crew(login_id=crew_login.id, role="Trainee", paired=member.id, end=480)
    world.add_vehicle()
    world.db.commit()
    sid = run_week(days=1)["schedule_id"]
    api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin)
    crew = auth(login(api, "crew")["access_token"])
    r = api.get("/v1/crew/day", headers=crew, params={"date": SUNDAY.isoformat()})
    assert r.json()["total"] == 1


def test_next_service_for_the_customer(api, world, admin, run_week):
    world.add_crew(end=480, name="Ravi Kumar")
    world.add_vehicle(cutoff=time(9, 30))
    world.db.commit()
    sid = run_week(days=2)["schedule_id"]
    cust = auth(login(api, "customer")["access_token"])
    params = {"from_date": SUNDAY.isoformat()}

    r = api.get("/v1/customer/next-job", headers=cust, params=params)
    assert r.status_code == 200 and r.json() == {"job": None}  # a draft is not shown

    api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin)
    job = api.get("/v1/customer/next-job", headers=cust, params=params).json()["job"]
    assert job["date"] == "2026-10-18" and job["service"] == "Cleaning-External"
    assert job["status"] == "Scheduled" and job["crew_name"] == "Ravi Kumar"
    assert job["start_time"] == "06:00" and job["finish_by"] == "09:30"
    assert set(job) == {"job_id", "visit_id", "vehicle_id", "registration", "vehicle", "date",
                        "service", "status", "start_time", "end_time", "crew_name",
                        "finish_by"}

    later = api.get("/v1/customer/next-job", headers=cust,
                    params={"from_date": "2026-10-19"}).json()["job"]
    assert later["date"] == "2026-10-19"


def test_a_visit_completes_only_when_all_its_jobs_are_done(api, world, admin, run_week, engine):
    world.add_crew(end=480)
    world.add_vehicle(interior_day="Sunday")
    world.db.commit()
    run_week(days=1)
    with Session(engine) as db:
        jobs = db.execute(select(Job)).scalars().all()
        assert len(jobs) == 2
        visit_id = jobs[0].visit_id
        service.set_job_status(db, jobs[0].id, "Completed")
        assert db.get(Visit, visit_id).status == "In progress"
        service.set_job_status(db, jobs[1].id, "Skipped")
        assert db.get(Visit, visit_id).status == "Completed"


def test_scheduling_endpoints_are_for_their_role(api, admin, world):
    cust = auth(login(api, "customer")["access_token"])
    r = api.post(f"{BASE}/run", headers=cust, json={"start_date": "2026-10-18"})
    assert r.status_code == 403
    assert api.get("/v1/crew/day", params={"date": "2026-10-18"}).status_code == 401
    assert api.get("/v1/customer/next-job", headers=admin).status_code == 403


def db_login(world, role):
    return world.db.execute(select(Login).where(Login.role == role)).scalars().first()
