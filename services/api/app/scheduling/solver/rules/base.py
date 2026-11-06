"""The base objective: capacity use first, then the cutoff, then earlier starts.

The terms and constants are unchanged from the single-function solver.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext, SolverJob

NAME = "base"
PRIORITY = 0

_PLACED = 1_000_000_000  # per minute of work placed: capacity use comes first
_LATE = 10_000_000  # then meeting the cutoff times
_EARLY = 1  # then earlier starts


def add_job_terms(ctx: ModelContext, job: SolverJob) -> None:
    model = ctx.model
    placed = ctx.placed_vars[job.key]
    start = ctx.start_vars[job.key]
    dur = ctx.durations[job.key]
    ctx.objective.append(_PLACED * job.duration * placed)
    ctx.objective.append(-_EARLY * start)
    if job.finish_by is not None:
        late = model.NewBoolVar(f"late_{job.key}")
        ctx.late_vars[job.key] = late
        model.Add(start + dur <= job.finish_by // ctx.params.step).OnlyEnforceIf(late.Not())
        ctx.objective.append(-_LATE * late)
