"""SCHS-34: capacity subtracts the break and shows the free early band
(SCHR-BRK-08, SCHR-EXT-09). Version 2 only."""
from types import SimpleNamespace

from app.directory import lookup, rule_seed, site_settings
from app.directory.models import WorkingSlot
from app.scheduling import capacity
from app.scheduling.capacity_lines import early_band
from app.scheduling.models import BreakRule
from tests.scheduling.conftest import SUNDAY

SERVICES = ["Cleaning-External", "Cleaning-Internal", "Deep Spa"]


def _site(world, version=2, start=300, end=660):
    member = world.add_crew(start=start, end=end)
    for name in SERVICES:
        world.db.add(WorkingSlot(society_id=world.society.id, service=name,
                                 start_minute=start, end_minute=end, days=list(range(7))))
    world.db.commit()
    rule_seed.seed_rule_keys(world.db)
    site_settings.write(world.db, world.society.id, "scheduler.rules_version", version, None)
    lookup.invalidate()
    return member



def _day(world):
    return capacity.capacity(world.db, world.society.id, SUNDAY, SUNDAY)[0]


def test_schr_brk_08_capacity_is_the_windows_minus_the_break(world):
    _site(world)  # 05:00 to 11:00 with a 09:30 to 10:00 break; first job at 05:30
    day = _day(world)
    assert day["break_minutes"] == 30
    assert day["capacity_minutes"] == (660 - 330) - 30
    assert day["crew"][0]["minutes"] == day["capacity_minutes"]
    assert day["crew"][0]["slots"] == "05:30-09:30, 10:00-11:00"


def test_schr_brk_08_a_cleaner_without_a_break_loses_nothing(world, site_cfg):
    _site(world)
    site_cfg(site_break_enabled=False)
    day = _day(world)
    assert day["break_minutes"] == 0 and day["capacity_minutes"] == 330


def test_schr_brk_08_a_date_rule_with_no_break_removes_the_deduction(world):
    _site(world)
    world.db.add(BreakRule(society_id=world.society.id, crew_id=None, start_date=SUNDAY,
                           end_date=SUNDAY, enabled=False))
    world.db.commit()
    assert _day(world)["break_minutes"] == 0


def test_schr_brk_07_a_shift_that_ends_before_the_break_has_none_to_take_out(world):
    _site(world, end=540)
    day = _day(world)
    assert day["break_minutes"] == 0 and day["capacity_minutes"] == 540 - 330


def test_schr_ext_09_free_early_band_minutes_are_shown(world):
    _site(world)
    # The band is 05:30 to 07:00 by default: 90 free minutes, one cleaner.
    assert _day(world)["early_band_free_minutes"] == 90


def test_schr_ext_09_busy_minutes_and_the_break_are_not_free():
    ctx = SimpleNamespace(windows={}, crew={}, busy={})
    assert early_band._free((330, 660), (330, 420), [(330, 360), (350, 380)]) == 40
    assert early_band._free((400, 660), (330, 420), []) == 20
    assert early_band._free((430, 660), (330, 420), []) == 0
    assert ctx.windows == {}


def test_schr_ext_09_nothing_changes_at_rules_version_1(world):
    _site(world, version=1)
    day = _day(world)
    assert day["break_minutes"] == 0 and day["early_band_free_minutes"] == 0
    assert day["capacity_minutes"] == 660 - 300
