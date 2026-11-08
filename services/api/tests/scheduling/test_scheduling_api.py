from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import AddonRequest
from app.directory import lookup
from app.directory.models import DirectoryService
from app.directory.seed import seed_defaults
from app.identity.models import Login
from app.platform.clock import IST
from app.scheduling import service
from app.scheduling.models import Job, Schedule, SchedulingCrewException, Visit
from tests.directory_helpers import set_feature, set_setting
from tests.scheduling.conftest import SUNDAY, run_day, run_days
from tests.test_api import auth, login

BASE = "/v1/admin/scheduling"


def pin_cleaning_to_20(world):
    """These tests are about capacity and times, not the default length."""
    seed_defaults(world.db)
    world.db.query(DirectoryService).filter(
        DirectoryService.name.in_(("Cleaning-External", "Cleaning-Internal"))
    ).update({"duration_minutes": 20})
    world.db.flush()
    lookup.invalidate()


def board(api, admin, schedule_id):
    r = api.get(f"{BASE}/board", headers=admin, params={"schedule_id": schedule_id})
    assert r.status_code == 200, r.text
    return r.json()


def test_a_run_makes_a_draft_and_respects_capacity(api, admin, world, run_week):
    pin_cleaning_to_20(world)
    # Two crew members with 60 minutes each fit six 20-minute cleans a day.
    world.add_crew()
    world.add_crew()
    for _ in range(8):
        world.add_vehicle(cutoff=time(8, 0))
    world.db.commit()

    summary = run_week(days=1)
    assert summary["status"] == "Draft"
    # Each car also owes an Interior (SCHS-36): 16 jobs, six fit.
    assert summary["placed"] == 6 and summary["unscheduled"] == 10

    b = board(api, admin, summary["schedule_id"])
    assert b["days"][0]["capacity_minutes"] == 120
    assert b["days"][0]["demand_minutes"] == 160 and b["days"][0]["over_capacity"]
    placed = [j for j in b["jobs"] if j["crew_id"]]
    assert all("parking" in j for j in b["jobs"])  # the Gantt card shows it (ADM-SCH-33)
    for crew_id in {j["crew_id"] for j in placed}:
        spans = sorted((j["start_minute"], j["start_minute"] + j["duration_minutes"])
                       for j in placed if j["crew_id"] == crew_id)
        assert spans[0][0] >= 360 and spans[-1][1] <= 420
        assert all(a[1] <= b_[0] for a, b_ in zip(spans, spans[1:], strict=False))

    r = api.get(f"{BASE}/needs-scheduling", headers=admin,
                params={"society_id": str(world.society.id)})
    assert len(r.json()["jobs"]) == 10  # the Exteriors and the Interiors that did not fit
    assert all(j["reason"] for j in r.json()["jobs"])


def test_a_manual_change_survives_a_rerun(api, admin, world, run_week):
    a = world.add_crew(end=720)  # room for the Interiors as well as the Exteriors
    world.add_crew(end=720)
    for _ in range(4):
        world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    first = run_week(days=1)
    jobs = board(api, admin, first["schedule_id"])["jobs"]
    target = jobs[-1]

    r = api.post(f"{BASE}/jobs/{target['id']}/move", headers=admin,
                 json={"crew_id": str(a.id), "start_minute": 540})
    assert r.status_code == 200, r.text
    assert r.json()["manual"] and r.json()["start_time"] == "09:00"

    second = run_week(days=1)
    assert second["schedule_id"] == first["schedule_id"]
    after = {j["id"]: j for j in board(api, admin, second["schedule_id"])["jobs"]}
    assert after[target["id"]]["crew_id"] == str(a.id)
    assert after[target["id"]]["start_minute"] == 540
    assert len(after) == 8 and all(j["crew_id"] for j in after.values())  # 4 cars, Exterior and Interior


def test_taking_a_job_off_is_kept_on_a_rerun(api, admin, world, run_week):
    world.add_crew(end=480)
    world.add_vehicle()
    world.db.commit()
    first = run_week(days=1)
    job = board(api, admin, first["schedule_id"])["jobs"][0]
    r = api.post(f"{BASE}/jobs/{job['id']}/move", headers=admin, json={"crew_id": None})
    assert r.status_code == 200 and r.json()["crew_id"] is None

    again = run_week(days=1)
    # The Interior is planned again; the Exterior taken off by hand stays off.
    assert again["placed"] == 1 and again["unscheduled"] == 1


