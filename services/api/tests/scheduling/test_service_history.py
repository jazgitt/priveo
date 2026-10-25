"""A-01 / HIST-04 / ADM-CUS-29: a vehicle's service history for the admin, with the
six states, a filter by state, and the original and revised dates of a reschedule."""
import uuid
from datetime import timedelta

import pytest

from app.scheduling import service
from tests.scheduling.conftest import SUNDAY
from tests.scheduling.test_operations import missed, pinned_today, resolve, setup  # noqa: F401
from tests.test_api import auth, login


def history(api, admin, vehicle, **params):
    r = api.get(f"/v1/admin/vehicles/{vehicle.id}/service-history", headers=admin, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def by_date(body):
    return {i["date"]: i for i in body["items"]}


def test_every_planned_visit_starts_as_scheduled_newest_first(world, api, admin):
    vehicle, *_ = setup(world, api, admin)
    body = history(api, admin, vehicle)
    assert body["counts"] == {"Scheduled": 7, "Completed": 0, "Partially Completed": 0,
                              "Not Completed": 0, "Rescheduled": 0, "Cancelled": 0}
    dates = [i["date"] for i in body["items"]]
    assert dates == sorted(dates, reverse=True) and len(dates) == body["total"] == 7
    first = body["items"][-1]
    assert first["date"] == SUNDAY.isoformat() and first["planned"] == [
        "Cleaning-External", "Cleaning-Internal"]
    assert first["original_date"] is None and first["revised_date"] is None


def test_the_six_states_and_the_filter(world, api, admin):
    vehicle, _, visit, jobs = setup(world, api, admin)
    monday, tuesday, wednesday = (SUNDAY + timedelta(days=n) for n in (1, 2, 3))
    from sqlalchemy import select

    from app.scheduling.models import Job, Visit
    day_job = {v.date: j for j, v in world.db.execute(
        select(Job, Visit).join(Visit, Visit.id == Job.visit_id)
        .where(Visit.vehicle_id == vehicle.id, Job.service == "Cleaning-External"))}
    service.set_job_status(world.db, jobs["Cleaning-External"].id, "Completed")
    missed(world, jobs["Cleaning-Internal"])           # Sunday: Partially Completed
    service.set_job_status(world.db, day_job[monday].id, "Completed")      # Monday: Completed
    missed(world, day_job[tuesday])                    # Tuesday: Not Completed
    service.set_job_status(world.db, day_job[wednesday].id, "Skipped")     # Wednesday: Cancelled
    world.db.expire_all()
    body = history(api, admin, vehicle)
    rows = by_date(body)
    assert rows[SUNDAY.isoformat()]["state"] == "Partially Completed"
    assert rows[SUNDAY.isoformat()]["delivered"] == ["Cleaning-External"]
    assert rows[monday.isoformat()]["state"] == "Completed"
    assert rows[tuesday.isoformat()]["state"] == "Not Completed"
    assert rows[wednesday.isoformat()]["state"] == "Cancelled"
    assert body["counts"]["Scheduled"] == 3 and sum(body["counts"].values()) == 7

    partial = history(api, admin, vehicle, state="Partially Completed")
    assert partial["total"] == 1 and partial["counts"] == body["counts"]  # counts ignore the filter
    (item,) = partial["items"]
    assert item["missed"] == [{"service": "Cleaning-Internal", "reason": item["missed"][0]["reason"],
                               "note": "Car unavailable", "rescheduled": False}]
    assert history(api, admin, vehicle, state="Scheduled")["total"] == 3
    assert history(api, admin, vehicle, state="Rescheduled")["items"] == []


def test_a_rescheduled_service_shows_its_original_and_revised_dates(world, api, admin):
    vehicle, _, visit, jobs = setup(world, api, admin)
    service.set_job_status(world.db, jobs["Cleaning-External"].id, "Completed")
    missed(world, jobs["Cleaning-Internal"])
    assert resolve(api, admin, jobs["Cleaning-Internal"], "Reschedule").status_code == 200
    world.db.expire_all()
    body = history(api, admin, vehicle)
    row = by_date(body)[SUNDAY.isoformat()]
    assert row["state"] == "Partially Completed"  # never hidden (C-06)
    assert row["original_date"] == SUNDAY.isoformat()
    assert row["revised_date"] > SUNDAY.isoformat()
    assert row["missed"][0]["rescheduled"] is True


def test_paging(world, api, admin):
    vehicle, *_ = setup(world, api, admin)
    page1 = history(api, admin, vehicle, limit=3)
    page2 = history(api, admin, vehicle, limit=3, offset=3)
    page3 = history(api, admin, vehicle, limit=3, offset=6)
    assert [len(p["items"]) for p in (page1, page2, page3)] == [3, 3, 1]
    seen = [i["visit_id"] for p in (page1, page2, page3) for i in p["items"]]
    assert len(set(seen)) == 7 and page1["total"] == 7


@pytest.mark.parametrize("params", [{"state": "Missed"}, {"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_bad_parameters_are_refused(world, api, admin, params):
    vehicle, *_ = setup(world, api, admin)
    r = api.get(f"/v1/admin/vehicles/{vehicle.id}/service-history", headers=admin, params=params)
    assert r.status_code == 422


def test_admin_only_unknown_vehicle_and_no_customer_details(world, api, admin):
    vehicle, *_ = setup(world, api, admin)
    url = f"/v1/admin/vehicles/{vehicle.id}/service-history"
    assert api.get(f"/v1/admin/vehicles/{uuid.uuid4()}/service-history", headers=admin).status_code == 404
    assert api.get(url).status_code == 401
    crew = auth(login(api, "crew")["access_token"])
    assert api.get(url, headers=crew).status_code == 403
    text = api.get(url, headers=admin).text
    assert "Asha" not in text and "9876543210" not in text
