"""Mandatory remark, new reasons, and the derived visit outcome on crew reads."""
import pytest
from sqlalchemy import select

from app.directory import defaults
from app.visits.models import JobOutcome
from tests.visits.conftest import upload_file
from tests.visits.test_crew_jobs import tick_all


def post(client, headers, job_id, body, manager=False):
    prefix = "/v1/crew/manager/jobs" if manager else "/v1/crew/jobs"
    return client.post(f"{prefix}/{job_id}/could-not-complete", headers=headers, json=body)


@pytest.mark.parametrize("note", [None, "", "   ", "\n\t "])
def test_the_remark_is_mandatory_for_a_crew_member(
        crew_client, make_crew, signin, new_visit, note):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    body = {"reason_key": "other"}
    if note is not None:
        body["note"] = note
    r = post(crew_client, signin(ravi), job.id, body)
    assert r.status_code == 422, r.text
    assert "note" in r.json()["fields"]
    detail = crew_client.get(f"/v1/crew/jobs/{job.id}", headers=signin(ravi)).json()
    assert detail["job"]["status"] == "Scheduled" and detail["outcome"] is None


@pytest.mark.parametrize("note", [None, "  "])
def test_the_remark_is_mandatory_on_the_manager_route(
        crew_client, make_crew, signin, new_visit, note):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    body = {"reason_key": "bad_weather"}
    if note is not None:
        body["note"] = note
    r = post(crew_client, signin(boss), job.id, body, manager=True)
    assert r.status_code == 422 and "note" in r.json()["fields"]


def test_the_remark_has_a_maximum_length(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    r = post(crew_client, signin(ravi), job.id, {"reason_key": "other", "note": "x" * 501})
    assert r.status_code == 422


def test_the_outcome_records_who_when_reason_and_remark(
        crew_client, make_crew, signin, new_visit, db):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    r = post(crew_client, signin(ravi), job.id,
             {"reason_key": "access_restricted", "note": "  Gate chained  "})
    assert r.status_code == 200, r.text
    assert r.json()["outcome"]["note"] == "Gate chained"
    row = db.scalar(select(JobOutcome).where(JobOutcome.job_id == job.id))
    assert row.by_login_id == ravi.login_id and row.at is not None
    assert (row.reason_key, row.note) == ("access_restricted", "Gate chained")


def test_the_new_reasons_are_offered_to_the_crew(crew_client, make_crew, signin, db):
    ravi = make_crew("9000000010", "Ravi")
    # An empty table falls back to the defaults.
    keys = {r["key"] for r in crew_client.get("/v1/crew/reasons", headers=signin(ravi)).json()}
    assert {k for k, _ in defaults.REASONS} == keys
    assert "different_parking_location" in keys and "car_locked" in keys


def finish(client, headers, job):
    jid = str(job.id)
    tick_all(client, headers, jid)
    for kind, stage in (("photo", "Before"), ("photo", "After"), ("video", "During")):
        upload_file(client, headers, jid, kind=kind, stage=stage)
    return client.post(f"/v1/crew/jobs/{jid}/complete", headers=headers).json()


def test_exterior_done_and_interior_missed_is_a_partial_visit(
        crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, jobs = new_visit(["Cleaning-External", "Cleaning-Internal"], assigned=ravi)
    headers = signin(ravi)
    by_service = {j.service: j for j in jobs}
    # Before the end of the visit it is still Scheduled / in progress.
    before = crew_client.get(f"/v1/crew/jobs/{jobs[0].id}", headers=headers).json()["job"]
    assert before["visit_outcome"] == "Scheduled"
    done = finish(crew_client, headers, by_service["Cleaning-External"])
    assert done["job"]["visit_outcome"] == "Scheduled"
    r = post(crew_client, headers, by_service["Cleaning-Internal"].id,
             {"reason_key": "car_locked", "note": "Locked"})
    card = r.json()["job"]
    assert card["visit_outcome"] == "Partially Completed"
    assert card["planned_services"] == ["Cleaning-External", "Cleaning-Internal"]
    assert card["delivered_services"] == ["Cleaning-External"]
    assert card["visit_status"] == "Could not complete"


def test_both_jobs_missed_is_not_completed(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, jobs = new_visit(["Cleaning-External", "Cleaning-Internal"], assigned=ravi)
    for job in jobs:
        r = post(crew_client, signin(ravi), job.id, {"reason_key": "other", "note": "No car"})
    card = r.json()["job"]
    assert card["visit_outcome"] == "Not Completed" and card["delivered_services"] == []


def test_a_fully_done_visit_is_completed(crew_client, make_crew, signin, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    done = finish(crew_client, signin(ravi), job)
    assert done["job"]["visit_outcome"] == "Completed"
    assert "Secret" not in str(done)
