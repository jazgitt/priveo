"""The base objective: capacity use first, then the cutoff, then earlier starts.

The terms and constants are unchanged from the single-function solver.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext, SolverJob

NAME = "base"
PRIORITY = 0

# The weights are the settings `scheduler.weight_placed`, `_late` and `_early`
# (SCHS-33); their defaults are the old constants. Capacity use comes first, then
# the cutoff times, then earlier starts.


def add_job_terms(ctx: ModelContext, job: SolverJob) -> None:
    model = ctx.model
    placed = ctx.placed_vars[job.key]
    start = ctx.start_vars[job.key]
    dur = ctx.durations[job.key]
    ctx.add_term("placed", job.duration * placed)
    ctx.add_term("early", -start)
    if job.finish_by is not None:
        late = model.NewBoolVar(f"late_{job.key}")
        ctx.late_vars[job.key] = late
        model.Add(start + dur <= job.finish_by // ctx.params.step).OnlyEnforceIf(late.Not())
        ctx.add_term("late", -late)
