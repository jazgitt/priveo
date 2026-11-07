"""SCHS-27: the exception report endpoint (SCHR-OUT-03, SCHR-WKE-06)."""
from datetime import time, timedelta

from sqlalchemy import select

from app.scheduling.models import Job, Schedule, ScheduleFinding, Visit
from tests.scheduling.builders import Scenario
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login

URL = "/v1/admin/scheduling/reports/exceptions"
THURSDAY = SUNDAY + timedelta(days=4)
KINDS = ["unassigned_exteriors", "deferred_interiors", "unavailable_keys_cars", "cross_zone",
         "infeasible", "weekend_lateness", "hand_placement", "missed_breaks"]


def get(api, world, start=SUNDAY, end=None):
    admin = auth(login(api, "admin")["access_token"])
    return api.get(URL, headers=admin, params={
        "society_id": str(world.society.id), "start_date": start.isoformat(),
        "end_date": (end or start).isoformat()})


def kinds(r):
    return {k["kind"]: k["rows"] for k in r.json()["kinds"]}


def test_SCHR_OUT_03_every_kind_is_present_and_empty_when_nothing_is_wrong(api, world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.car()
    sc.run(SUNDAY)
    r = get(api, world)
    assert r.status_code == 200, r.text
    assert [k["kind"] for k in r.json()["kinds"]] == KINDS
    assert all(rows == [] for rows in kinds(r).values())


def test_SCHR_OUT_03_an_unassigned_exterior_has_date_car_code_and_no_cleaner(api, world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 540))
    cars = sc.cars(3)
    sc.run(SUNDAY)
    rows = kinds(get(api, world))["unassigned_exteriors"]
    assert len(rows) == 1
    row = rows[0]
    assert row["date"] == SUNDAY.isoformat() and row["code"] == "capacity_short"
    assert row["vehicle_id"] in {str(c.id) for c in cars} and row["registration"]
    assert row["cleaner_id"] is None and row["cleaner_name"] == ""


def test_SCHR_OUT_03_a_cutoff_that_cannot_be_met_is_also_listed_as_infeasible(api, world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.car(cutoff=time(8, 15))
    sc.run(THURSDAY)
    r = get(api, world, THURSDAY)
    assert [x["code"] for x in kinds(r)["infeasible"]] == ["customer_cutoff"]
    assert [x["code"] for x in kinds(r)["unassigned_exteriors"]] == ["customer_cutoff"]


def test_SCHR_OUT_03_unplanned_interiors_cross_zone_and_stored_findings_are_listed(api, world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 510))
    car = sc.car(interior_day="Sunday")
    sc.run(SUNDAY)
    interior = world.db.scalar(select(Job).where(Job.service == "Cleaning-Internal"))
    exterior = world.db.scalar(select(Job).where(Job.service == "Cleaning-External"))
    # One 30 minute slot: leave the Exterior placed and the Interior unplanned.
    cleaner_id = world.db.scalar(select(Job.crew_id).where(Job.crew_id.is_not(None)))
    exterior.crew_id, exterior.start_minute = cleaner_id, 480
    interior.crew_id, interior.start_minute, interior.manual = None, None, False
    schedule_id = world.db.scalar(select(Schedule.id))
    exterior.cross_zone_reason = "Zone B had no cleaner"
    world.db.add_all([
        ScheduleFinding(schedule_id=schedule_id, job_id=exterior.id, code="key_unavailable", detail="Key out"),
        ScheduleFinding(schedule_id=schedule_id, job_id=exterior.id, code="break_missed", detail="No break"),
        ScheduleFinding(schedule_id=schedule_id, job_id=None, code="no_plan", detail="No plan.")])
    world.db.commit()
    k = kinds(get(api, world))
    assert [x["vehicle_id"] for x in k["deferred_interiors"]] == [str(car.id)]
    assert k["deferred_interiors"][0]["job_id"] == str(interior.id)
    assert k["cross_zone"][0]["detail"] == "Zone B had no cleaner" and k["cross_zone"][0]["code"] == "cross_zone"
    assert [x["code"] for x in k["unavailable_keys_cars"]] == ["key_unavailable"]
    assert k["unavailable_keys_cars"][0]["cleaner_name"]
    assert [x["code"] for x in k["missed_breaks"]] == ["break_missed"]
    assert [x["code"] for x in k["infeasible"]] == ["no_plan"] and k["infeasible"][0]["date"] is None


def test_SCHR_WKE_06_a_late_job_on_a_weekend_day_is_reported(api, world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.cars(2, cutoff=time(8, 30))  # one fits before the cutoff; Sunday is soft
    sc.run(SUNDAY)
    rows = kinds(get(api, world))["weekend_lateness"]
    assert len(rows) == 1 and rows[0]["code"] == "weekend_late" and rows[0]["cleaner_name"]
    assert kinds(get(api, world))["unassigned_exteriors"] == []


def test_SCHR_OUT_03_hand_placement_breaches_are_listed(api, world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    cleaner = sc.cleaner(shift=(480, 600))
    sc.cars(2)
    sc.run(SUNDAY)
    one, two = world.db.scalars(select(Job).order_by(Job.start_minute)).all()
    admin = auth(login(api, "admin")["access_token"])
    # 10:00 is after the cleaner's shift (08:00 to 10:00): a breach that is not an
    # overlap, so the admin can confirm it. An overlap is refused (SCHR-HIER-08).
    r = api.post(f"/v1/admin/scheduling/jobs/{two.id}/move", headers=admin, json={
        "crew_id": str(cleaner.id), "start_minute": 600, "override": True})
    assert r.status_code == 200, r.text
    rows = kinds(get(api, world))["hand_placement"]
    assert [(x["code"], x["job_id"]) for x in rows] == [("hand_outside_hours", str(two.id))]
    assert rows[0]["cleaner_name"] and rows[0]["registration"]


def test_dates_outside_the_range_and_bad_ranges_and_non_admins(api, world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.car()
    sc.run(SUNDAY)  # no cleaner
    assert len(kinds(get(api, world))["unassigned_exteriors"]) == 1
    assert kinds(get(api, world, SUNDAY + timedelta(days=1)))["unassigned_exteriors"] == []
    assert get(api, world, SUNDAY, SUNDAY - timedelta(days=1)).status_code == 422
    cust = auth(login(api, "customer")["access_token"])
    r = api.get(URL, headers=cust, params={"society_id": str(world.society.id),
                                           "start_date": SUNDAY.isoformat(), "end_date": SUNDAY.isoformat()})
    assert r.status_code == 403


def test_kill_switch_version_1_reports_no_weekend_lateness_and_is_read_only(api, world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.cars(2, cutoff=time(8, 30))
    sc.run(SUNDAY)
    before = world.db.scalar(select(ScheduleFinding.id).limit(1))
    k = kinds(get(api, world))
    assert k["weekend_lateness"] == [] and k["hand_placement"] == []
    assert world.db.scalar(select(ScheduleFinding.id).limit(1)) == before
    assert world.db.scalars(select(Visit.id)).first() is not None
