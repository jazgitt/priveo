"""SCHS-45: each cross-zone job stores its reason; the Board and the daily view show it."""
from datetime import time, timedelta

from sqlalchemy import select

from app.scheduling import service
from app.scheduling.models import Job, Schedule, Visit
from app.scheduling.post_solve import zone_reason
from tests.scheduling.builders import Scenario
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login

MONDAY = SUNDAY + timedelta(days=1)


def _reasons(sc):
    sc.db.expire_all()
    return {v.vehicle_id: j.cross_zone_reason for j, v in sc.db.execute(
        select(Job, Visit).join(Visit, Visit.id == Job.visit_id)).all() if j.status != "Skipped"}


def _two(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Asha", shift=(360, 600), zone="Z1")
    sc.cleaner("Bala", shift=(360, 600), zone="Z2")
    return sc


def test_schr_zone_06_a_cleaner_away_means_home_zone_cleaner_absent(world):
    sc = _two(world)
    car = sc.car(zone="Z1")
    sc.exception(sc.cleaners["Asha"], MONDAY)
    sc.run(MONDAY)
    assert _reasons(sc)[car.id] == zone_reason.ABSENT


def test_schr_zone_06_a_full_home_zone_means_home_zone_full(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Asha", shift=(360, 390), zone="Z1")  # room for one Exterior
    sc.cleaner("Bala", shift=(360, 600), zone="Z2")
    cars = sc.cars(2, zone="Z1")
    sc.run(MONDAY)
    found = _reasons(sc)
    assert sorted(v or "" for v in found.values()) == ["", zone_reason.FULL]
    assert all(c.id in found for c in cars)


def test_schr_zone_06_a_job_for_a_cleaner_with_room_is_spare_capacity_used(world):
    sc = _two(world)
    car = sc.car(zone="Z1")
    sc.fixed(car, MONDAY, sc.cleaners["Bala"], 360)  # placed by hand on the other zone's cleaner
    sc.run(MONDAY)
    assert _reasons(sc)[car.id] == zone_reason.SPARE


def test_schr_zone_06_a_cutoff_the_home_cleaner_cannot_meet_is_named(world):
    sc = _two(world)
    busy, early = sc.cars(2, zone="Z1"), sc.car(zone="Z1", cutoff=time(7, 0))
    for i, car in enumerate(busy):  # Asha is busy from 06:00 to 07:00
        sc.fixed(car, MONDAY, sc.cleaners["Asha"], 360 + 30 * i)
    sc.run(MONDAY)
    assert _reasons(sc)[early.id] == zone_reason.NEEDED
    assert [_reasons(sc)[c.id] for c in busy] == [None, None]


def test_schr_zone_06_a_job_in_the_home_zone_has_no_reason_and_a_rerun_clears_it(world):
    sc = _two(world)
    car = sc.car(zone="Z1")
    sc.exception(sc.cleaners["Asha"], MONDAY)
    sc.run(MONDAY)
    assert _reasons(sc)[car.id] == zone_reason.ABSENT
    for e in list(sc.db.scalars(select(type(sc.exception(sc.cleaners["Bala"], SUNDAY))))):
        if e.on_date == MONDAY:
            sc.db.delete(e)
    sc.db.commit()
    sc.run(MONDAY)
    assert _reasons(sc)[car.id] is None


def test_schr_zone_06_a_site_without_home_zones_stores_no_reason(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Asha", shift=(360, 600))
    car = sc.car(zone="Z1")
    sc.run(MONDAY)
    assert _reasons(sc)[car.id] is None


def test_schr_zone_06_the_interior_reason_when_the_home_zone_is_full():
    # Direct check of the room test: one window 06:00-07:00 held by two 30 minute jobs.
    assert zone_reason._fits([(360, 420)], [(360, 390), (390, 420)], 30, None) == (False, False)
    assert zone_reason._fits([(360, 480)], [(360, 420)], 30, 450) == (True, True)
    assert zone_reason._fits([(360, 480)], [(360, 420)], 30, 440) == (True, False)


def test_schr_zone_06_the_board_and_the_daily_view_carry_the_reason(api, world):
    sc = _two(world)
    sc.car(zone="Z1", cutoff=time(9, 0))  # the daily view needs a cutoff to show a job
    sc.exception(sc.cleaners["Asha"], MONDAY)
    sc.run(MONDAY)
    admin = auth(login(api, "admin")["access_token"])
    daily = api.get("/v1/admin/scheduling/reports/daily", headers=admin,
                    params={"society_id": str(world.society.id), "date": MONDAY.isoformat()}).json()
    assert daily["cleaners"][0]["jobs"][0]["cross_zone_reason"] == zone_reason.ABSENT
    schedule = sc.db.scalar(select(Schedule).where(Schedule.society_id == world.society.id))
    rows = service.board(sc.db, schedule)["jobs"]
    assert [r["cross_zone_reason"] for r in rows] == [zone_reason.ABSENT]


# ---- SCHR-ZONE-06: the reason helpers (gap check, 06-Nov-26) -----------------


def test_schr_zone_06_room_is_found_in_a_gap_between_busy_spans_and_checked_against_the_cutoff():
    from app.scheduling.post_solve import zone_reason

    windows = [(480, 600)]
    busy = [(540, 600)]  # the cleaner is busy from 09:00 to the end
    # 30 minutes fit at 08:00, which is before a 08:50 cutoff.
    assert zone_reason._fits(windows, busy, 30, 530) == (True, True)
    # The same gap is found, but no cutoff can be met before 08:20.
    assert zone_reason._fits(windows, busy, 30, 500) == (True, False)
    # No gap of 30 minutes at all.
    assert zone_reason._fits([(480, 500)], [(490, 500)], 30, None) == (False, False)
    # No cutoff: any room counts as in time.
    assert zone_reason._fits(windows, [], 30, None) == (True, True)


def test_schr_zone_06_a_skipped_job_is_given_no_reason():
    import uuid
    from types import SimpleNamespace

    from app.scheduling.post_solve import zone_reason

    cleaner, vehicle = uuid.uuid4(), uuid.uuid4()
    key = f"{cleaner}|a"
    job = SimpleNamespace(crew_id=cleaner, start_minute=480, duration_minutes=30,
                          finish_by_minute=None, status="Skipped", cross_zone_reason="old")
    visit = SimpleNamespace(vehicle_id=vehicle)
    ctx = SimpleNamespace(zone_days={SUNDAY: {
        "home": {key: "Z1"}, "vehicle_zone": {str(vehicle): "Z2"},
        "crew": {key: [(360, 600)]}}})
    zone_reason.after_solve(ctx, SUNDAY, [(job, visit)], None)
    assert job.cross_zone_reason is None
