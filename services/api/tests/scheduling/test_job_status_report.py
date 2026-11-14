"""Operations > Reports: the completed service per vehicle and day."""

from datetime import timedelta

from app.visits.job_report import cell_label
from tests.scheduling.conftest import SUNDAY
from tests.scheduling.test_completion_status import set_status, setup

EXT, INT, SPA = "Cleaning-External", "Cleaning-Internal", "Deep Spa"


def report(api, admin, **q):
    return api.get("/v1/admin/operations/job-status-report", headers=admin, params=q)


def test_cell_labels():
    assert cell_label({EXT}) == "EXT"
    assert cell_label({INT}) == "INT"
    assert cell_label({EXT, INT}) == "Both"
    assert cell_label({SPA}) == "SPA"
    assert cell_label({EXT, SPA}) == "EXT+SPA"
    assert cell_label(set()) == ""


def test_report_marks_completed_services_by_day(world, api, admin):
    vehicle, visit, jobs = setup(world, api, admin)
    start = SUNDAY.isoformat()
    first = report(api, admin, date_from=start, date_to=(SUNDAY + timedelta(days=1)).isoformat())
    assert first.status_code == 200, first.text
    body = first.json()
    assert len(body["dates"]) == 2
    (row,) = [r for r in body["rows"] if r["vehicle_id"] == str(vehicle.id)]
    assert row["registration"] == vehicle.registration
    assert row["cells"] == {}  # planned only, nothing completed yet

    assert set_status(api, admin, jobs[EXT], status="Completed").status_code == 200
    (row,) = report(api, admin, date_from=start, date_to=start).json()["rows"]
    assert row["cells"] == {start: "EXT"}
    assert set_status(api, admin, jobs[INT], status="Completed").status_code == 200
    (row,) = report(api, admin, date_from=start, date_to=start).json()["rows"]
    assert row["cells"] == {start: "Both"}


def test_report_filters_by_society_and_checks_the_period(world, api, admin):
    setup(world, api, admin)
    start = SUNDAY.isoformat()
    other = "00000000-0000-0000-0000-000000000001"
    assert report(api, admin, date_from=start, date_to=start, society_id=other).json()["rows"] == []
    assert report(api, admin, date_from=start, date_to=(SUNDAY - timedelta(days=1)).isoformat()).status_code == 422
    assert report(api, admin, date_from=start, date_to=(SUNDAY + timedelta(days=31)).isoformat()).status_code == 422


def test_operations_job_list_keeps_only_visits_inside_the_dates(world, api, admin):
    setup(world, api, admin)
    day = SUNDAY

    def ids(**q):
        r = api.get("/v1/admin/operations/jobs", headers=admin, params={"queue": "scheduled", **q})
        assert r.status_code == 200, r.text
        return {j["date"] for j in r.json()}

    assert len(ids()) > 1  # the test world plans a week
    assert ids(date_from=day.isoformat(), date_to=day.isoformat()) == {day.isoformat()}
    after = ids(date_from=(day + timedelta(days=1)).isoformat())
    assert after and min(after) > day.isoformat()
    assert ids(date_to=(day - timedelta(days=1)).isoformat()) == set()
