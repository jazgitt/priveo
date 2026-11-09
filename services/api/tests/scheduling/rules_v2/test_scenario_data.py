"""Scenario data tests: each test builds one named scenario (tests/scheduling/scenarios.py)
and checks the rules it carries. Rule IDs are in the test names and in
tests/scheduling/scenario_matrix.py."""
import pytest
from sqlalchemy import select

from app.scheduling import passes, service
from app.scheduling.breaks import effective_break
from app.scheduling.codes import ReasonCode
from app.scheduling.models import InteriorEntitlement, Job, Visit
from tests.scheduling import scenarios as s
from tests.scheduling.builders import INTERNAL, Scenario


def _sc(world):
    return Scenario(world)


def _job_rows(sc):
    """(job, visit) pairs of the site; the car is on the visit."""
    return sc.db.execute(select(Job, Visit).join(Visit, Visit.id == Job.visit_id)).all()


def _row(sc, car, week):
    return sc.db.scalar(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == car.id,
        InteriorEntitlement.service_week_start == week))


def test_schr_par_02_nothing_is_planned_on_the_weekly_off(world):
    sc = _sc(world)
    built = s.weekly_off_wednesday(sc)
    result = sc.run(*built["run"])
    wed = [p for p in result.placed if p.day == s.WEDNESDAY] + \
          [u for u in result.unassigned if u.day == s.WEDNESDAY]
    assert wed == []
    assert result.placed_on(s.TUESDAY) and result.placed_on(s.THURSDAY)


def test_schr_zone_03_home_zone_first_then_one_cross_zone_job_with_a_reason(world):
    sc = _sc(world)
    b = s.home_zones_absent_and_zoneless_car(sc)
    sc.run(*b["run"])
    crew_of = {v.vehicle_id: j.crew_id for j, v in _job_rows(sc) if j.crew_id is not None}
    by_car = {v.vehicle_id: j for j, v in _job_rows(sc) if j.crew_id is not None}
    # Asha takes one North car, Bina takes both South cars and the spilled North car.
    north_with_asha = [c for c in b["north"] if crew_of.get(c.id) == b["asha"].id]
    north_with_bina = [c for c in b["north"] if crew_of.get(c.id) == b["bina"].id]
    assert len(north_with_asha) == 1 and len(north_with_bina) == 1
    assert all(crew_of.get(c.id) == b["bina"].id for c in b["south"])
    # The spill is recorded; the zone-less car is never cross-zone (SCHR-ZONE-08).
    assert by_car[north_with_bina[0].id].cross_zone_reason
    assert by_car[b["loose"].id].cross_zone_reason is None
    assert b["loose"].id in crew_of
    # Chetan is sick: no job is his.
    assert b["chetan"].id not in crew_of.values()


def test_schr_brk_06_break_comes_from_the_most_specific_rule(world):
    sc = _sc(world)
    b = s.breaks_site_crew_and_date_range(sc)
    site = effective_break(sc.db, b["site"], b["monday"])
    crew = effective_break(sc.db, b["crew"], b["monday"])
    late = effective_break(sc.db, b["late"], b["monday"])
    tuesday = effective_break(sc.db, b["crew"], b["tuesday"])
    assert (site.start_minute, site.end_minute, site.source) == (570, 600, "site")
    assert (crew.start_minute, crew.end_minute, crew.source) == (660, 690, "date_crew")
    assert late is None  # the window starts after the break (SCHR-BRK-07)
    assert (tuesday.start_minute, tuesday.end_minute, tuesday.source) == (540, 570, "date")


def test_schr_zone_09_trainee_follows_the_member_and_adds_no_capacity(world):
    sc = _sc(world)
    b = s.trainee_follows_member(sc)
    result = sc.run(*b["run"])
    placed = result.placed_on(s.MONDAY)
    assert len(placed) == 3
    assert {p.crew_id for p in placed} == {b["member"].id}
    unplaced = [u for u in result.unassigned if u.day == s.MONDAY]
    assert len(unplaced) == 1 and unplaced[0].reason_code == ReasonCode.CAPACITY_SHORT


def test_schr_int_12_oldest_service_week_gets_the_one_interior(world):
    sc = _sc(world)
    b = s.interior_oldest_week_first(sc)
    result = sc.run(*b["run"])
    interiors = [p for p in result.placed if p.service == INTERNAL and p.day == s.TUESDAY]
    assert [p.vehicle_id for p in interiors] == [b["old"].id]
    assert interiors[0].duration == 30  # each Interior takes exactly 30 minutes (SCHR-INT-02)
    assert _row(sc, b["old"], s.WEEK1).status == "Planned"


