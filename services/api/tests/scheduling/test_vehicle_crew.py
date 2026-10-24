"""ADM-CUS-28: the admin's read-only view of the crew who serve a vehicle."""
import uuid

from app.scheduling import service
from tests.scheduling.test_operations import setup


def crew_of(api, admin, vehicle_id):
    return api.get(f"/v1/admin/vehicles/{vehicle_id}/crew", headers=admin)


def test_the_crew_are_read_from_the_vehicles_scheduled_jobs(world, api, admin, monkeypatch):
    vehicle, _, visit, jobs = setup(world, api, admin)
    monkeypatch.setattr("app.customers.administration.today_ist", lambda: visit.date)
    r = crew_of(api, admin, vehicle.id)
    assert r.status_code == 200, r.text
    (member,) = r.json()
    assert member["name"] == "Ravi" and member["role"] == "Member"
    assert set(member["services"]) == {"Cleaning-External", "Cleaning-Internal"}
    # A week: External every day (7) and Internal on the care day (1).
    assert member["jobs"] == 8 and member["next_date"] == visit.date.isoformat()
    # No customer name or mobile number reaches the crew view.
    assert "Asha" not in r.text and "9876543210" not in r.text


def test_skipped_jobs_and_past_days_are_left_out(world, api, admin, monkeypatch):
    vehicle, _, visit, jobs = setup(world, api, admin)
    monkeypatch.setattr("app.customers.administration.today_ist", lambda: visit.date)
    service.set_job_status(world.db, jobs["Cleaning-Internal"].id, "Skipped")
    (member,) = crew_of(api, admin, vehicle.id).json()
    assert member["services"] == ["Cleaning-External"] and member["jobs"] == 7
    monkeypatch.setattr("app.customers.administration.today_ist",
                        lambda: visit.date.replace(year=visit.date.year + 1))
    assert crew_of(api, admin, vehicle.id).json() == []


def test_an_unknown_vehicle_is_404_and_only_the_admin_may_read(world, api, admin):
    vehicle, *_ = setup(world, api, admin)
    assert crew_of(api, admin, uuid.uuid4()).status_code == 404
    assert api.get(f"/v1/admin/vehicles/{vehicle.id}/crew").status_code == 401
