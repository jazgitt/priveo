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
from typing import Any

from ortools.sat.python import cp_model

from app.directory import settings_registry
from app.scheduling.codes import ReasonCode
from app.scheduling.solver.registry import discover
from app.scheduling.solver.rules.job_cutoff import cutoff_blocks
from app.scheduling.solver.rules.objective_order import optimise


def _default(key: str) -> int:
    return int(settings_registry.default_for(key))


@dataclass(frozen=True)
class SolverParams:
    """Grid step, time limit, seed and workers (SCHS-25). The defaults are the
    registry defaults, so a caller that passes nothing plans as before."""

    step: int = field(default_factory=lambda: _default("scheduler.grid_minutes"))
    max_seconds: float = field(default_factory=lambda: float(_default("scheduler.solve_seconds")))
    seed: int = field(default_factory=lambda: _default("scheduler.seed"))
    workers: int = field(default_factory=lambda: _default("scheduler.workers"))
    # The run's settings snapshot (version 2 only; empty at version 1). Rule
    # modules read weights, the objective order and times from it (SCHS-33).
    settings: dict[str, Any] = field(default_factory=dict, compare=False)

    @classmethod
    def load(cls, db) -> SolverParams:
        """The global settings, read through the lookup."""
        from app.directory import lookup

        return cls(
            step=int(lookup.setting(db, "scheduler.grid_minutes")),
            max_seconds=float(lookup.setting(db, "scheduler.solve_seconds")),
            seed=int(lookup.setting(db, "scheduler.seed")),
            workers=int(lookup.setting(db, "scheduler.workers")),
        )


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
    service: str = ""  # the job's service; the passes split on it (SCHS-32)


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
    params: SolverParams = field(default_factory=SolverParams)
    pass_name: str = "single"  # single | exterior | interior (SCHS-32)
    inputs: dict[str, Any] = field(default_factory=dict)  # per rule module, by NAME
    terms: dict[str, list] = field(default_factory=dict)  # objective name -> terms

    def weight(self, name: str) -> int:
        """The weight of an objective: the run's setting, else the registry default."""
        key = f"scheduler.weight_{name}"
        value = self.params.settings.get(key)
        return int(_default(key) if value is None else value)

    def add_term(self, name: str, expr) -> None:
        """Add a term to a named objective. The flat objective gets it times the
        weight (the single weighted solve of version 1); the ordered solve of
        version 2 takes the terms by name (`rules/objective_order.py`)."""
        self.terms.setdefault(name, []).append(expr)
        self.objective.append(self.weight(name) * expr)


def solve_day(
    crew: list[SolverCrew],
    jobs: list[SolverJob],
    params: SolverParams | None = None,
    pass_name: str = "single",
    inputs: dict[str, Any] | None = None,
) -> SolverResult:
    params = params or SolverParams()
    STEP = params.step

    def _up(minutes: int) -> int:
        return -(-minutes // STEP)

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
    ctx = ModelContext(
        model=model, crew=crew, free=free, kept=kept, params=params, pass_name=pass_name, inputs=inputs or {}
    )
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
    status, solver = optimise(ctx)
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
