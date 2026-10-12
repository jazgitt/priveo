import uuid
from datetime import timedelta

from sqlalchemy import select

from app.addons.models import AddonBooking
from app.billing.models import Payment
from app.changes.models import PlanExtension
from app.directory.models import DirectoryAudit
from app.notifications.models import Notification
from app.scheduling import service
from app.scheduling.models import Job, Schedule, SchedulingCrewException, Visit
from app.visits.models import JobOutcome, OperationsDecision
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login


def setup(world, api, admin):
    world.add_crew(start=360, end=840)
    vehicle = world.add_vehicle(interior_day="Sunday")
    world.db.commit()
    response = api.post(
        "/v1/admin/scheduling/run",
        headers=admin,
        json={
            "society_id": str(world.society.id),
            "start_date": SUNDAY.isoformat(),
            "days": 7,
        },
    )
    assert response.status_code == 200, response.text
    sid = response.json()["schedules"][0]["schedule_id"]
    api.post(f"/v1/admin/scheduling/schedules/{sid}/freeze", headers=admin)
    visit = world.db.scalar(
        select(Visit).where(Visit.vehicle_id == vehicle.id, Visit.date == SUNDAY)
    )
    jobs = {j.service: j for j in world.db.scalars(select(Job).where(Job.visit_id == visit.id))}
    return vehicle, sid, visit, jobs


def resolve(api, admin, job, action, **body):
    return api.post(
        f"/v1/admin/operations/jobs/{job.id}/resolve",
        headers=admin,
        json={"action": action, **body},
    )


def missed(world, job):
    world.db.add(
        JobOutcome(
            job_id=job.id,
            kind="could_not_complete",
            reason_key="other",
            note="Car unavailable",
            by_login_id=world.customer_login.id,
        )
    )
    service.set_job_status(world.db, job.id, "Could not complete")


def test_skip_extends_once_moves_unreceived_payment_and_preserves_failure(world, api, admin):
    vehicle, _, visit, jobs = setup(world, api, admin)
    job = jobs["Cleaning-External"]
    missed(world, job)
    from app.customers.models import Subscription

    sub = world.db.scalar(select(Subscription).where(Subscription.vehicle_id == vehicle.id))
    due = Payment(
        customer_id=vehicle.customer_id,
        vehicle_id=vehicle.id,
        subscription_id=sub.id,
        kind="Plan",
        description="Renewal",
        status="Initiated",
        amount_rupees=999,
        due_date=SUNDAY + timedelta(days=20),
        cycle_start=SUNDAY + timedelta(days=20),
        cycle_end=SUNDAY + timedelta(days=50),
    )
    world.db.add(due)
    world.db.commit()
    for _ in range(2):
        result = resolve(
            api, admin, job, "Skip", reason="Crew unavailable", note="One-day extension"
        )
        assert result.status_code == 200, result.text
    world.db.expire_all()
    assert len(list(world.db.scalars(select(PlanExtension)))) == 1
    assert world.db.get(Payment, due.id).due_date == SUNDAY + timedelta(days=21)
    assert (
        world.db.scalar(select(JobOutcome).where(JobOutcome.job_id == job.id)).note
        == "Car unavailable"
    )
    assert world.db.get(Job, jobs["Cleaning-Internal"].id).status == "Scheduled"
    assert world.db.scalar(select(DirectoryAudit).where(DirectoryAudit.entity == "operations"))
    assert world.db.scalar(select(Notification).where(Notification.event == "service_skipped"))
    history = api.get("/v1/admin/operations/jobs?queue=history", headers=admin).json()
    assert history[0]["resolved_by"] and history[0]["resolution_reason"] == "Crew unavailable"


def test_next_day_internal_retry_preserves_frozen_work_and_calendar_link(world, api, admin):
    vehicle, sid, visit, jobs = setup(world, api, admin)
    job = jobs["Cleaning-Internal"]
    service.set_job_status(world.db, jobs["Cleaning-External"].id, "Completed")
    missed(world, job)
    before = {
        j.id: (j.crew_id, j.start_minute) for j, _ in service._jobs_of(world.db, uuid.UUID(sid))
    }
    result = resolve(api, admin, job, "Reschedule")
    assert result.status_code == 200, result.text
    assert result.json()["rescheduled_on"] == (SUNDAY + timedelta(days=1)).isoformat()
    assert result.json()["replacement_assigned"]
    assert resolve(api, admin, job, "Reschedule").status_code == 200
    assert not any(
        j["id"] == str(job.id)
        for j in api.get("/v1/admin/operations/jobs?queue=missed", headers=admin).json()
    )
    assert any(
        j["id"] == str(job.id)
        for j in api.get("/v1/admin/operations/jobs?queue=history", headers=admin).json()
    )
    world.db.expire_all()
    redo = world.db.scalar(select(Job).where(Job.source_job_id == job.id))
    assert redo and redo.crew_id
    assert world.db.get(Job, job.id).status == "Could not complete"
    for jid, placement in before.items():
        original = world.db.get(Job, jid)
        assert (original.crew_id, original.start_minute) == placement
    service.run_schedule(world.db, world.db.get(Schedule, uuid.UUID(sid)), None)
    assert world.db.get(Job, redo.id).status == "Scheduled"
    customer = auth(login(api, "customer")["access_token"])
    calendar = api.get(
        f"/v1/customer/calendar?month=2026-10&vehicle_id={vehicle.id}", headers=customer
    ).json()
    original = next(v for v in calendar["visits"] if v["visit_id"] == str(visit.id))
    assert original["rescheduled_on"] == (SUNDAY + timedelta(days=1)).isoformat()
    assert world.db.scalar(select(PlanExtension)) is None
    assert resolve(api, admin, job, "Skip").status_code == 409


