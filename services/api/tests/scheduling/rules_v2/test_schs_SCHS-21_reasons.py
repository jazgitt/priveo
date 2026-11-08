"""SCHS-21: structured unassigned reasons and the shortfall of a run."""
from datetime import time, timedelta

from sqlalchemy import select

from app.scheduling.codes import ReasonCode
from app.scheduling.models import Job, ScheduleFinding
from tests.scheduling.builders import EXTERNAL, Scenario
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login

THURSDAY = SUNDAY + timedelta(days=4)


def _post_run(api, world, day=SUNDAY):
    admin = auth(login(api, "admin")["access_token"])
    r = api.post("/v1/admin/scheduling/run", headers=admin, json={
        "society_id": str(world.society.id), "start_date": day.isoformat(), "days": 1})
    assert r.status_code == 200, r.text
    return admin, r.json()["schedules"][0]


def _capacity_short(world, cars=3, shift=(480, 540)):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=shift)
    sc.cars(cars)
    return sc


def test_SCHR_EXT_04_every_unassigned_job_carries_a_code_and_a_text(world):
    sc = _capacity_short(world)  # room for two 30 minute Exteriors, three cars
    res = sc.run(SUNDAY)
    assert len(res.placed) == 2 and len(res.unassigned) == 1
    assert res.reasons() == [ReasonCode.CAPACITY_SHORT.value]
    assert res.unassigned[0].note == ReasonCode.CAPACITY_SHORT.text
    assert res.findings == [ReasonCode.CAPACITY_SHORT.value]


def test_SCHR_EXT_04_the_run_reports_the_shortfall_in_cars_and_minutes(api, world):
    sc = _capacity_short(world, cars=4)
    sc.db.commit()
    _admin, run = _post_run(api, world)
    assert run["placed"] == 2 and run["unscheduled"] == 2
    assert run["unassigned_exteriors"] == 2 and run["shortfall_cars"] == 2
    assert run["shortfall_minutes"] == 2 * world.db.scalar(
        select(Job.duration_minutes).where(Job.service == EXTERNAL).limit(1))


def test_SCHR_OUT_04_the_job_list_shows_the_code_beside_the_text(api, world):
    sc = _capacity_short(world)
    sc.db.commit()
    admin, _run = _post_run(api, world)
    r = api.get("/v1/admin/scheduling/needs-scheduling", headers=admin,
                params={"society_id": str(world.society.id)})
    assert r.status_code == 200, r.text
    (job,) = r.json()["jobs"]
    assert job["reason_code"] == "capacity_short"
    assert job["reason"] == ReasonCode.CAPACITY_SHORT.text


def test_SCHR_HARD_13_a_job_no_cleaner_window_fits_is_unassigned_with_its_reason(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 500))  # 20 minutes: too short for a 30 minute Exterior
    sc.car()
    res = sc.run(SUNDAY)
    assert res.placed == [] and len(res.unassigned) == 1
    assert res.reasons() == [ReasonCode.SHIFT_TOO_SHORT.value]
    assert res.unassigned[0].note == ReasonCode.SHIFT_TOO_SHORT.text


def test_SCHR_HARD_13_a_day_with_no_cleaner_is_reported_too(world):
    sc = Scenario(world)
    sc.slots()
    sc.car()
    res = sc.run(SUNDAY)
    assert res.reasons() == [ReasonCode.NO_CLEANER.value]
    assert res.unassigned[0].note == ReasonCode.NO_CLEANER.text


def test_SCHR_HARD_09_a_car_that_cannot_be_covered_is_named_in_the_findings(world, site_cfg):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    car = sc.car(cutoff=time(8, 15))  # cannot end by 08:15 from a 08:00 start
    res = sc.run(THURSDAY)
    assert res.unassigned and res.unassigned[0].vehicle_id == car.id
    assert res.reasons() == [ReasonCode.CUSTOMER_CUTOFF.value]
    finding = world.db.scalar(select(ScheduleFinding).where(ScheduleFinding.code == "customer_cutoff"))
    assert finding is not None and finding.detail == ReasonCode.CUSTOMER_CUTOFF.text


def test_SCHR_EXT_01_a_job_placed_on_a_later_run_loses_its_code(world):
    sc = _capacity_short(world)
    assert sc.run(SUNDAY).reasons() == ["capacity_short"]
    sc.cleaner("Meena", shift=(480, 540))
    res = sc.run(SUNDAY)
    assert res.unassigned == [] and len(res.placed) == 3
    assert world.db.scalars(select(Job.reason_code)).all() == [None, None, None]

