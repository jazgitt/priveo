"""P1-3: the admin sets a completion status for one scheduled job or many (ADM-OPS-10 to ADM-OPS-12)."""

from sqlalchemy import select

from app.directory.models import CncReason, DirectoryAudit
from app.scheduling import service
from app.scheduling.models import JOB_STATUSES, Job, Visit
from app.visits.models import JobOutcome
from tests.scheduling.conftest import SUNDAY, run_days


def setup(world, api, admin):
    world.add_crew(start=360, end=840)
    vehicle = world.add_vehicle(interior_day="Sunday")
    world.db.add_all([
        CncReason(key="car_locked", label="Car is locked", sort_order=0, defers=True),
        CncReason(key="other", label="Other", sort_order=1, defers=False),
    ])
    world.db.commit()
    days = run_days(api, admin, world.society.id, SUNDAY)
    for day in days:
        api.post(f"/v1/admin/scheduling/schedules/{day['schedule_id']}/freeze", headers=admin)
    visit = world.db.scalar(
        select(Visit).where(Visit.vehicle_id == vehicle.id, Visit.date == SUNDAY)
    )
    jobs = {j.service: j for j in world.db.scalars(select(Job).where(Job.visit_id == visit.id))}
    return vehicle, visit, jobs


def set_status(api, admin, job, **body):
    return api.post(f"/v1/admin/operations/jobs/{job.id}/completion", headers=admin, json=body)


def test_completed_sets_the_status_and_writes_an_audit_row(world, api, admin):
    _, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-External"]
    result = set_status(api, admin, job, status="Completed")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "Completed"
    world.db.expire_all()
    assert world.db.get(Job, job.id).status == "Completed"
    # No outcome row for a completed job: there is nothing to explain.
    assert world.db.scalar(select(JobOutcome).where(JobOutcome.job_id == job.id)) is None
    audit = world.db.scalar(
        select(DirectoryAudit).where(
            DirectoryAudit.entity == "job", DirectoryAudit.entity_id == str(job.id),
            DirectoryAudit.action == "status_set",
        )
    )
    assert audit is not None
    assert audit.detail["status"] == ["Scheduled", "Completed"]


def test_not_completed_needs_a_reason_and_a_remark(world, api, admin):
    _, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-Internal"]
    assert set_status(api, admin, job, status="Could not complete", note="Car away").status_code == 422
    assert set_status(api, admin, job, status="Could not complete", reason_key="other").status_code == 422
    assert set_status(api, admin, job, status="Could not complete", reason_key="nope",
                      note="Car away").status_code == 422
    world.db.expire_all()
    assert world.db.get(Job, job.id).status == "Scheduled"


def test_deferred_and_could_not_complete_follow_the_reason(world, api, admin):
    _, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-Internal"]
    # The reason decides, as for the crew: a deferring reason is Deferred, any other is Could not complete.
    assert set_status(api, admin, job, status="Deferred", reason_key="other", note="Keys").status_code == 422
    assert set_status(api, admin, job, status="Could not complete", reason_key="car_locked",
                      note="Locked").status_code == 422
    world.db.expire_all()
    assert world.db.get(Job, job.id).status == "Scheduled"

    result = set_status(api, admin, job, status="Could not complete", reason_key="other", note="Car away")
    assert result.status_code == 200, result.text
    world.db.expire_all()
    assert world.db.get(Job, job.id).status == "Could not complete"
    outcome = world.db.scalar(select(JobOutcome).where(JobOutcome.job_id == job.id))
    assert (outcome.kind, outcome.reason_key, outcome.note) == ("could_not_complete", "other", "Car away")
    # A not-completed job is on the Missed list for the admin to decide (ADM-CNC-03).
    missed = api.get("/v1/admin/operations/jobs?queue=missed", headers=admin).json()
    assert any(j["id"] == str(job.id) for j in missed)


def test_deferred_uses_a_deferring_reason(world, api, admin):
    _, _, jobs = setup(world, api, admin)
    job = jobs["Cleaning-Internal"]
    result = set_status(api, admin, job, status="Deferred", reason_key="car_locked", note="Locked out")
    assert result.status_code == 200, result.text
    world.db.expire_all()
    assert world.db.get(Job, job.id).status == "Deferred"


def test_bulk_sets_one_status_for_many_jobs(world, api, admin):
    _, visit, jobs = setup(world, api, admin)
    ids = [str(jobs["Cleaning-External"].id), str(jobs["Cleaning-Internal"].id)]
    result = api.post("/v1/admin/operations/bulk-completion", headers=admin, json={
        "job_ids": ids, "status": "Could not complete", "reason_key": "other", "note": "Water cut"})
    assert result.status_code == 200, result.text
    assert len(result.json()) == 2
    world.db.expire_all()
    assert {world.db.get(Job, jobs[s].id).status for s in jobs} == {"Could not complete"}
    audits = world.db.scalars(
        select(DirectoryAudit).where(DirectoryAudit.entity == "job", DirectoryAudit.action == "status_set")
    ).all()
    assert len(audits) == 2
    assert all(a.detail["remark_length"] == len("Water cut") for a in audits)


def test_bulk_changes_nothing_when_one_job_is_closed(world, api, admin):
    _, _, jobs = setup(world, api, admin)
    service.set_job_status(world.db, jobs["Cleaning-External"].id, "Completed")
    ids = [str(jobs["Cleaning-External"].id), str(jobs["Cleaning-Internal"].id)]
    result = api.post("/v1/admin/operations/bulk-completion", headers=admin, json={
        "job_ids": ids, "status": "Completed"})
    assert result.status_code == 409, result.text
    world.db.expire_all()
    assert world.db.get(Job, jobs["Cleaning-Internal"].id).status == "Scheduled"


def test_completion_options_are_the_crew_statuses(world, api, admin):
    setup(world, api, admin)
    body = api.get("/v1/admin/operations/completion-options", headers=admin).json()
    assert body["statuses"] == ["Completed", "Could not complete", "Deferred"]
    assert set(body["statuses"]) <= set(JOB_STATUSES)
    flags = {r["key"]: r["defers"] for r in body["reasons"]}
    assert flags == {"car_locked": True, "other": False}
