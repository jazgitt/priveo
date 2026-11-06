"""SCHS-44: home zone first, other zones into spare capacity, fewest zone switches."""
from datetime import timedelta

from app.scheduling import passes
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, solve_day
from tests.scheduling.builders import Scenario
from tests.scheduling.conftest import SUNDAY

EXT = passes.EXTERIOR
ORDER = "placed,zone,break,fifo,late,early_capacity,early"
MONDAY = SUNDAY + timedelta(days=1)


def _params():
    return SolverParams(settings={"scheduler.objective_order": ORDER})


def _job(key, zone, **kw):
    return SolverJob(key, f"v{key}", 30, service=EXT, **kw), (f"v{key}", zone)


def _solve(crew, specs, home, allowed=True, owned=None):
    jobs = [s[0] for s in specs]
    data = {
        "home": home, "vehicle_zone": {v: z for _j, (v, z) in specs if z},
        "owned": sorted(owned if owned is not None else {z for z in home.values() if z}),
        "cross_allowed": allowed,
    }
    return solve_day(crew, jobs, _params(), "exterior", {"zones": data})


def test_schr_zone_03_home_zone_jobs_go_to_their_own_cleaner():
    crew = [SolverCrew("a", 360, 480), SolverCrew("b", 360, 480)]
    specs = [_job("a1", "Z1"), _job("a2", "Z1"), _job("b1", "Z2"), _job("b2", "Z2")]
    result = _solve(crew, specs, {"a": "Z1", "b": "Z2"})
    assert {k: result.placed[k][0] for k in result.placed} == {"a1": "a", "a2": "a", "b1": "b", "b2": "b"}


def test_schr_zone_03_a_cleaner_takes_other_zone_work_into_spare_capacity():
    crew = [SolverCrew("a", 360, 480), SolverCrew("b", 360, 420)]  # b has one hour
    specs = [_job(f"a{i}", "Z1") for i in range(5)] + [_job("b1", "Z2")]
    result = _solve(crew, specs, {"a": "Z1", "b": "Z2"})
    assert len(result.placed) == 6  # a fits four Z1 jobs, b takes the fifth after its own
    assert result.placed["b1"][0] == "b"
    assert sum(1 for k, (c, _s) in result.placed.items() if k.startswith("a") and c == "b") == 1


def test_schr_zone_04_spill_never_pushes_a_home_job_past_its_hard_cutoff():
    crew = [SolverCrew("a", 360, 480), SolverCrew("b", 360, 420)]
    home = [_job("b1", "Z2", finish_by=390, hard_cutoff=True), _job("b2", "Z2", finish_by=420, hard_cutoff=True)]
    spill = [_job(f"a{i}", "Z1") for i in range(5)]
    result = _solve(crew, home + spill, {"a": "Z1", "b": "Z2"})
    assert result.placed["b1"][0] == "b" and result.placed["b2"][0] == "b"
    assert not result.late
    assert "b1" not in result.unplaced and "b2" not in result.unplaced
    assert len(result.placed) == 6  # a's four slots and b's two home jobs; the fifth spill job stays open


def test_schr_zone_04_cross_zone_help_off_keeps_cleaners_in_their_zone():
    crew = [SolverCrew("a", 360, 420), SolverCrew("b", 360, 480)]
    specs = [_job(f"a{i}", "Z1") for i in range(3)]  # 3 jobs; a fits 2, b is idle
    on = _solve(crew, specs, {"a": "Z1", "b": "Z2"})
    off = _solve(crew, specs, {"a": "Z1", "b": "Z2"}, allowed=False)
    assert len(on.placed) == 3
    assert len(off.placed) == 2 and all(c == "a" for c, _s in off.placed.values())


def test_schr_zone_07_a_zone_nobody_owns_is_served_as_cross_zone_work():
    crew = [SolverCrew("a", 360, 480)]
    result = _solve(crew, [_job("x", "Z9")], {"a": "Z1"}, allowed=False, owned={"Z1"})
    assert "x" in result.placed


def test_schr_zone_08_cars_without_a_zone_go_to_any_cleaner():
    crew = [SolverCrew("a", 360, 390), SolverCrew("b", 360, 480)]
    result = _solve(crew, [_job("n1", None), _job("n2", None), _job("n3", None)], {"a": "Z1", "b": "Z2"},
                    allowed=False)
    assert len(result.placed) == 3


def test_schr_zone_11_no_home_zones_plans_as_today():
    crew = [SolverCrew("a", 360, 480)]
    jobs = [SolverJob(f"j{i}", f"v{i}", 30, service=EXT) for i in range(3)]
    plain = solve_day(crew, jobs, _params(), "exterior", {})
    with_none = solve_day(crew, jobs, _params(), "exterior", {"zones": None})
    assert plain.placed == with_none.placed


def test_schr_zone_02_a_cleaner_works_one_zone_at_a_time():
    crew = [SolverCrew("a", 360, 480)]
    specs = [_job("p1", "Z1"), _job("q1", "Z2"), _job("p2", "Z1"), _job("q2", "Z2")]
    result = _solve(crew, specs, {"a": None}, owned=set())
    order = [k[0] for k, _ in sorted(result.placed.items(), key=lambda kv: kv[1][1])]
    switches = sum(1 for x, y in zip(order, order[1:], strict=False) if x != y)
    assert switches == 1


def test_schr_ext_10_equal_plans_prefer_fewer_zone_changes():
    crew = [SolverCrew("a", 360, 420), SolverCrew("b", 360, 420)]
    specs = [_job("p1", "Z1"), _job("p2", "Z1"), _job("q1", "Z2"), _job("q2", "Z2")]
    result = _solve(crew, specs, {"a": None, "b": None}, owned=set())
    zones = {}
    for key, (c, _s) in result.placed.items():
        zones.setdefault(c, set()).add(key[0])
    assert all(len(z) == 1 for z in zones.values())


def test_schr_zone_05_no_travel_minutes_are_added():
    crew = [SolverCrew("a", 360, 480)]
    specs = [_job("p1", "Z1"), _job("q1", "Z2"), _job("p2", "Z1"), _job("q2", "Z2")]
    result = _solve(crew, specs, {"a": None}, owned=set())
    assert sorted(s for _c, s in result.placed.values()) == [360, 390, 420, 450]


def test_schr_zone_10_a_run_with_home_zones_fills_the_home_zone_first(world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Asha", shift=(360, 600), zone="Z1")
    sc.cleaner("Bala", shift=(360, 600), zone="Z2")
    cars = [sc.car(zone="Z1") for _ in range(2)] + [sc.car(zone="Z2") for _ in range(2)]
    res = sc.run(MONDAY)
    by_car = {p.vehicle_id: p.crew_id for p in res.placed}
    assert by_car[cars[0].id] == by_car[cars[1].id] == sc.cleaners["Asha"].id
    assert by_car[cars[2].id] == by_car[cars[3].id] == sc.cleaners["Bala"].id


def test_schr_zone_11_a_site_with_no_home_zones_records_no_cross_zone_job(world, rules_v2):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Asha", shift=(360, 600))
    sc.car(zone="Z1")
    res = sc.run(MONDAY)
    assert len(res.placed) == 1
    assert res.summary.cross_zone_jobs == 0
