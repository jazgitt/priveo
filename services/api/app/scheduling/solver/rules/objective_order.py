"""Ordered objectives and weights from configuration (SCHR-PAR-15, SCHR-HIER-03
to 06).

Rule modules add their terms by objective name (`ctx.add_term`). At rules
version 2 the run's settings carry `scheduler.objective_order`, a comma list of
objective names, highest first, and this module solves one stage per objective:
it maximises the objective, fixes the best value it reached as a floor, and goes
on to the next one. So a lower objective never worsens a higher one, whatever
the weights. The weight of an objective (`scheduler.weight_<name>`) scales its
own terms only.

Without `scheduler.objective_order` in the settings (version 1, direct calls)
the terms are summed with their weights and solved once, as before.

Derived: an objective with terms that the order does not list runs after the
listed ones, by name. Tie-breaks of SCHR-HIER-06 beyond "earlier start" come
with the zone and FIFO stories.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext

NAME = "objective_order"
PRIORITY = 1000  # a helper module: it adds no terms of its own


def order_of(ctx: ModelContext) -> list[str] | None:
    """The objective names with terms, highest first; None for the single weighted solve."""
    raw = ctx.params.settings.get("scheduler.objective_order")
    if not raw:
        return None
    listed = [n.strip() for n in str(raw).split(",") if n.strip()]
    rest = sorted(n for n in ctx.terms if n not in listed)
    return [n for n in listed + rest if ctx.terms.get(n)]


def optimise(ctx: ModelContext):
    """Solve the model. Returns (status, solver)."""
    model, params = ctx.model, ctx.params
    names = order_of(ctx)
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = params.workers
    solver.parameters.random_seed = params.seed
    if names is None:
        model.Maximize(sum(ctx.objective))
        solver.parameters.max_time_in_seconds = params.max_seconds
        return solver.Solve(model), solver
    if not names:
        solver.parameters.max_time_in_seconds = params.max_seconds
        return solver.Solve(model), solver
    remaining = float(params.max_seconds)
    _greedy_hint(ctx)
    solver.parameters.repair_hint = True
    best = None
    for i, name in enumerate(names):
        stage = sum(ctx.weight(name) * t for t in ctx.terms[name])
        model.Maximize(stage)
        # The time left is shared by the stages that are still to run.
        solver.parameters.max_time_in_seconds = max(remaining / (len(names) - i), 0.01)
        status = solver.Solve(model)
        remaining -= solver.WallTime()
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # A later stage that finds no plan in its time keeps the plan of the
            # stage before; only the first stage can leave the day without a plan.
            return (cp_model.FEASIBLE, best) if best is not None else (status, solver)
        best = _Plan(ctx, solver)
        if i + 1 < len(names):
            model.Add(stage >= round(solver.ObjectiveValue()))
            model.ClearHints()
            for var, value in best.pairs:
                model.AddHint(var, value)
    return cp_model.FEASIBLE, best


class _Plan:
    """The values a stage found for the variables the core reads back, so a
    later stage that runs out of time cannot take the plan away."""

    def __init__(self, ctx: ModelContext, solver) -> None:
        groups = (ctx.start_vars, ctx.placed_vars, ctx.presence)
        self.pairs = [(v, solver.Value(v)) for g in groups for v in g.values()]
        self._by_id = {id(v): x for v, x in self.pairs}

    def Value(self, var) -> int:  # the solver's method name, as the core calls it
        return self._by_id[id(var)]


def _greedy_hint(ctx: ModelContext) -> None:
    """A first full plan for the solver to start from: each job, longest first,
    on the cleaner who is free earliest, at the first start its domain allows.
    Without it the first stage can spend its whole slice finding any plan on a
    day with many equal jobs. A hint never changes what is allowed."""
    step = ctx.params.step
    free_at = {c.key: -(-c.start // step) for c in ctx.crew}
    ends = {c.key: c.end // step for c in ctx.crew}
    for job in sorted(ctx.free, key=lambda j: (-ctx.durations.get(j.key, 0), j.key)):
        if job.key not in ctx.start_vars:
            continue
        dur = ctx.durations[job.key]
        allowed = job.windows if job.windows is not None else ((0, 1440),)
        domain: list[int] = []
        for s0, e0 in allowed:
            lo, hi = -(-s0 // step), e0 // step - dur
            if lo <= hi:
                domain += [lo, hi]
        if not domain:
            continue
        best = None  # (start, crew key)
        for c in ctx.crew:
            if (job.key, c.key) not in ctx.presence:
                continue
            for lo, hi in zip(domain[::2], domain[1::2], strict=True):
                begin = max(free_at[c.key], lo)
                if begin <= hi and begin + dur <= ends[c.key]:
                    if best is None or begin < best[0]:
                        best = (begin, c.key)
                    break
        for c in ctx.crew:
            if (job.key, c.key) in ctx.presence:
                ctx.model.AddHint(ctx.presence[(job.key, c.key)], int(best is not None and best[1] == c.key))
        ctx.model.AddHint(ctx.placed_vars[job.key], int(best is not None))
        ctx.model.AddHint(ctx.start_vars[job.key], best[0] if best else domain[0])
        if best is not None:
            free_at[best[1]] = best[0] + dur
