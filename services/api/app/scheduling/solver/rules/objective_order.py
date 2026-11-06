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
    status = cp_model.UNKNOWN
    for i, name in enumerate(names):
        stage = sum(ctx.weight(name) * t for t in ctx.terms[name])
        model.Maximize(stage)
        # The time left is shared by the stages that are still to run.
        solver.parameters.max_time_in_seconds = max(remaining / (len(names) - i), 0.01)
        status = solver.Solve(model)
        remaining -= solver.WallTime()
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return status, solver
        if i + 1 < len(names):
            model.Add(stage >= round(solver.ObjectiveValue()))
            model.ClearHints()
            for group in (ctx.start_vars, ctx.placed_vars, ctx.presence):
                for var in group.values():
                    model.AddHint(var, solver.Value(var))
    return status, solver
