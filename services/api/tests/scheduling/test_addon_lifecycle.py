import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.addons.models import AddonBooking
from app.scheduling import service
from app.scheduling.models import Job, Schedule, Visit
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login


def test_standalone_without_subscription_is_scheduled_unpaid_and_tracks_completion(world, api, admin, customer):
    from app.changes.rules import get_now
    from tests.changes.money_fixtures import at
    api.app.dependency_overrides[get_now] = lambda: lambda: at(17, 10)
    from app.billing.models import Payment
    from app.customers.models import Subscription, Vehicle
    world.add_crew(start=360, end=840)
    car = Vehicle(customer_id=world.customer.id, society_id=world.society.id,
                  registration='HR01SP1234', model='Spa car', parking_basement='B2', parking_number='1')
    world.db.add(car)
    world.db.commit()
    response = api.post('/v1/customer/addons/standalone', headers=customer, json={
        'vehicle_id': str(car.id), 'date': SUNDAY.isoformat(), 'finish_by': '12:00'})
    assert response.status_code == 201, response.text
    booking = response.json()
    run(api, admin, world)
    job = world.db.scalar(select(Job).where(Job.addon_booking_id == uuid.UUID(booking['id'])))
    assert job.duration_minutes == 120 and job.finish_by_minute == 720 and job.crew_id
    assert world.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id)) is None
    payment = world.db.get(Payment, uuid.UUID(booking['payment_id']))
    assert payment.status == 'Due'
    service.set_job_status(world.db, job.id, 'Completed')
    result = api.get('/v1/customer/addons', headers=customer).json()['requests'][0]
    assert result['status'] == 'Completed' and result['visit_id'] == str(job.visit_id)


@pytest.fixture
def customer(api):
    return auth(login(api, "customer")["access_token"])


def request(api, customer, vehicle, finish="12:00"):
    r = api.post(
        f"/v1/customer/vehicles/{vehicle.id}/addons",
        headers=customer,
        json={"date": SUNDAY.isoformat(), "finish_by": finish},
    )
    assert r.status_code == 201, r.text
    return r.json()


def run(api, admin, world):
    r = api.post(
        "/v1/admin/scheduling/run",
        headers=admin,
        json={"society_id": str(world.society.id), "start_date": SUNDAY.isoformat(), "days": 7},
    )
    assert r.status_code == 200, r.text
    return r.json()["schedules"][0]["schedule_id"]


def test_booking_reaches_scheduler_without_payment_and_has_its_own_visit(
    world, api, admin, customer
):
    world.add_crew(start=360, end=840)
    v = world.add_vehicle()
    world.db.commit()
    b = request(api, customer, v)
    run(api, admin, world)
    world.db.expire_all()
    job = world.db.scalar(select(Job).where(Job.addon_booking_id == uuid.UUID(b["id"])))
    assert job and job.duration_minutes == 120 and job.finish_by_minute == 720
    assert job.crew_id is not None
    booking = world.db.get(AddonBooking, uuid.UUID(b["id"]))
    assert booking.status == "Scheduled"
    assert b["payment_status"] == "Due"
    plan = world.db.scalar(
        select(Visit).where(Visit.vehicle_id == v.id, Visit.date == SUNDAY, Visit.addon_key == "")
    )
    spa = world.db.get(Visit, job.visit_id)
    assert spa.id != plan.id and spa.addon_key == b["id"]
    plan_job = world.db.scalar(select(Job).where(Job.visit_id == plan.id))
    service.set_job_status(world.db, plan_job.id, "Completed")
    assert world.db.get(Visit, plan.id).status == "Completed"
    assert world.db.get(Visit, spa.id).status == "Scheduled"
    service.set_job_status(world.db, job.id, "Completed")
    assert world.db.get(AddonBooking, booking.id).status == "Completed"


