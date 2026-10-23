"""Derived visit outcomes on the customer reads: Partially Completed and the
other service-history states. Nothing is stored; the repository holds jobs."""
from datetime import date

from app.customer_reads.repository import Job, JobOutcomeEntry, Visit


def _visit(repo, ids, vid, status, jobs, day=date(2026, 11, 4)):
    repo.visit_rows.append(Visit(vid, ids[0], day, status))
    repo.job_rows.extend(jobs)


def _missed(reason="Car is locked", note="Gate shut"):
    return JobOutcomeEntry("could_not_complete", reason, note)


def test_exterior_done_and_interior_missed_is_partially_completed(api, asha, repo):
    _visit(repo, asha["vehicles"], "v-p", "Missed", [
        Job("p-1", "v-p", "Cleaning-External", "Done", crew_name="Ravi"),
        Job("p-2", "v-p", "Cleaning-Internal", "Missed", crew_name="Ravi", outcome=_missed()),
    ])
    body = api.get("/v1/customer/visits/v-p", headers=asha["headers"]).json()
    assert body["outcome"] == "Partially Completed"
    assert body["planned_services"] == ["Cleaning-External", "Cleaning-Internal"]
    assert body["delivered_services"] == ["Cleaning-External"]
    assert body["missed_services"][0]["service"] == "Cleaning-Internal"
    assert body["missed_services"][0]["reason"] == "Car is locked"
    assert body["outcome_summary"] == "Exterior done. Interior not done today: Car is locked."

    history = api.get("/v1/customer/history", headers=asha["headers"]).json()
    item = next(i for i in history if i["visit_id"] == "v-p")
    assert item["outcome"] == "Partially Completed"
    assert item["outcome_summary"] == body["outcome_summary"]


def test_partial_copy_names_no_crew_member(api, asha, repo):
    _visit(repo, asha["vehicles"], "v-p", "Missed", [
        Job("p-1", "v-p", "Cleaning-External", "Done", crew_name="Ravi"),
        Job("p-2", "v-p", "Cleaning-Internal", "Missed", outcome=_missed()),
    ])
    body = api.get("/v1/customer/visits/v-p", headers=asha["headers"]).json()
    assert "Ravi" not in body["outcome_summary"]


def test_service_history_states(api, asha, repo):
    ids = asha["vehicles"]
    _visit(repo, ids, "v-done", "Completed", [Job("d-1", "v-done", "Cleaning-External", "Done")])
    _visit(repo, ids, "v-none", "Missed", [
        Job("n-1", "v-none", "Cleaning-Internal", "Missed", outcome=_missed())])
    _visit(repo, ids, "v-redo", "Missed", [
        Job("r-1", "v-redo", "Cleaning-Internal", "Missed", outcome=_missed())])
    repo.job_rows.append(Job("r-2", "v-next", "Cleaning-Internal", "Pending", source_job_id="r-1"))
    _visit(repo, ids, "v-cancel", "Skipped", [
        Job("c-1", "v-cancel", "Deep Spa", "Skipped", addon_cancelled=True)])
    _visit(repo, ids, "v-open", "Scheduled", [Job("o-1", "v-open", "Cleaning-External", "Pending")])

    def outcome(vid):
        return api.get(f"/v1/customer/visits/{vid}", headers=asha["headers"]).json()["outcome"]

    assert outcome("v-done") == "Completed"
    assert outcome("v-none") == "Not Completed"
    assert outcome("v-redo") == "Rescheduled"
    assert outcome("v-cancel") == "Cancelled"
    assert outcome("v-open") == "Scheduled"


def test_a_completed_visit_has_no_missed_services(api, asha):
    body = api.get("/v1/customer/visits/v-1", headers=asha["headers"]).json()
    assert body["outcome"] == "Completed"
    assert body["missed_services"] == [] and body["outcome_summary"] == ""


def test_the_calendar_lists_a_partial_day_as_partially_completed(api, asha, repo):
    _visit(repo, asha["vehicles"], "v-p", "Missed", [
        Job("p-1", "v-p", "Cleaning-External", "Done"),
        Job("p-2", "v-p", "Cleaning-Internal", "Missed", outcome=_missed()),
    ], day=date(2026, 11, 4))
    month = api.get("/v1/customer/calendar?month=2026-11", headers=asha["headers"]).json()
    day = next(v for v in month["visits"] if v["visit_id"] == "v-p")
    assert day["state"] == "Partially Completed"
