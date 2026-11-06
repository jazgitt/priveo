"""SCHS-17: Interior job windows start no earlier than the site's Interior-earliest
time, every day; Exterior is untouched; only at rules version 2."""
from datetime import timedelta

import pytest

from app.directory import lookup, rule_seed, site_settings
from app.directory.models import WorkingSlot
from app.scheduling import windows
from tests.scheduling.conftest import SUNDAY

INTERIOR = "Cleaning-Internal"
EXTERIOR = "Cleaning-External"
WEEK = [SUNDAY + timedelta(days=i) for i in range(7)]  # weekdays and the weekend


def _site(world, version=2, earliest=None, start=300, end=660):
    for name in (INTERIOR, EXTERIOR):
        world.db.add(WorkingSlot(society_id=world.society.id, service=name,
                                 start_minute=start, end_minute=end, days=list(range(7))))
    world.db.commit()
    rule_seed.seed_rule_keys(world.db)
    site_settings.write(world.db, world.society.id, "scheduler.rules_version", version, None)
    if earliest is not None:
        site_settings.write(world.db, world.society.id,
                            "site.interior_earliest_minute", earliest, None)
    lookup.invalidate()


def _w(world, name, day):
    return windows.job_windows(world.db, world.society.id, name, day)


@pytest.mark.parametrize("day", WEEK)
def test_schr_par_08_interior_starts_at_07_00_on_every_day(world, day):
    _site(world)
    assert tuple(_w(world, INTERIOR, day)) == ((420, 660),)


@pytest.mark.parametrize("day", WEEK)
def test_schr_hard_05_no_interior_window_starts_before_the_earliest_time(world, day):
    _site(world)
    assert all(s >= 420 for s, _ in _w(world, INTERIOR, day))


def test_schr_int_03_the_time_comes_from_the_site_setting_not_a_literal(world):
    _site(world, earliest=480)
    assert tuple(_w(world, INTERIOR, SUNDAY)) == ((480, 660),)


def test_schr_int_03_a_window_ending_before_the_earliest_time_is_dropped(world):
    _site(world, start=300, end=400)
    assert not _w(world, INTERIOR, SUNDAY)


def test_schr_ext_08_exterior_keeps_the_early_band(world):
    _site(world)
    assert tuple(_w(world, EXTERIOR, SUNDAY)) == ((300, 660),)


def test_schr_par_08_at_rules_version_1_nothing_changes(world):
    _site(world, version=1)
    assert tuple(_w(world, INTERIOR, SUNDAY)) == ((300, 660),)


def test_schr_par_08_without_the_version_setting_nothing_changes(world):
    world.db.add(WorkingSlot(society_id=world.society.id, service=INTERIOR,
                             start_minute=300, end_minute=660, days=list(range(7))))
    world.db.commit()
    assert tuple(_w(world, INTERIOR, SUNDAY)) == ((300, 660),)
