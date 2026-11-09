"""SCHS-20 follow-up: site.weekend_cutoff_flexible decides if a weekend day is strict."""
from datetime import date, timedelta

import pytest

from app.scheduling.solver.rules.job_cutoff import is_strict_day

THURSDAY = date(2026, 10, 22)
SATURDAY = THURSDAY + timedelta(days=2)


class Ctx:
    def __init__(self, flexible=True, hard=True):
        self._s = {"site.weekday_cutoff_hard": hard, "site.weekend_cutoff_flexible": flexible,
                   "site.weekend_weekdays": [5, 6]}

    def setting(self, key):
        return self._s[key]


@pytest.mark.parametrize("flexible, weekday, weekend", [(True, True, False), (False, True, True)])
def test_SCHR_WKE_flag_states_on_a_weekday_and_a_weekend_day(flexible, weekday, weekend):
    ctx = Ctx(flexible=flexible)
    assert is_strict_day(ctx, THURSDAY) is weekday
    assert is_strict_day(ctx, SATURDAY) is weekend


def test_SCHR_WKE_the_weekday_switch_off_stays_soft():
    assert not is_strict_day(Ctx(flexible=False, hard=False), SATURDAY)
    assert not is_strict_day(Ctx(hard=False), THURSDAY)


def test_SCHR_WKE_a_weekend_exterior_that_misses_the_cutoff_is_placed_late_when_not_flexible(world, site_cfg):
    # A strict weekend day is strict for the Exterior too, but an Exterior is
    # protected (SCHR-CUT-09): the second car is placed late, not left out.
    from datetime import time

    from tests.scheduling.builders import Scenario
    site_cfg({"site.weekend_cutoff_flexible": False})
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.cars(2, cutoff=time(8, 30))
    res = sc.run(SATURDAY)
    assert len(res.placed) == 2 and [p.late for p in res.placed].count(True) == 1
    assert not res.unassigned
