"""SCHS-25: grid step, time limit, seed and workers come from settings."""
import inspect
import re
import uuid

from ortools.sat.python import cp_model

from app.directory import settings_registry
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, core, solve_day
from app.scheduling.solver.rules import base


def test_defaults_equal_the_registry_values_and_the_old_constants():
    p = SolverParams()
    assert (p.step, p.max_seconds, p.seed, p.workers) == (5, 10.0, 7, 1)
    for key, want in (("scheduler.grid_minutes", p.step), ("scheduler.solve_seconds", p.max_seconds),
                      ("scheduler.seed", p.seed), ("scheduler.workers", p.workers)):
        assert float(settings_registry.default_for(key)) == want


def test_no_literal_constants_remain_in_the_solver():
    for name in ("STEP", "MAX_SECONDS", "SEED", "WORKERS"):
        assert not hasattr(base, name)
    code = re.sub(r'""".*?"""', "", inspect.getsource(core), flags=re.S)
    assert not re.search(r"\b(10\.0|7)\b", code)
    assert not re.search(r"random_seed = \d|num_workers = \d|// 5\b|\* 5\b", code)


def test_grid_step_sets_the_start_times():
    crew = [SolverCrew("c", 360, 600)]
    jobs = [SolverJob("a", "v1", 30, windows=((363, 600),))]
    assert solve_day(crew, jobs, SolverParams(step=5)).placed["a"][1] % 5 == 0
    start = solve_day(crew, jobs, SolverParams(step=15)).placed["a"][1]
    assert start % 15 == 0 and start == 375


def test_solver_receives_time_limit_seed_and_workers(monkeypatch):
    seen = {}
    real = cp_model.CpSolver

    class Spy(real):
        def Solve(self, model, *a, **k):
            p = self.parameters
            seen.update(t=p.max_time_in_seconds, s=p.random_seed, w=p.num_workers)
            return super().Solve(model, *a, **k)

    monkeypatch.setattr(core.cp_model, "CpSolver", Spy)
    solve_day([SolverCrew("c", 360, 600)], [SolverJob("a", "v", 30)], SolverParams(max_seconds=3, seed=99, workers=2))
    assert seen == {"t": 3, "s": 99, "w": 2}


def test_seed_changes_tie_breaks_only():
    crew = [SolverCrew("c1", 360, 720), SolverCrew("c2", 360, 720)]
    jobs = [SolverJob(f"j{i}", f"v{i}", 30) for i in range(6)]
    plans = [solve_day(crew, jobs, SolverParams(seed=s)) for s in (1, 7, 12345)]
    for r in plans:
        assert set(r.placed) == {j.key for j in jobs} and not r.unplaced and not r.late
    starts = [sorted(t for _, t in r.placed.values()) for r in plans]
    assert starts[0] == starts[1] == starts[2]


def test_load_reads_the_settings(db):
    from app.directory.service import save_settings
    save_settings(db, None, {"scheduler.grid_minutes": 10, "scheduler.seed": 3})
    p = SolverParams.load(db, uuid.uuid4())  # no site value: the stored global one
    assert (p.step, p.seed, p.max_seconds, p.workers) == (10, 3, 10.0, 1)
