"""SCHS-07: the scenario builders and the site_cfg and rules_v2 fixtures."""
from datetime import time, timedelta

from app.directory import lookup, site_settings
from app.scheduling.models import SocietySetting
from tests.scheduling import builders
from tests.scheduling.builders import EXTERNAL, Scenario, default_of
from tests.scheduling.conftest import SUNDAY

MONDAY = SUNDAY + timedelta(days=1)


def test_site_cleaner_car_run_in_a_few_lines(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", shift=(360, 600))
    car = sc.car(cutoff=time(9, 0))
    res = sc.run(SUNDAY)
    assert [p.vehicle_id for p in res.placed_on(SUNDAY)] == [car.id]
    assert not res.unassigned and res.summary.unscheduled == 0


def test_weekly_off_and_unassigned_reason_read_back(world):
    sc = Scenario(world)
    sc.slots(off=[6])  # Sunday off
    sc.cleaner(shift=(360, 600))
    car = sc.car()
    res = sc.run(SUNDAY, days=2)
    assert res.placed_on(SUNDAY) == [] and len(res.placed_on(MONDAY, car)) == 1
    assert res.unassigned == []  # no demand on the off day, nothing is unassigned


def test_no_cleaner_gives_an_unassigned_job_with_its_note(world):
    sc = Scenario(world)
    sc.slots()
    sc.car()
    res = sc.run(SUNDAY)
    assert len(res.unassigned) == 1 and res.unassigned[0].note
    assert res.reasons() == [None]  # EXTENSION POINT: codes arrive with SCHS-21
    assert res.findings == []


def test_cleaner_zone_exception_and_car_zone(world):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner("Ravi", zone="A", shift=(360, 600), reporting=300, first_job=330)
    sc.exception(ravi, SUNDAY, "Sick")
    car = sc.car(zone="A", cutoff=time(9, 0), interior_day="Monday")
    assert ravi.home_zone_id == car.zone_id
    assert (ravi.reporting_minute, ravi.first_job_minute) == (300, 330)
    res = sc.run(SUNDAY)
    assert len(res.unassigned) == 1  # the only cleaner is sick


def test_cleaner_working_days(world):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner(shift=(360, 600), days=[0, 1, 2, 3, 4, 5])
    assert [h["working"] for h in ravi.working_hours] == [True] * 6 + [False]
    sc.car()
    res = sc.run(SUNDAY)
    assert len(res.unassigned) == 1  # Sunday is the cleaner's day off


def test_entitlement_creation_and_break_rule(world):
    sc = Scenario(world)
    car = sc.car(interior_day="Sunday")
    ent = sc.entitlement(car, SUNDAY, seq=2, status="Waived", waived_reason="test")
    assert (ent.vehicle_id, ent.service_week_start, ent.seq) == (car.id, SUNDAY, 2)
    assert ent.subscription_id is not None and ent.status == "Waived"
    rule = sc.break_rule(SUNDAY, MONDAY, minutes=(570, 600))
    assert rule.society_id == world.society.id and rule.crew_id is None and rule.enabled
    ravi = sc.cleaner()
    assert sc.break_rule(SUNDAY, SUNDAY, cleaner=ravi, enabled=False).crew_id == ravi.id


def test_fixed_placement_is_kept_and_a_second_site_is_made(world):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner(shift=(360, 600))
    car = sc.car()
    job = sc.fixed(car, SUNDAY, ravi, 400)  # must be a service the car is due that day
    res = sc.run(SUNDAY)
    assert job.manual
    assert [(p.start, p.manual) for p in res.placed_on(SUNDAY, car, EXTERNAL)] == [(400, True)]
    assert sc.add_site("Other").id != world.society.id


def test_config_helper_sets_site_values(world):
    Scenario(world).config(site_break_start_minute=560, site_break_end_minute=590)
    assert site_settings.read(world.db, world.society.id, "site.break_start_minute") == 560


def test_site_cfg_sets_a_value_and_restores_it(world, site_cfg):
    key = "site.first_job_minute"
    site_cfg({key: 345})
    assert site_settings.read(world.db, world.society.id, key) == 345
    site_cfg(site_reporting_minute=310)  # keyword form
    assert site_settings.read(world.db, world.society.id, "site.reporting_minute") == 310
    assert default_of(key) == 330  # the global default is untouched


def test_site_cfg_restore_removes_own_values_and_puts_old_ones_back(world):
    db, site = world.db, world.society.id
    before = builders.set_site_values(db, site, {"site.first_job_minute": 345})
    assert before == {"site.first_job_minute": None}
    builders.restore_site_values(db, site, before)
    assert site_settings.own_value(db, site, "site.first_job_minute") is None
    assert site_settings.read(db, site, "site.first_job_minute") == 330  # the global default
    builders.set_site_values(db, site, {"site.first_job_minute": 340})
    again = builders.set_site_values(db, site, {"site.first_job_minute": 350})
    assert again == {"site.first_job_minute": 340}
    builders.restore_site_values(db, site, again)
    assert site_settings.own_value(db, site, "site.first_job_minute") == 340


def test_rules_v2_flips_the_switch_for_the_test(world, rules_v2):
    assert site_settings.read(world.db, world.society.id, "scheduler.rules_version") == 2
    lookup.invalidate()
    assert world.db.query(SocietySetting).filter_by(
        society_id=world.society.id, key="scheduler.rules_version").count() == 1


def test_rules_version_is_one_without_the_fixture(world, site_cfg):
    site_cfg({})  # seeds the global defaults, sets nothing
    assert site_settings.read(world.db, world.society.id, "scheduler.rules_version") == 1
