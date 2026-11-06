"""SCHS-12: the site's closed weekday gives no cleaner window, no job window and
no capacity, for all three services, and only at rules version 2."""
from datetime import timedelta

import pytest

from app.directory import lookup, rule_seed, site_settings
from app.directory.models import WorkingSlot
from app.scheduling import capacity, service, windows
from tests.scheduling.conftest import SUNDAY

SERVICES = ["Cleaning-External", "Cleaning-Internal", "Deep Spa"]
WEDNESDAY = SUNDAY + timedelta(days=3)
FRIDAY = SUNDAY + timedelta(days=5)
WEEK = [SUNDAY + timedelta(days=i) for i in range(7)]


def _slots(world, closed_weekday, services=SERVICES):
    days = [d for d in range(7) if d != closed_weekday]
    for name in services:
        world.db.add(WorkingSlot(society_id=world.society.id, service=name,
                                 start_minute=300, end_minute=660, days=days))


def _version(world, value):
    rule_seed.seed_rule_keys(world.db)
    site_settings.write(world.db, world.society.id, "scheduler.rules_version", value, None)
    lookup.invalidate()


def _site(world, closed_weekday=2, version=2, services=SERVICES):
    world.add_crew()
    _slots(world, closed_weekday, services)
    world.db.commit()
    _version(world, version)
    return service.load_crew(world.db, world.society.id)


def _cap(world, day):
    return capacity.capacity(world.db, world.society.id, day, day)[0]


def test_schr_par_02_no_cleaner_has_a_window_on_the_closed_weekday(world):
    crew = _site(world)
    avail = service.availability(world.db, crew, WEEK)
    assert avail[WEDNESDAY] == {}
    assert all(avail[d] for d in WEEK if d != WEDNESDAY)


@pytest.mark.parametrize("name", SERVICES)
def test_schr_par_16_every_service_has_no_job_window_on_the_closed_weekday(world, name):
    _site(world)
    assert not windows.job_windows(world.db, world.society.id, name, WEDNESDAY)
    assert windows.job_windows(world.db, world.society.id, name, SUNDAY)


def test_schr_par_02_capacity_is_zero_on_the_closed_weekday_and_unchanged_elsewhere(world):
    _site(world)
    assert _cap(world, WEDNESDAY)["capacity_minutes"] == 0
    assert _cap(world, WEDNESDAY)["crew"] == []
    assert _cap(world, SUNDAY)["capacity_minutes"] == 60


def test_schr_par_02_crew_hours_that_include_the_closed_day_add_nothing(world):
    crew = _site(world)
    member = next(iter(crew.values()))
    member.working_hours = [
        {"day": d, "working": True, "start": "05:30", "end": "12:00", "extra_slots": []}
        for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]]
    world.db.commit()
    avail = service.availability(world.db, service.load_crew(world.db, world.society.id), WEEK)
    assert avail[WEDNESDAY] == {}
    assert avail[SUNDAY][member.id] == [(330, 720)]
    assert _cap(world, WEDNESDAY)["capacity_minutes"] == 0


def test_schr_hard_07_no_job_is_planned_on_the_closed_weekday(world, api, admin, run_week):
    world.add_vehicle()
    _site(world)
    summary = run_week(days=4)  # Sunday to Wednesday
    b = api.get("/v1/admin/scheduling/board", headers=admin,
                params={"schedule_id": summary["schedule_id"]}).json()
    assert all(j["date"] != WEDNESDAY.isoformat() for j in b["jobs"])
    assert any(j["date"] == SUNDAY.isoformat() for j in b["jobs"])


def test_schr_par_02_the_closed_weekday_is_not_hardcoded(world):
    crew = _site(world, closed_weekday=4)
    avail = service.availability(world.db, crew, WEEK)
    assert avail[FRIDAY] == {}
    assert avail[WEDNESDAY]  # Wednesday is open at this site


def test_schr_par_02_a_service_slot_on_the_day_keeps_it_open(world):
    crew = _site(world, services=SERVICES[:2])
    world.db.add(WorkingSlot(society_id=world.society.id, service="Deep Spa",
                             start_minute=0, end_minute=1440, days=list(range(7))))
    world.db.commit()
    assert service.availability(world.db, crew, WEEK)[WEDNESDAY]


def test_schr_par_02_a_site_without_slots_has_no_closed_day(world):
    world.add_crew()
    world.db.commit()
    _version(world, 2)
    crew = service.load_crew(world.db, world.society.id)
    assert service.availability(world.db, crew, WEEK)[WEDNESDAY]


def test_schr_par_02_at_rules_version_1_nothing_changes(world):
    crew = _site(world, version=1)
    assert service.availability(world.db, crew, WEEK)[WEDNESDAY]
    assert _cap(world, WEDNESDAY)["capacity_minutes"] == 60


def test_schr_par_02_without_the_version_setting_nothing_changes(world):
    world.add_crew()
    _slots(world, 2)
    world.db.commit()
    crew = service.load_crew(world.db, world.society.id)
    assert service.availability(world.db, crew, WEEK)[WEDNESDAY]
