"""SCHS-03: the solver is a core plus rule modules found in a folder.

The refactor is behaviour-neutral: 50 generated days give exactly the plans of
the old single-function solver (kept below as a reference), and a module dropped
into solver/rules/ is used with no other edit.
"""

import random
import sys
from pathlib import Path

from ortools.sat.python import cp_model

from app.scheduling.solver import (
    SolverCrew,
    SolverJob,
    SolverResult,
    registry,
    rules,
    solve_day,
)

# ---- reference: the solver as it was before SCHS-03 (do not edit) ----------
_STEP = 5
_PLACED = 1_000_000_000
_LATE = 10_000_000
_EARLY = 1


def _up(minutes: int) -> int:
    return -(-minutes // _STEP)


def ref_solve_day(crew: list[SolverCrew], jobs: list[SolverJob], max_seconds: float = 10.0) -> SolverResult:
    result = SolverResult()
    crew_by_key = {c.key: c for c in crew}
    free: list[SolverJob] = []
    kept: list[SolverJob] = []
    for job in jobs:
        if job.fixed is not None and job.fixed[0] in crew_by_key:
            result.placed[job.key] = job.fixed
            kept.append(job)
            if job.finish_by is not None and job.fixed[1] + job.duration > job.finish_by:
                result.late.add(job.key)
        else:
            free.append(job)

    if not free:
        return result
    if not crew:
        result.unplaced = {j.key: "No crew member works that day." for j in free}
        return result

    model = cp_model.CpModel()
    per_crew: dict[str, list] = {c.key: [] for c in crew}
    per_vehicle: dict[str, list] = {}
    objective = []

    for job in kept:
        crew_key, start = job.fixed
        interval = model.NewFixedSizeIntervalVar(start // _STEP, _up(job.duration), f"fix_{job.key}")
        per_crew[crew_key].append(interval)
        per_vehicle.setdefault(job.vehicle, []).append(interval)

    placed_vars: dict[str, object] = {}
    start_vars: dict[str, object] = {}
    late_vars: dict[str, object] = {}
    presence: dict[tuple[str, str], object] = {}

    for job in free:
        dur = _up(job.duration)
        allowed = job.windows if job.windows is not None else ((0, 1440),)
        domains = [[_up(s), e // _STEP - dur] for s, e in allowed if _up(s) + dur <= e // _STEP]
        if not domains:
            result.unplaced[job.key] = "No working slot allows this service that day."
            continue
        fits = [
            c for c in crew if any(max(_up(c.start), lo) + dur <= min(c.end // _STEP, hi + dur) for lo, hi in domains)
        ]
        if not fits:
            result.unplaced[job.key] = "No crew member's hours are long enough for this job."
            continue
        start = model.NewIntVarFromDomain(cp_model.Domain.FromIntervals(domains), f"s_{job.key}")
        start_vars[job.key] = start
        flags = []
        for c in fits:
            p = model.NewBoolVar(f"p_{job.key}_{c.key}")
            presence[(job.key, c.key)] = p
            flags.append(p)
            model.Add(start >= _up(c.start)).OnlyEnforceIf(p)
            model.Add(start + dur <= c.end // _STEP).OnlyEnforceIf(p)
            per_crew[c.key].append(model.NewOptionalFixedSizeIntervalVar(start, dur, p, f"i_{job.key}_{c.key}"))
        placed = model.NewBoolVar(f"placed_{job.key}")
        model.Add(sum(flags) == placed)
        placed_vars[job.key] = placed
        # One vehicle is not worked on by two crew members at the same time.
        per_vehicle.setdefault(job.vehicle, []).append(
            model.NewOptionalFixedSizeIntervalVar(start, dur, placed, f"v_{job.key}")
        )
        objective.append(_PLACED * job.duration * placed)
        objective.append(-_EARLY * start)
        if job.finish_by is not None:
            late = model.NewBoolVar(f"late_{job.key}")
            late_vars[job.key] = late
            model.Add(start + dur <= job.finish_by // _STEP).OnlyEnforceIf(late.Not())
            objective.append(-_LATE * late)

    for intervals in per_crew.values():
        model.AddNoOverlap(intervals)
    for intervals in per_vehicle.values():
        model.AddNoOverlap(intervals)
    model.Maximize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_seconds
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = 7
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for job in free:
            result.unplaced.setdefault(job.key, "The scheduler found no plan.")
        return result

    for job in free:
        if job.key in result.unplaced:
            continue
        if not solver.Value(placed_vars[job.key]):
            result.unplaced[job.key] = "Capacity is short for that day."
            continue
        crew_key = next(
            c.key for c in crew if (job.key, c.key) in presence and solver.Value(presence[(job.key, c.key)])
        )
        begin = solver.Value(start_vars[job.key]) * _STEP
        result.placed[job.key] = (crew_key, begin)
        if job.finish_by is not None and begin + job.duration > job.finish_by:
            result.late.add(job.key)
    return result


# ---- the corpus ----------------------------------------------------------------


def make_day(rng):
    crew = []
    for i in range(rng.randint(0, 3)):
        start = rng.choice([300, 330, 360])
        crew.append(SolverCrew(f"c{i}", start, start + rng.choice([60, 120, 180])))
    jobs = []
    vehicles = [f"v{i}" for i in range(rng.randint(2, 7))]
    for i in range(rng.randint(1, 9)):
        duration = rng.choice([20, 30, 30, 60, 120])
        finish_by = rng.choice([None, None, 360, 390, 420, 540])
        windows = rng.choice([None, None, ((300, 420), (480, 600)), ((420, 660),)])
        fixed = None
        if crew and rng.random() < 0.15:
            c = rng.choice(crew)
            fixed = (c.key, c.start + 5 * rng.randint(0, 6))
        jobs.append(SolverJob(f"j{i}", rng.choice(vehicles), duration, finish_by, fixed, windows))
    return crew, jobs


def test_fifty_generated_days_equal_the_old_solver():
    rng = random.Random(20261106)
    for day in range(50):
        crew, jobs = make_day(rng)
        old = ref_solve_day(crew, jobs)
        new = solve_day(crew, jobs)
        assert new.placed == old.placed, day
        assert new.unplaced == old.unplaced, day
        assert new.late == old.late, day


def test_imports_still_work_from_the_package():
    assert callable(solve_day) and SolverResult().placed == {}


def test_base_rule_is_found_first_and_order_is_deterministic():
    names = [r.name for r in registry.discover()]
    assert names[0] == "base"
    assert names == [r.name for r in registry.discover()]


def _expected(baseline, *dropped):
    """The folder's real modules plus the dropped (name, priority) ones, ordered
    by priority then name, so a new rule module does not break these tests."""
    prio = {r.name: r.priority for r in registry.discover() if r.name in baseline}
    items = [(p, n) for n, p in prio.items()] + [(p, n) for n, p in dropped]
    return [n for _, n in sorted(items)]


def test_a_module_dropped_in_the_folder_is_used(tmp_path):
    folder = Path(rules.__path__[0])
    baseline = [r.name for r in registry.discover()]
    path = folder / "zz_temp_rule.py"
    path.write_text(
        "NAME = 'zz_temp'\n"
        "PRIORITY = 50\n"
        "CALLS = []\n"
        "def add_job_terms(ctx, job):\n"
        "    CALLS.append(job.key)\n"
        "    # forbid starting this job before 07:00 (a constraint from the new file)\n"
        "    ctx.model.Add(ctx.start_vars[job.key] >= 420 // 5)\n"
        "def add_day_terms(ctx):\n"
        "    CALLS.append('day')\n"
    )
    try:
        names = [r.name for r in registry.discover()]
        assert names == _expected(baseline, ("zz_temp", 50))
        crew = [SolverCrew("a", 360, 600)]
        result = solve_day(crew, [SolverJob("j", "v", 20)])
        assert result.placed["j"] == ("a", 420)
        assert sys.modules["app.scheduling.solver.rules.zz_temp_rule"].CALLS == ["j", "day"]
    finally:
        path.unlink(missing_ok=True)
        sys.modules.pop("app.scheduling.solver.rules.zz_temp_rule", None)
    assert [r.name for r in registry.discover()] == baseline
    assert solve_day(crew, [SolverJob("j", "v", 20)]).placed["j"] == ("a", 360)


def test_underscore_modules_are_ignored():
    folder = Path(rules.__path__[0])
    baseline = [r.name for r in registry.discover()]
    path = folder / "_ignored.py"
    path.write_text("raise RuntimeError('must not be imported')\n")
    try:
        assert [r.name for r in registry.discover()] == baseline
    finally:
        path.unlink(missing_ok=True)


def test_order_is_by_priority_then_name():
    folder = Path(rules.__path__[0])
    baseline = [r.name for r in registry.discover()]
    made = []
    try:
        for name, prio in (("zz_b", 10), ("zz_a", 10), ("zz_c", 5)):
            p = folder / f"{name}.py"
            p.write_text(f"PRIORITY = {prio}\n")
            made.append((p, name))
        dropped = [(n, p) for n, p in (("zz_c", 5), ("zz_a", 10), ("zz_b", 10))]
        assert [r.name for r in registry.discover()] == _expected(baseline, *dropped)
    finally:
        for p, name in made:
            p.unlink(missing_ok=True)
            sys.modules.pop(f"app.scheduling.solver.rules.{name}", None)
