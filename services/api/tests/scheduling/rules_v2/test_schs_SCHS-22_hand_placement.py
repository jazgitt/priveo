"""SCHS-22: a hand placement against a rule warns, needs a confirm and is flagged."""
from datetime import time, timedelta

from sqlalchemy import select

from app.scheduling.models import Job, ScheduleFinding, Visit
from tests.scheduling.builders import Scenario
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login

THURSDAY = SUNDAY + timedelta(days=4)
BASE = "/v1/admin/scheduling"


def _two_cars(world, day=SUNDAY, cutoff=None, n=2):
    sc = Scenario(world)
    sc.slots()
    cleaner = sc.cleaner(shift=(480, 600))
    sc.cars(n, cutoff=cutoff)
    sc.run(day)
    jobs = world.db.scalars(select(Job).order_by(Job.start_minute)).all()
    assert len(jobs) == n and all(j.crew_id for j in jobs)
    return cleaner, jobs


def _move(api, job, cleaner, start, **extra):
    admin = auth(login(api, "admin")["access_token"])
    return api.post(f"{BASE}/jobs/{job.id}/move", headers=admin,
                    json={"crew_id": str(cleaner.id), "start_minute": start, **extra})


def _hand_findings(world):
    world.db.expire_all()
    return sorted(f.code for f in world.db.scalars(select(ScheduleFinding)) if f.code.startswith("hand_"))


def test_SCHR_HIER_08_a_drop_against_a_rule_is_a_warning_not_a_refusal(api, world, rules_v2):
    cleaner, (one, two) = _two_cars(world)
    r = _move(api, two, cleaner, one.start_minute + 10)
    assert r.status_code == 409
    assert r.json()["code"] == "placement_warning"
    assert r.json()["fields"] == {"overlap": "That time overlaps another job."}
    world.db.refresh(two)
    assert two.start_minute != one.start_minute + 10 and _hand_findings(world) == []


def test_SCHR_HIER_08_after_confirm_the_job_moves_and_the_breach_is_stored(api, world, rules_v2):
    cleaner, (one, two) = _two_cars(world)
    r = _move(api, two, cleaner, one.start_minute + 10, override=True)
    assert r.status_code == 200, r.text
    assert r.json()["start_minute"] == one.start_minute + 10 and r.json()["manual"] is True
    assert _hand_findings(world) == ["hand_overlap"]
    finding = world.db.scalar(select(ScheduleFinding).where(ScheduleFinding.code == "hand_overlap"))
    assert finding.job_id == two.id and finding.detail == "That time overlaps another job."


def test_SCHR_HIER_08_outside_the_hours_all_breaches_are_listed_together(api, world, rules_v2):
    cleaner, (_one, two) = _two_cars(world)
    r = _move(api, two, cleaner, 60)
    assert r.status_code == 409 and r.json()["code"] == "placement_warning"
    assert set(r.json()["fields"]) == {"outside_hours", "outside_slot"}
    assert _move(api, two, cleaner, 60, override=True).status_code == 200
    assert _hand_findings(world) == ["hand_outside_hours", "hand_outside_slot"]


def test_SCHR_CUT_05_a_hand_placement_after_a_weekday_cutoff_warns_and_is_marked_late(api, world, rules_v2):
    cleaner, (two,) = _two_cars(world, day=THURSDAY, cutoff=time(8, 30), n=1)
    late_start = 8 * 60 + 30
    r = _move(api, two, cleaner, late_start)
    assert r.status_code == 409 and r.json()["code"] == "placement_warning"
    assert "customer_cutoff" in r.json()["fields"]
    r = _move(api, two, cleaner, late_start, override=True)
    assert r.status_code == 200 and r.json()["late"] is True
    assert "hand_customer_cutoff" in _hand_findings(world)


def test_SCHR_HIER_08_a_placement_that_breaks_nothing_needs_no_confirm_and_leaves_no_finding(api, world, rules_v2):
    cleaner, (one, two) = _two_cars(world)
    r = _move(api, two, cleaner, one.start_minute + 60)
    assert r.status_code == 200, r.text
    assert _hand_findings(world) == []


def test_SCHR_HIER_08_the_breach_survives_a_rerun_and_goes_when_the_job_is_taken_off(api, world, rules_v2):
    cleaner, (one, two) = _two_cars(world)
    assert _move(api, two, cleaner, one.start_minute + 10, override=True).status_code == 200
    Scenario(world).run(SUNDAY)  # the hand placement is kept, so is its finding
    assert _hand_findings(world) == ["hand_overlap"]
    admin = auth(login(api, "admin")["access_token"])
    r = api.post(f"{BASE}/jobs/{two.id}/move", headers=admin, json={})
    assert r.status_code == 200 and _hand_findings(world) == []


def test_SCHR_HIER_08_the_planner_itself_never_produces_such_a_placement(world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.cars(6)  # more work than the shift holds
    sc.run(SUNDAY)
    assert _hand_findings(world) == []
    placed = world.db.execute(select(Job.start_minute, Job.duration_minutes)
                              .where(Job.crew_id.is_not(None)).order_by(Job.start_minute)).all()
    assert all(a[0] + a[1] <= b[0] for a, b in zip(placed, placed[1:], strict=False))


def test_kill_switch_version_1_refuses_as_before(api, world):
    cleaner, (one, two) = _two_cars(world)
    r = _move(api, two, cleaner, one.start_minute + 10, override=True)
    assert r.status_code == 409 and r.json()["code"] == "overlap"
    assert _hand_findings(world) == []
    assert world.db.scalar(select(Visit.id).limit(1)) is not None