def test_a_move_that_overlaps_or_leaves_the_hours_is_refused(api, admin, world, run_week):
    a = world.add_crew(end=480)
    world.add_vehicle()
    world.add_vehicle()
    world.db.commit()
    first = run_week(days=1)
    jobs = [j for j in board(api, admin, first["schedule_id"])["jobs"] if j["service"] == "Cleaning-External"]
    one, two = jobs[0], jobs[1]
    r = api.post(f"{BASE}/jobs/{two['id']}/move", headers=admin,
                 json={"crew_id": str(a.id), "start_minute": one["start_minute"] + 10})
    assert r.status_code == 409 and r.json()["code"] == "overlap"
    r = api.post(f"{BASE}/jobs/{two['id']}/move", headers=admin,
                 json={"crew_id": str(a.id), "start_minute": 480})  # the shift ends at 480
    # On the Board a breach is a warning first (SCHS-22): the code is placement_warning.
    assert r.status_code == 409 and r.json()["code"] == "placement_warning" and "outside_hours" in r.text


def test_interior_day_and_deep_spa_are_jobs_of_their_own(api, admin, world):
    world.add_crew(end=600)
    car = world.add_vehicle(cutoff=time(9, 0), interior_day="Wednesday")
    world.db.add(AddonRequest(customer_id=world.customer.id, vehicle_id=car.id,
                              service="Deep Spa", service_date=date(2026, 10, 20)))
    world.db.commit()
    days = run_days(api, admin, world.society.id, SUNDAY)  # a week, one daily run at a time
    jobs = [j for d in days for j in board(api, admin, d["schedule_id"])["jobs"]]
    by_day = {}
    for j in jobs:
        by_day.setdefault(j["date"], []).append(j["service"])
    assert len(jobs) == 7 + 2 + 1  # the Interiors are ledger demand (SCHS-36), not only the weekday
    # Daily runs (ADM-SCH-09): each Interior is planned on the first run day with room, not on the
    # car's preferred Wednesday (SCHR-INT-05). The Sunday and Monday runs each take one.
    assert sorted(by_day["2026-10-18"]) == ["Cleaning-External", "Cleaning-Internal"]
    assert sorted(by_day["2026-10-19"]) == ["Cleaning-External", "Cleaning-Internal"]
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
    assert len(b["jobs"]) == 2  # the car's Exterior and Interior
    assert b["days"][0]["capacity_minutes"] == 120


def test_capacity_days_break_down_crew_hours_and_demand(api, admin, world, run_week):
    pin_cleaning_to_20(world)
    # The Capacity page shows these lines on hover (ADM-CAP-01).
    world.add_crew()
    world.add_crew()
    for _ in range(3):
        world.add_vehicle(cutoff=time(8, 0))
    world.db.commit()
    day = board(api, admin, run_week(days=1)["schedule_id"])["days"][0]
    r = api.get(f"{BASE}/capacity", headers=admin, params={
        "society_id": str(world.society.id), "start_date": SUNDAY.isoformat(), "days": 1})
    assert r.status_code == 200, r.text
    row = r.json()[0]
    assert row["capacity_minutes"] == day["capacity_minutes"] == 120
    assert sum(c["minutes"] for c in row["crew"]) == 120 and len(row["crew"]) == 2
    assert all(c["name"] and c["slots"] and c["role"] == "Member" for c in row["crew"])
    assert sum(d["minutes"] for d in row["demand"]) == row["demand_minutes"] == 60
    assert all(d["source"] == "Subscription" and d["jobs"] > 0 for d in row["demand"])
    # Each crew member's windows and the reason, for the board (ADM-SCH-30).
    assert len(row["availability"]) == 2
    assert all(a["status"] == "Working" and a["windows"] and a["reason"].startswith("Works")
               for a in row["availability"])


def test_capacity_explains_why_a_crew_member_is_off(api, admin, world, run_week):
    sick = world.add_crew()
    world.add_crew()
    world.add_vehicle(cutoff=time(8, 0))
    world.db.add(SchedulingCrewException(crew_id=sick.id, on_date=SUNDAY, kind="Sick"))
    world.db.commit()
    r = api.get(f"{BASE}/capacity", headers=admin, params={
        "society_id": str(world.society.id), "start_date": SUNDAY.isoformat(), "days": 1})
    by = {a["crew_id"]: a for a in r.json()[0]["availability"]}
    assert by[str(sick.id)]["status"] == "Off" and by[str(sick.id)]["windows"] == []
    assert by[str(sick.id)]["reason"] == "Sick on this date."
    others = [a for k, a in by.items() if k != str(sick.id)]
    assert others[0]["status"] == "Working" and others[0]["windows"]


