"""Usable early capacity (SCHR-EXT-05 to 07).

In the Exterior pass, among plans that cover the same Exteriors, the one that
leaves the most usable early free time wins. Free time is usable when it starts
no earlier than `site.interior_earliest_minute` and ends before the latest
cutoff of an Interior that is still to be placed (`pending_interiors`, given by
the Exterior pass). Free time at the end of that range counts less than free time
earlier, so each minute of work placed inside the range costs (end - minute),
and work placed before the earliest Interior start costs nothing: the early band
is where Exteriors go. The objective ranks below coverage and lateness in
`scheduler.objective_order`, so no cutoff or coverage is given up for it
(SCHR-EXT-06). The weight is `scheduler.weight_early_capacity`. The Interior pass
then fills the free slots (SCHR-EXT-07), since placed minutes come first there.

Derived: the cost falls in a straight line towards the end of the range.
The range ends at the latest cutoff of the pending Interiors, or at the end of the
last shift when one of them has no cutoff. Nothing is added when no Interior is
pending, or when the run carries no Interior-earliest time (version 1).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext, SolverJob

NAME = "early_capacity"
PRIORITY = 50
EARLIEST_KEY = "site.interior_earliest_minute"
PENDING = "pending_interiors"


def usable_range(ctx: ModelContext) -> tuple[int, int] | None:
    """(first, end) minutes of the usable early range, or None for no objective."""
    earliest = ctx.params.settings.get(EARLIEST_KEY)
    pending = ctx.inputs.get(PENDING)
    if earliest is None or not pending or ctx.pass_name == "interior":
        return None
    shift_end = max((c.end for c in ctx.crew), default=0)
    end = max(shift_end if j.finish_by is None else j.finish_by for j in pending)
    return (int(earliest), min(end, shift_end)) if end > int(earliest) else None


def cost_table(first: int, end: int, duration: int, step: int, size: int) -> list[int]:
    """Cost of a job of `duration` grid steps that starts at each grid step."""
    lo, hi = -(-first // step), end // step
    weight = [max(hi - t, 0) if t >= lo else 0 for t in range(size + duration + 1)]
    return [sum(weight[s : s + duration]) for s in range(size)]


def add_job_terms(ctx: ModelContext, job: SolverJob) -> None:
    span = usable_range(ctx)
    if span is None:
        return
    model, step = ctx.model, ctx.params.step
    size = 1440 // step + 1
    table = cost_table(*span, ctx.durations[job.key], step, size)
    if not any(table):
        return
    cost = model.NewIntVar(0, max(table), f"ec_{job.key}")
    model.AddElement(ctx.start_vars[job.key], table, cost)
    charged = model.NewIntVar(0, max(table), f"ecg_{job.key}")
    placed = ctx.placed_vars[job.key]
    model.Add(charged == cost).OnlyEnforceIf(placed)
    model.Add(charged == 0).OnlyEnforceIf(placed.Not())
    ctx.add_term("early_capacity", -charged)