def test_frozen_change_is_a_request_and_cancel_removes_spa_only(world, api, admin, customer):
    world.add_crew(start=360, end=840)
    v = world.add_vehicle()
    world.db.commit()
    b = request(api, customer, v)
    sid = run(api, admin, world)
    assert (
        api.post(f"/v1/admin/scheduling/schedules/{sid}/freeze", headers=admin).status_code == 200
    )
    changed = api.patch(
        f"/v1/customer/addons/{b['id']}",
        headers=customer,
        json={"date": (SUNDAY + timedelta(days=1)).isoformat(), "finish_by": "13:00"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["change_requested"] and changed.json()["date"] == SUNDAY.isoformat()
    assert (
        api.patch(
            f"/v1/admin/addons/{b['id']}", headers=admin, json={"resolve_change": True}
        ).status_code
        == 409
    )
    assert api.delete(f"/v1/customer/addons/{b['id']}", headers=customer).status_code == 200
    world.db.expire_all()
    job = world.db.scalar(select(Job).where(Job.addon_booking_id == uuid.UUID(b["id"])))
    assert job.status == "Skipped"
    plan_jobs = list(
        world.db.scalars(
            select(Job)
            .join(Visit, Visit.id == Job.visit_id)
            .where(Visit.vehicle_id == v.id, Visit.date == SUNDAY, Visit.addon_key == "")
        )
    )
    assert all(j.status == "Scheduled" for j in plan_jobs)


def test_unfit_booking_stays_requested_and_late_additions_do_not_move_frozen_jobs(
    world, api, admin, customer
):
    world.add_crew(start=360, end=480)
    v = world.add_vehicle()
    world.db.commit()
    sid = run(api, admin, world)
    api.post(f"/v1/admin/scheduling/schedules/{sid}/freeze", headers=admin)
    before = api.get(f"/v1/admin/scheduling/board?schedule_id={sid}", headers=admin).json()["jobs"]
    b = request(api, customer, v, "07:00")
    assert b["status"] == "Requested"
    after = api.get(f"/v1/admin/scheduling/board?schedule_id={sid}", headers=admin).json()["jobs"]
    positions = {j["id"]: (j["crew_id"], j["start_minute"]) for j in after}
    assert all(positions[j["id"]] == (j["crew_id"], j["start_minute"]) for j in before)
    needs = api.get("/v1/admin/scheduling/needs-scheduling", headers=admin).json()["jobs"]
    assert any(j["service"] == "Deep Spa" for j in needs)


def test_swap_failure_is_atomic_and_suggestions_do_not_write(world, api, admin):
    world.add_crew(start=360, end=480)
    world.add_vehicle()
    world.add_vehicle()
    world.db.commit()
    sid = run(api, admin, world)
    board = api.get(f"/v1/admin/scheduling/board?schedule_id={sid}", headers=admin).json()
    jobs = [j for j in board["jobs"] if j["date"] == SUNDAY.isoformat()]
    before = {(j["id"], j["crew_id"], j["start_minute"]) for j in board["jobs"]}
    preview = api.get(f"/v1/admin/scheduling/schedules/{sid}/suggestions", headers=admin)
    assert preview.status_code == 200
    fresh = api.get(f"/v1/admin/scheduling/board?schedule_id={sid}", headers=admin).json()
    assert before == {(j["id"], j["crew_id"], j["start_minute"]) for j in fresh["jobs"]}
    # The first placement succeeds, but the second cannot fit. Both must roll back.
    second = world.db.get(Job, uuid.UUID(jobs[1]["id"]))
    second.duration_minutes = 140
    world.db.commit()
    failed = api.post(
        "/v1/admin/scheduling/jobs/swap",
        headers=admin,
        json={"first_job_id": jobs[0]["id"], "second_job_id": jobs[1]["id"]},
    )
    assert failed.status_code == 409
    unchanged = api.get(f"/v1/admin/scheduling/board?schedule_id={sid}", headers=admin).json()
    assert before == {(j["id"], j["crew_id"], j["start_minute"]) for j in unchanged["jobs"]}
    stale = api.post(
        f"/v1/admin/scheduling/schedules/{sid}/suggestions/apply",
        headers=admin,
        json={"fingerprint": preview.json()["fingerprint"], "job_ids": [jobs[0]["id"]]},
    )
    assert stale.status_code == 409 and stale.json()["code"] == "stale_suggestions"
    api.post(f"/v1/admin/scheduling/schedules/{sid}/freeze", headers=admin)
    bad = api.post(
        "/v1/admin/scheduling/jobs/swap",
        headers=admin,
        json={"first_job_id": jobs[0]["id"], "second_job_id": jobs[1]["id"]},
    )
    assert bad.status_code == 409
    world.db.expire_all()
    assert world.db.get(Schedule, uuid.UUID(sid)).status == "Frozen"