@pytest.mark.xfail(strict=True, reason="Open: an Interior the planner could not place "
                   "keeps its ledger row as Planned; SCHR-CUT-03 and INT-21 say it stays owed "
                   "(Pending). Remove the marker when the link step leaves unplaced rows Pending.")
def test_schr_int_21_an_interior_left_unplaced_stays_pending(world):
    sc = _sc(world)
    b = s.interior_oldest_week_first(sc)
    sc.run(*b["run"])
    assert _row(sc, b["new"], s.WEEK2).status == "Pending"


def test_schr_wke_01_saturday_cutoff_is_late_not_lost(world):
    sc = _sc(world)
    b = s.weekend_cutoff_is_soft(sc)
    sat = sc.run(s.SATURDAY, 1)
    placed = [p for p in sat.placed_on(s.SATURDAY, car=b["car"])]
    assert len(placed) == 1 and placed[0].late
    assert sat.summary.late >= 1  # the lateness is counted in the run summary (SCHR-WKE-06)
    # Monday is a strict day: the Exterior is placed late, not left out (SCHR-CUT-09).
    mon = sc.run(s.MONDAY, 1)
    monday = mon.placed_on(s.MONDAY, car=b["car"])
    assert len(monday) == 1 and monday[0].late
    assert not [u for u in mon.unassigned if u.vehicle_id == b["car"].id]


def test_schr_cut_09_a_weekday_exterior_that_misses_its_cutoff_is_placed_late_and_flagged(world):
    sc = _sc(world)
    b = s.weekday_cutoff_is_hard(sc)
    result = sc.run(*b["run"])
    placed = result.placed_on(s.MONDAY, car=b["car"])
    assert len(placed) == 1 and placed[0].late
    assert not [u for u in result.unassigned if u.vehicle_id == b["car"].id]


def test_schr_hard_01_sick_leave_and_late_start_limit_the_crew(world):
    sc = _sc(world)
    b = s.sick_leave_and_late_start(sc)
    result = sc.run(*b["run"])
    placed = result.placed_on(s.MONDAY)
    assert len(placed) == 3
    assert {b["asha"].id, b["bina"].id}.isdisjoint({p.crew_id for p in placed})
    chetan_jobs = [p for p in placed if p.crew_id == b["chetan"].id]
    assert all(p.start >= 600 for p in chetan_jobs)


def test_schr_hier_08_hand_placement_past_cutoff_is_kept_and_flagged(world):
    sc = _sc(world)
    b = s.hand_placement_past_cutoff(sc)
    result = sc.run(*b["run"])
    placed = result.placed_on(s.MONDAY, car=b["car"])
    assert len(placed) == 1 and placed[0].manual
    assert placed[0].late  # the job is marked Late, as ADM-SCH-07 says


def test_schr_def_03_deferred_interior_goes_back_to_its_week(world):
    sc = _sc(world)
    b = s.deferred_interior_returns_to_pending(sc)
    service.set_job_status(sc.db, b["job"].id, "Deferred")
    sc.db.expire_all()
    row = sc.db.get(InteriorEntitlement, b["row"].id)
    assert row.status == "Pending" and row.service_week_start == s.WEEK1


def test_schr_ext_04_schr_ext_01_shortfall_serves_exteriors_first_and_reports_the_rest(world):
    sc = _sc(world)
    b = s.exterior_shortfall(sc)
    result = sc.run(*b["run"])
    day = result.placed_on(s.TUESDAY)
    exteriors = [p for p in day if p.service == passes.EXTERIOR]
    assert len(exteriors) == 2  # as many Exteriors as the window allows
    assert all(p.service != INTERNAL for p in day)  # the Interior waits behind the Exteriors
    short = [u for u in result.unassigned if u.day == s.TUESDAY and u.service == passes.EXTERIOR]
    assert [u.reason_code for u in short] == [ReasonCode.CAPACITY_SHORT]  # the shortfall is reported
    interior = [u for u in result.unassigned if u.day == s.TUESDAY and u.service == INTERNAL]
    assert [u.reason_code for u in interior] == [ReasonCode.CAPACITY_SHORT]


def test_schr_hard_13_a_window_too_short_for_the_job_is_reported(world):
    sc = _sc(world)
    b = s.shift_too_short(sc)
    result = sc.run(*b["run"])
    assert result.placed_on(s.TUESDAY, car=b["car"]) == []
    assert [u.reason_code for u in result.unassigned if u.day == s.TUESDAY] == [ReasonCode.SHIFT_TOO_SHORT]