def test_a_crew_exception_removes_that_days_capacity(api, admin, world, run_week):
    crew = world.add_crew(end=480)
    world.add_vehicle()
    world.db.add(SchedulingCrewException(crew_id=crew.id, on_date=SUNDAY, kind="Sick"))
    world.db.commit()
    summary = run_week(days=1)
    assert summary["placed"] == 0 and summary["unscheduled"] == 2  # the Exterior and the Interior


def test_freeze_and_unfreeze_with_the_code(api, admin, world, run_week):
    a = world.add_crew(end=480)
    world.add_vehicle()
    world.db.commit()
    summary = run_week(days=1)
    sid = summary["schedule_id"]
    job = next(j for j in board(api, admin, sid)["jobs"] if j["service"] == "Cleaning-External")

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
                 json={"crew_id": str(a.id), "start_minute": 390})  # clear of the Interior at 420
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
    # The new car's Exterior and Interior, and the first car's Interior that was not placed before.
    assert summary["status"] == "Frozen" and summary["placed"] == 4
    after = {j["id"]: (j["crew_id"], j["start_minute"])
             for j in board(api, admin, sid)["jobs"]}
    for job_id, placement in before.items():
        assert after[job_id] == placement


def test_freeze_by_itself_is_off_until_the_feature_is_on(api, admin, world, run_week, engine):
    world.add_crew()
    world.add_vehicle()
    world.db.commit()
    run_week(days=1)
    with Session(engine) as db:
        assert service.freeze_due(db, datetime(2026, 10, 17, 21, 0, tzinfo=IST)) == []
    set_feature(engine, "scheduler.auto_freeze", True)
    with Session(engine) as db:
        assert len(service.freeze_due(db, datetime(2026, 10, 17, 21, 0, tzinfo=IST))) == 1


def test_the_freeze_cutoff_time_freezes_drafts(api, admin, world, run_week, engine):
    world.add_crew()
    world.add_vehicle()
    world.db.commit()
    run_week(days=1)
    set_feature(engine, "scheduler.auto_freeze", True)
    with Session(engine) as db:
        early = datetime(2026, 10, 17, 19, 59, tzinfo=IST)
        assert service.freeze_due(db, early) == []
        ids = service.freeze_due(db, datetime(2026, 10, 17, 20, 0, tzinfo=IST))
        assert len(ids) == 1
        assert db.get(Schedule, ids[0]).status == "Frozen"


def test_the_crew_day_shows_only_frozen_work_and_no_customer_details(
        api, world, admin, run_week):
    pin_cleaning_to_20(world)
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
    assert day["total"] == 2 and day["left"] == 2 and day["society"] == "DLF Meadows"
    card = next(c for c in day["jobs"] if c["service"] == "Cleaning-External")
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
    assert r.json()["total"] == 2  # the Exterior and the Interior of the car


def test_next_service_for_the_customer(api, world, admin):
    world.add_crew(end=480, name="Ravi Kumar")
    world.add_vehicle(cutoff=time(9, 30))
    world.db.commit()
    days = run_days(api, admin, world.society.id, SUNDAY, 2)
    cust = auth(login(api, "customer")["access_token"])
    params = {"from_date": SUNDAY.isoformat()}

    r = api.get("/v1/customer/next-job", headers=cust, params=params)
    assert r.status_code == 200 and r.json() == {"job": None}  # a draft is not shown

    for d in days:
        api.post(f"{BASE}/schedules/{d['schedule_id']}/freeze", headers=admin)
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


# ---- the admin's settings are honoured (ADM-SET) -------------------------------------

def test_a_changed_unfreeze_code_is_the_one_that_works(api, admin, world, run_week, engine):
    world.add_crew()
    world.add_vehicle()
    world.db.commit()
    sid = run_week(days=1)["schedule_id"]
    assert api.post(f"{BASE}/schedules/{sid}/freeze", headers=admin).status_code == 200
    set_setting(engine, "schedule.unfreeze_code", "open sesame")
    old = api.post(f"{BASE}/schedules/{sid}/unfreeze", headers=admin, json={"code": "unfreeze"})
    assert old.status_code == 403
    new = api.post(f"{BASE}/schedules/{sid}/unfreeze", headers=admin,
                   json={"code": "open sesame"})
    assert new.status_code == 200 and new.json()["status"] == "Draft"