def test_spa_retry_has_one_job_and_booking_completes_from_retry(world, api, admin):
    vehicle, sid, _, _ = setup(world, api, admin)
    customer = auth(login(api, "customer")["access_token"])
    response = api.post(
        f"/v1/customer/vehicles/{vehicle.id}/addons",
        headers=customer,
        json={"date": SUNDAY.isoformat(), "finish_by": "14:00"},
    )
    assert response.status_code == 201, response.text
    booking = world.db.get(AddonBooking, uuid.UUID(response.json()["id"]))
    job = world.db.scalar(select(Job).where(Job.addon_booking_id == booking.id))
    missed(world, job)
    result = resolve(api, admin, job, "Reschedule")
    assert result.status_code == 200, result.text
    service.run_schedule(world.db, world.db.get(Schedule, uuid.UUID(sid)), None)
    spa_jobs = list(world.db.scalars(select(Job).where(Job.addon_booking_id == booking.id)))
    assert len(spa_jobs) == 2
    redo = next(j for j in spa_jobs if j.source_job_id)
    world.db.refresh(booking)
    service.set_job_status(world.db, redo.id, "Completed")
    world.db.refresh(booking)
    assert booking.status == "Completed"
    assert world.db.scalar(select(PlanExtension)) is None


def test_completed_and_external_jobs_cannot_be_repeated_and_roles_are_enforced(world, api, admin):
    _, _, visit, jobs = setup(world, api, admin)
    ext = jobs["Cleaning-External"]
    missed(world, ext)
    assert resolve(api, admin, ext, "Reschedule").status_code == 409
    internal = jobs["Cleaning-Internal"]
    service.set_job_status(world.db, internal.id, "Completed")
    assert resolve(api, admin, internal, "Skip").status_code == 409
    assert world.db.scalar(select(OperationsDecision)) is None
    customer = auth(login(api, "customer")["access_token"])
    assert api.get("/v1/admin/operations/jobs", headers=customer).status_code == 403
    assert (
        api.get(
            "/v1/admin/operations/jobs?date_from=2026-11-10&date_to=2026-11-01", headers=admin
        ).status_code
        == 422
    )
    assert (
        api.post(
            f"/v1/admin/operations/visits/{visit.id}/skip",
            headers=admin,
            json={"reason": "Crew unavailable"},
        ).status_code
        == 200
    )
    world.db.refresh(internal)
    assert internal.status == "Completed"


def test_unplaced_retry_survives_rerun_and_stays_on_needs_scheduling(world, api, admin):
    _, sid, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-Internal"]
    missed(world, job)
    world.db.add(
        SchedulingCrewException(
            crew_id=world.crew[0].id, on_date=SUNDAY + timedelta(days=1), kind="Leave"
        )
    )
    world.db.commit()
    result = resolve(api, admin, job, "Reschedule")
    assert result.status_code == 200, result.text
    assert result.json()["replacement_assigned"] is False
    world.db.expire_all()
    redo = world.db.scalar(select(Job).where(Job.source_job_id == job.id))
    service.run_schedule(world.db, world.db.get(Schedule, uuid.UUID(sid)), None)
    needs = api.get("/v1/admin/scheduling/needs-scheduling", headers=admin).json()["jobs"]
    assert any(j["id"] == str(redo.id) for j in needs)


def test_past_retry_rolls_back_and_audit_filters_find_the_actual_actor(
    world, api, admin, monkeypatch
):
    _, _, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-Internal"]
    missed(world, job)
    monkeypatch.setattr("app.visits.operations.today_ist", lambda: SUNDAY + timedelta(days=3))
    result = resolve(api, admin, job, "Reschedule")
    assert result.status_code == 409 and result.json()["code"] == "retry_date_passed"
    assert world.db.scalar(select(OperationsDecision)) is None
    assert world.db.scalar(select(Job).where(Job.source_job_id == job.id)) is None
    assert resolve(api, admin, job, "Skip", reason="Retry date passed").status_code == 200
    audit = world.db.scalar(select(DirectoryAudit).where(DirectoryAudit.entity == "operations"))
    rows = api.get(
        f"/v1/admin/directory/audit?entity=operations&actor_id={audit.admin_login_id}",
        headers=admin,
    ).json()
    assert len(rows) == 1 and rows[0]["action"] == "skip"
    assert (
        api.get(
            f"/v1/admin/directory/audit?entity=operations&actor_id={uuid.uuid4()}", headers=admin
        ).json()
        == []
    )
    assert (
        api.get(
            "/v1/admin/directory/audit?date_from=2026-11-10&date_to=2026-11-01", headers=admin
        ).status_code
        == 422
    )
