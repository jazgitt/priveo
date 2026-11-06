"""SCHS-20 follow-up: site.weekend_cutoff_flexible decides if a weekend day is strict."""
from datetime import date, timedelta

import pytest

from app.scheduling.solver.rules.job_cutoff import is_strict_day

THURSDAY = date(2026, 10, 22)
SATURDAY = THURSDAY + timedelta(days=2)


class Ctx:
    def __init__(self, active=True, flexible=True, hard=True):
        self.active = active
        self._s = {"site.weekday_cutoff_hard": hard, "site.weekend_cutoff_flexible": flexible,
                   "site.weekend_weekdays": [5, 6]}

    def setting(self, key):
        return self._s[key]


@pytest.mark.parametrize("flexible, weekday, weekend", [(True, True, False), (False, True, True)])
def test_SCHR_WKE_flag_states_on_a_weekday_and_a_weekend_day(flexible, weekday, weekend):
    ctx = Ctx(flexible=flexible)
    assert is_strict_day(ctx, THURSDAY) is weekday
    assert is_strict_day(ctx, SATURDAY) is weekend


def test_SCHR_WKE_version_1_and_the_weekday_switch_off_stay_soft():
    assert not is_strict_day(Ctx(active=False, flexible=False), SATURDAY)
    assert not is_strict_day(Ctx(flexible=False, hard=False), SATURDAY)
    assert not is_strict_day(Ctx(hard=False), THURSDAY)


def test_SCHR_WKE_a_weekend_job_that_misses_the_cutoff_is_unassigned_when_not_flexible(world, site_cfg):
    from datetime import time

    from app.scheduling.codes import ReasonCode
    from tests.scheduling.builders import Scenario
    site_cfg({"scheduler.rules_version": 2, "site.weekend_cutoff_flexible": False})
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.cars(2, cutoff=time(8, 30))
    res = sc.run(SATURDAY)
    assert len(res.placed) == 1 and not any(p.late for p in res.placed)
    assert res.unassigned[0].note == ReasonCode.CUSTOMER_CUTOFF.text
