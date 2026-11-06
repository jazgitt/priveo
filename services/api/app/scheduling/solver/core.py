"""The scheduler as a pure function (ADM-SCH-02 to ADM-SCH-08).

One day, one society at a time. Jobs with a `fixed` placement (made by hand, or
already frozen) are kept and take up their crew member's time; the rest are
placed to use as much of the crew's time as possible. A job that cannot meet
its finish-by time is still placed when it fits, and flagged late; a job that
fits nowhere is returned as unplaced with a reason.

The model is built here; the objective terms and extra constraints come from
the rule modules in `solver/rules/`, found by `solver.registry`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from app.scheduling.codes import ReasonCode
from app.scheduling.solver.registry import discover
from app.scheduling.solver.rules.base import MAX_SECONDS, SEED, STEP, WORKERS
from app.scheduling.solver.rules.job_cutoff import cutoff_blocks


@dataclass(frozen=True)
class SolverCrew:
    key: str
    start: int  # minutes after midnight
    end: int


@dataclass(frozen=True)
class SolverJob:
    key: str
    vehicle: str
    duration: int
    finish_by: int | None = None
    fixed: tuple[str, int] | None = None  # (crew key, start minute)
    windows: tuple[tuple[int, int], ...] | None = None
    hard_cutoff: bool = False  # finish_by is a hard limit (SCHS-19)


@dataclass
class SolverResult:
    placed: dict[str, tuple[str, int]] = field(default_factory=dict)
    unplaced: dict[str, str] = field(default_factory=dict)  # job key -> human text
    unplaced_codes: dict[str, ReasonCode] = field(default_factory=dict)  # job key -> code
    late: set[str] = field(default_factory=set)


def _unplace(result: SolverResult, key: str, code: ReasonCode) -> None:
    result.unplaced[key] = code.text
    result.unplaced_codes[key] = code


@dataclass
class ModelContext:
    """What a rule module sees while the model is built."""

    model: cp_model.CpModel
    crew: list[SolverCrew]
    free: list[SolverJob]
    kept: list[SolverJob]
    per_crew: dict[str, list] = field(default_factory=dict)
    per_vehicle: dict[str, list] = field(default_factory=dict)
    objective: list = field(default_factory=list)
    placed_vars: dict[str, object] = field(default_factory=dict)
    start_vars: dict[str, object] = field(default_factory=dict)
    late_vars: dict[str, object] = field(default_factory=dict)
    presence: dict[tuple[str, str], object] = field(default_factory=dict)
    durations: dict[str, int] = field(default_factory=dict)  # in grid steps


def _up(minutes: int) -> int:
    return -(-minutes // STEP)


def solve_day(crew: list[SolverCrew], jobs: list[SolverJob], max_seconds: float = MAX_SECONDS) -> SolverResult:
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
        for j in free:
            _unplace(result, j.key, ReasonCode.NO_CLEANER)
        return result

    model = cp_model.CpModel()
    ctx = ModelContext(model=model, crew=crew, free=free, kept=kept)
    ctx.per_crew = {c.key: [] for c in crew}
    per_crew = ctx.per_crew
    per_vehicle = ctx.per_vehicle
    rules = discover()

    for job in kept:
        crew_key, start = job.fixed
        interval = model.NewFixedSizeIntervalVar(start // STEP, _up(job.duration), f"fix_{job.key}")
        per_crew[crew_key].append(interval)
        per_vehicle.setdefault(job.vehicle, []).append(interval)

    for job in free:
        dur = _up(job.duration)
        allowed = job.windows if job.windows is not None else ((0, 1440),)
        domains = [[_up(s), e // STEP - dur] for s, e in allowed if _up(s) + dur <= e // STEP]
        if not domains:
            _unplace(result, job.key, ReasonCode.NO_SLOT)
            continue
        fits = [
            c for c in crew if any(max(_up(c.start), lo) + dur <= min(c.end // STEP, hi + dur) for lo, hi in domains)
        ]
        if not fits:
            _unplace(result, job.key, ReasonCode.SHIFT_TOO_SHORT)
            continue
        start = model.NewIntVarFromDomain(cp_model.Domain.FromIntervals(domains), f"s_{job.key}")
        ctx.start_vars[job.key] = start
        ctx.durations[job.key] = dur
        flags = []
        for c in fits:
            p = model.NewBoolVar(f"p_{job.key}_{c.key}")
            ctx.presence[(job.key, c.key)] = p
            flags.append(p)
            model.Add(start >= _up(c.start)).OnlyEnforceIf(p)
            model.Add(start + dur <= c.end // STEP).OnlyEnforceIf(p)
            per_crew[c.key].append(model.NewOptionalFixedSizeIntervalVar(start, dur, p, f"i_{job.key}_{c.key}"))
        placed = model.NewBoolVar(f"placed_{job.key}")
        model.Add(sum(flags) == placed)
        ctx.placed_vars[job.key] = placed
        # One vehicle is not worked on by two crew members at the same time.
        per_vehicle.setdefault(job.vehicle, []).append(
            model.NewOptionalFixedSizeIntervalVar(start, dur, placed, f"v_{job.key}")
        )
        for rule in rules:
            rule.add_job_terms(ctx, job)

    for rule in rules:
        rule.add_day_terms(ctx)
    for intervals in per_crew.values():
        model.AddNoOverlap(intervals)
    for intervals in per_vehicle.values():
        model.AddNoOverlap(intervals)
    model.Maximize(sum(ctx.objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_seconds
    solver.parameters.num_workers = WORKERS
    solver.parameters.random_seed = SEED
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for job in free:
            if job.key not in result.unplaced:
                _unplace(result, job.key, ReasonCode.NO_PLAN)
        return result

    for job in free:
        if job.key in result.unplaced:
            continue
        if not solver.Value(ctx.placed_vars[job.key]):
            _unplace(result, job.key, ReasonCode.CUSTOMER_CUTOFF if cutoff_blocks(job) else ReasonCode.CAPACITY_SHORT)
            continue
        crew_key = next(
            c.key for c in crew if (job.key, c.key) in ctx.presence and solver.Value(ctx.presence[(job.key, c.key)])
        )
        begin = solver.Value(ctx.start_vars[job.key]) * STEP
        result.placed[job.key] = (crew_key, begin)
        if job.finish_by is not None and begin + job.duration > job.finish_by:
            result.late.add(job.key)
    return result
