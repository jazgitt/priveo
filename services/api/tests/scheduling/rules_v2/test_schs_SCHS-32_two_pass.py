"""SCHS-32: each day is solved twice, Exteriors first, then Interiors in the gaps."""
from datetime import time, timedelta

from app.scheduling import passes
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, solve_day
from tests.scheduling.builders import EXTERNAL, INTERNAL, Scenario
from tests.scheduling.conftest import SUNDAY

EXT, INT = passes.EXTERIOR, "Cleaning-Internal"
SATURDAY = SUNDAY + timedelta(days=6)
MONDAY = SUNDAY + timedelta(days=1)


def _ext(key, duration=30, **kw):
    return SolverJob(key, f"v{key}", duration, service=EXT, **kw)


def _int(key, duration=30, **kw):
    return SolverJob(key, f"v{key}", duration, service=INT, **kw)


def test_schr_ext_03_all_exteriors_are_placed_before_any_interior_is_considered():
    # Room for two 30 minute jobs. The Interior is first in the list and has
    # the same size, yet both Exteriors win the room.
    crew = [SolverCrew("a", 480, 540)]
    result = passes.solve_passes(crew, [_int("i"), _ext("e1"), _ext("e2")])
    assert set(result.placed) == {"e1", "e2"} and set(result.unplaced) == {"i"}


def test_schr_wke_02_the_same_holds_on_a_weekend(world, site_cfg):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 540))
    ext_car, int_car = sc.car(interior_day="Saturday"), sc.car(interior_day="Saturday")
    res = sc.run(SATURDAY)
    assert {p.service for p in res.placed} == {EXTERNAL}
    assert len(res.placed) == 2 and {u.service for u in res.unassigned} == {INTERNAL}
    assert ext_car and int_car


def test_schr_hier_07_pass_b_receives_pass_a_as_fixed_jobs():
    seen = []
    import app.scheduling.passes as module
    real = module.solve_day

    def spy(crew, jobs, params=None, pass_name="single", inputs=None):
        seen.append((pass_name, {j.key: j.fixed for j in jobs}))
        return real(crew, jobs, params, pass_name, inputs)

    module.solve_day = spy
    try:
        crew = [SolverCrew("a", 480, 600)]
        result = passes.solve_passes(crew, [_ext("e"), _int("i")])
    finally:
        module.solve_day = real
    assert [name for name, _ in seen] == ["exterior", "interior"]
    assert seen[0][1] == {"e": None}
    assert seen[1][1]["e"] == result.placed["e"] and seen[1][1]["i"] is None
    assert result.placed["e"][1] < result.placed["i"][1] or result.placed["e"][0] != result.placed["i"][0]


def test_schr_int_08_an_interior_goes_to_a_cleaner_who_is_free_while_another_does_exteriors():
    crew = [SolverCrew("a", 480, 600), SolverCrew("b", 480, 600)]
    jobs = [_ext("e1", 60), _ext("e2", 60), _int("i", 30)]
    result = passes.solve_passes(crew, jobs)
    assert not result.unplaced
    # Both cleaners are busy 08:00 to 09:00 with Exteriors only if each took one;
    # the Interior starts while another Exterior may still run.
    assert result.placed["i"][1] < 600 - 30 + 1
    starts = sorted(t for _, t in result.placed.values())
    assert starts[0] == 480


def test_schr_int_07_interiors_take_the_gaps_between_exteriors():
    crew = [SolverCrew("a", 480, 600)]
    fixed = _ext("e", 30, fixed=("a", 480))
    result = passes.solve_passes(crew, [fixed, _int("i1"), _int("i2"), _int("i3")])
    assert result.placed["e"] == ("a", 480)
    assert sorted(result.placed[k][1] for k in ("i1", "i2", "i3")) == [510, 540, 570]


def test_schr_int_09_pass_b_respects_cutoffs_and_existing_assignments():
    crew = [SolverCrew("a", 480, 600)]
    jobs = [_ext("e", 60), _int("i", 30, finish_by=540, hard_cutoff=True)]
    result = passes.solve_passes(crew, jobs)
    assert result.placed["e"] == ("a", 480)
    assert "i" in result.unplaced  # the only gap before 09:00 is taken


def test_schr_hier_02_hard_constraints_hold_and_the_unplaced_are_reported():
    crew = [SolverCrew("a", 480, 510)]
    result = passes.solve_passes(crew, [_ext("e1"), _ext("e2"), _int("i")])
    assert len(result.placed) == 1
    assert set(result.unplaced) == {"e2", "i"} or set(result.unplaced) == {"e1", "i"}
    assert set(result.unplaced_codes) == set(result.unplaced)


def test_schr_hier_01_runs_two_passes_with_each_pass_named(world, site_cfg, monkeypatch):
    names = []
    real = passes.solve_day
    monkeypatch.setattr(
        passes, "solve_day", lambda c, j, p=None, n="single", i=None: names.append(n) or real(c, j, p, n, i)
    )
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 720))
    sc.car(interior_day="Monday", cutoff=time(11, 0))
    res = sc.run(MONDAY)
    assert names == ["exterior", "interior"] and len(res.placed) == 2


def test_the_time_limit_applies_to_each_pass():
    seen = []
    import app.scheduling.passes as module
    real = module.solve_day
    module.solve_day = lambda c, j, p=None, n="single", i=None: seen.append(p.max_seconds) or real(c, j, p, n, i)
    try:
        passes.solve_passes([SolverCrew("a", 480, 600)], [_ext("e"), _int("i")], SolverParams(max_seconds=3))
    finally:
        module.solve_day = real
    assert seen == [3, 3]


def test_single_pass_is_unchanged_for_jobs_without_a_service():
    crew = [SolverCrew("a", 480, 600)]
    jobs = [SolverJob("x", "v1", 30), SolverJob("y", "v2", 30)]
    assert set(solve_day(crew, jobs).placed) == {"x", "y"}