def test_a_changed_freeze_hour_moves_the_cutoff(api, admin, world, run_week, engine):
    world.add_crew()
    world.add_vehicle()
    world.db.commit()
    run_week(days=1)
    set_feature(engine, "scheduler.auto_freeze", True)
    set_setting(engine, "schedule.freeze_hour", 18)
    with Session(engine) as db:
        assert service.freeze_due(db, datetime(2026, 10, 17, 17, 59, tzinfo=IST)) == []
        assert len(service.freeze_due(db, datetime(2026, 10, 17, 18, 0, tzinfo=IST))) == 1


def test_a_changed_service_duration_is_used_for_new_jobs(api, admin, world, run_week, engine):
    world.add_crew(end=480)
    world.add_vehicle()
    world.db.commit()
    with Session(engine) as db:
        seed_defaults(db)
        db.scalar(select(DirectoryService).where(
            DirectoryService.name == "Cleaning-External")).duration_minutes = 35
        db.commit()
    lookup.invalidate()
    run_week(days=1)
    with Session(engine) as db:
        durations = set(db.scalars(select(Job.duration_minutes).where(
            Job.service == "Cleaning-External")))
    assert durations == {35}


def test_the_schedules_of_a_society_list_oldest_first_from_a_date(api, admin, world, run_week):
    # ADM-SCH-35: the Board offers the days of every schedule, not just one.
    world.add_crew()
    world.add_vehicle()
    world.db.commit()
    first = run_week(days=1)
    second = run_day(api, admin, world.society.id, date(2026, 10, 19))

    r = api.get(f"{BASE}/schedules", headers=admin, params={"society_id": str(world.society.id)})
    assert r.status_code == 200, r.text
    rows = r.json()
    assert [s["id"] for s in rows] == [first["schedule_id"], second["schedule_id"]]
    assert rows[0]["start_date"] == "2026-10-18" and rows[0]["status"] == "Draft"
    assert rows[1]["end_date"] == "2026-10-19" and rows[1]["freeze_deadline"]

    r = api.get(f"{BASE}/schedules", headers=admin,
                params={"society_id": str(world.society.id), "date_from": "2026-10-19"})
    assert [s["id"] for s in r.json()] == [second["schedule_id"]]


def test_needs_attention_lists_cars_on_interior_care_with_no_day(api, admin, world):
    """Needs Attention: a car on a plan with Interior care and no preferred Interior day
    is listed, and leaves the list once its day is saved through the subscription."""
    from app.customers.models import Subscription
    from app.directory.models import Plan

    plan = Plan(name="Interior attention plan", monthly_price_rupees=1299, includes_interior=True)
    world.db.add(plan)
    world.db.flush()
    no_day = world.add_vehicle()
    has_day = world.add_vehicle(interior_day="Monday")
    world.db.commit()
    subs = {}
    for car in (no_day, has_day):
        sub = world.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
        sub.plan_id = plan.id
        subs[car.id] = sub.id
    world.db.commit()

    rows = api.get(f"{BASE}/interior-day-missing", headers=admin).json()
    assert [r["vehicle_id"] for r in rows] == [str(no_day.id)]
    assert rows[0]["plan_name"] == "Interior attention plan" and rows[0]["registration"]

    r = api.patch(f"/v1/admin/subscriptions/{subs[no_day.id]}", headers=admin,
                  json={"interior_day": "Monday"})
    assert r.status_code == 200, r.text
    assert api.get(f"{BASE}/interior-day-missing", headers=admin).json() == []


def test_needs_attention_skips_a_plan_without_interior_care(api, admin, world):
    from app.customers.models import Subscription
    from app.directory.models import Plan

    plan = Plan(name="Exterior only plan", monthly_price_rupees=499, includes_interior=False)
    world.db.add(plan)
    world.db.flush()
    car = world.add_vehicle()
    world.db.commit()
    sub = world.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    sub.plan_id = plan.id
    world.db.commit()
    assert api.get(f"{BASE}/interior-day-missing", headers=admin).json() == []
