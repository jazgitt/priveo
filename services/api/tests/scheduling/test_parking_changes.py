"""S-07 / ADM-CUS-27 / CRW-SCH-17: a temporary or permanent change of a vehicle's
parking slot, shown on the crew job card and the admin schedule for the job's date."""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.customers.models import VehicleParkingChange
from app.directory.models import DirectoryAudit
from app.scheduling import service
from app.scheduling.models import Job
from app.visits import service as visits
from tests.scheduling.conftest import SUNDAY
from tests.scheduling.test_operations import setup

TODAY = SUNDAY - timedelta(days=1)
MONDAY = SUNDAY + timedelta(days=1)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    monkeypatch.setattr("app.customers.parking.today_ist", lambda: TODAY)


def url(vehicle, tail=""):
    return f"/v1/admin/vehicles/{vehicle.id}/parking-changes{tail}"


def change(api, admin, vehicle, **body):
    body = {"basement": "B1", "number": "24", "from_date": SUNDAY.isoformat(), **body}
    return api.post(url(vehicle), headers=admin, json=body)


def card_parking(world, jobs, day):
    crew = world.crew[0]
    cards = visits.list_jobs(world.db, crew.login_id, day).jobs
    return {c.service: c.parking for c in cards}


def admin_parking(world, visit):
    return {r["service"]: r["parking"] for r in service.job_rows(world.db, Job.visit_id == visit.id)}


def test_a_temporary_change_shows_only_on_its_days(world, api, admin):
    vehicle, _, visit, jobs = setup(world, api, admin)
    base = f"{vehicle.parking_basement}-{vehicle.parking_number}"
    assert card_parking(world, jobs, SUNDAY)["Cleaning-External"] == base
    r = change(api, admin, vehicle, to_date=SUNDAY.isoformat(), note="Water logging")
    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "Temporary" and r.json()["state"] == "Upcoming"
    world.db.expire_all()
    assert card_parking(world, jobs, SUNDAY) == {
        "Cleaning-External": "B1-24", "Cleaning-Internal": "B1-24"}
    assert admin_parking(world, visit)["Cleaning-External"] == "B1-24"
    # The next day, and the crew day list, fall back to the vehicle's own slot.
    assert card_parking(world, jobs, MONDAY)["Cleaning-External"] == base
    day = service.crew_day(world.db, world.crew[0].login_id, SUNDAY)["jobs"]
    assert {(j["parking_basement"], j["parking_number"]) for j in day} == {("B1", "24")}
    other = service.crew_day(world.db, world.crew[0].login_id, MONDAY)["jobs"]
    assert {(j["parking_basement"], j["parking_number"]) for j in other} == {
        (vehicle.parking_basement, vehicle.parking_number)}


def test_a_permanent_change_runs_on_from_its_date_and_the_latest_wins(world, api, admin):
    vehicle, _, visit, jobs = setup(world, api, admin)
    assert change(api, admin, vehicle).json()["kind"] == "Permanent"
    assert change(api, admin, vehicle, basement="b3", number=" 7 ",
                  to_date=SUNDAY.isoformat()).status_code == 201
    world.db.expire_all()
    # The temporary change was made later, so it wins on its day; the permanent one after.
    assert card_parking(world, jobs, SUNDAY)["Cleaning-External"] == "B3-7"
    assert card_parking(world, jobs, MONDAY)["Cleaning-External"] == "B1-24"
    # The vehicle's own slot is never rewritten.
    world.db.refresh(vehicle)
    assert vehicle.parking_basement == "B2"


def test_cancelling_a_change_keeps_it_in_the_history(world, api, admin):
    vehicle, _, visit, jobs = setup(world, api, admin)
    made = change(api, admin, vehicle, to_date=MONDAY.isoformat()).json()
    listing = api.get(url(vehicle), headers=admin).json()
    assert listing["base"] == f"{vehicle.parking_basement}-{vehicle.parking_number}"
    assert listing["today"] == listing["base"]
    assert [c["id"] for c in listing["changes"]] == [made["id"]]
    assert api.delete(url(vehicle, f"/{made['id']}"), headers=admin).status_code == 204
    assert api.delete(url(vehicle, f"/{made['id']}"), headers=admin).status_code == 204  # again
    world.db.expire_all()
    assert card_parking(world, jobs, SUNDAY)["Cleaning-External"] == listing["base"]
    (kept,) = api.get(url(vehicle), headers=admin).json()["changes"]
    assert kept["state"] == "Cancelled"
    assert world.db.scalar(select(VehicleParkingChange).where(
        VehicleParkingChange.id == uuid.UUID(made["id"]))).cancelled_at is not None


def test_a_change_that_covers_today_shows_as_current(world, api, admin):
    vehicle, *_ = setup(world, api, admin)
    change(api, admin, vehicle, from_date=TODAY.isoformat(), to_date=SUNDAY.isoformat())
    listing = api.get(url(vehicle), headers=admin).json()
    assert listing["today"] == "B1-24" and listing["changes"][0]["state"] == "Current"


def test_bad_changes_are_refused(world, api, admin):
    vehicle, *_ = setup(world, api, admin)
    assert change(api, admin, vehicle, basement="Z9").status_code == 422
    assert change(api, admin, vehicle, number="  ").status_code == 422
    assert change(api, admin, vehicle, to_date=TODAY.isoformat()).status_code == 422  # ends first
    old = (TODAY - timedelta(days=5)).isoformat()
    assert change(api, admin, vehicle, from_date=old, to_date=old).status_code == 422  # over
    assert api.get(url(vehicle), headers=admin).json()["changes"] == []


def test_unknown_ids_are_404_and_only_the_admin_may_use_it(world, api, admin):
    vehicle, *_ = setup(world, api, admin)
    ghost = type("V", (), {"id": uuid.uuid4()})
    assert api.get(url(ghost), headers=admin).status_code == 404
    assert change(api, admin, ghost).status_code == 404
    assert api.delete(url(vehicle, f"/{uuid.uuid4()}"), headers=admin).status_code == 404
    assert api.get(url(vehicle)).status_code == 401
    assert api.post(url(vehicle), json={}).status_code == 401


def test_each_change_and_cancel_is_audited(world, api, admin):
    vehicle, *_ = setup(world, api, admin)
    made = change(api, admin, vehicle).json()
    api.delete(url(vehicle, f"/{made['id']}"), headers=admin)
    actions = [a.action for a in world.db.scalars(select(DirectoryAudit).where(
        DirectoryAudit.entity == "parking", DirectoryAudit.entity_id == str(vehicle.id))
        .order_by(DirectoryAudit.at))]
    assert actions == ["create", "cancel"]


def test_a_range_without_changes_uses_the_vehicles_slot(world):
    from app.customers.parking import slots
    vehicle = world.add_vehicle()
    assert slots(world.db, []) == {}
    assert slots(world.db, [(vehicle, date(2026, 1, 1))]) == {
        (vehicle.id, date(2026, 1, 1)): (vehicle.parking_basement, vehicle.parking_number)}
