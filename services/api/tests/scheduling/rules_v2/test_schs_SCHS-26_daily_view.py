"""SCHS-26: the daily cleaner view endpoint (SCHR-OUT-01)."""
from datetime import time

from app.scheduling.models import Job, ScheduleFinding, Visit
from tests.scheduling.builders import Scenario
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login

URL = "/v1/admin/scheduling/reports/daily"


def get(api, world, day=SUNDAY, **extra):
    admin = auth(login(api, "admin")["access_token"])
    return api.get(URL, headers=admin,
                   params={"society_id": str(world.society.id), "date": day.isoformat(), **extra})


def test_SCHR_OUT_01_row_has_the_sheet_fields(api, world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", zone="A", shift=(360, 600))
    car = sc.car(zone="A", cutoff=time(9, 0))
    sc.run(SUNDAY)
    r = get(api, world)
    assert r.status_code == 200, r.text
    body = r.json()
    assert [c["name"] for c in body["cleaners"]] == ["Ravi"]
    cleaner = body["cleaners"][0]
    assert cleaner["break"] is None and cleaner["free_slots"] is None
    job = cleaner["jobs"][0]
    assert job["vehicle_id"] == str(car.id) and job["zone"] == "A"
    assert job["type"] == "Exterior"
    assert job["start_time"] and job["end_time"] and job["cutoff"] == "09:00"
    assert job["exceptions"] == [] and job["cross_zone_reason"] is None


def test_SCHR_OUT_01_exceptions_and_cross_zone_reason_are_read_from_the_job(api, world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", zone="A", shift=(360, 600))
    sc.car(zone="A", cutoff=time(9, 0))
    sc.run(SUNDAY)
    visit_job = world.db.query(Job).join(Visit, Visit.id == Job.visit_id).one()
    visit_job.cross_zone_reason = "Zone B had no cleaner"
    world.db.add(ScheduleFinding(schedule_id=world.db.get(Visit, visit_job.visit_id).schedule_id,
                                 job_id=visit_job.id, code="key_unavailable", detail="Key out"))
    world.db.commit()
    job = get(api, world).json()["cleaners"][0]["jobs"][0]
    assert job["cross_zone_reason"] == "Zone B had no cleaner"
    assert job["exceptions"] == [{"code": "key_unavailable", "detail": "Key out"}]


def test_SCHR_OUT_01_other_days_unassigned_jobs_and_non_admins_are_left_out(api, world):
    sc = Scenario(world)
    sc.slots()
    sc.car()
    sc.run(SUNDAY)  # no cleaner: the job is unassigned
    assert get(api, world).json()["cleaners"] == []
    assert get(api, world, day=SUNDAY.replace(day=SUNDAY.day + 1)).json()["cleaners"] == []
    cust = auth(login(api, "customer")["access_token"])
    r = api.get(URL, headers=cust, params={"society_id": str(world.society.id),
                                           "date": SUNDAY.isoformat()})
    assert r.status_code == 403
