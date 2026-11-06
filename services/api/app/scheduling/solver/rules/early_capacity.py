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

Derived: the cost falls in a straight line towards the end of the range. It is
charged on the middle of the job, so a job that starts before the range is free
even if it ends inside it.
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


def add_job_terms(ctx: ModelContext, job: SolverJob) -> None:
    span = usable_range(ctx)
    if span is None:
        return
    model, step = ctx.model, ctx.params.step
    first, end = -(-span[0] // step), span[1] // step
    dur = ctx.durations[job.key]
    start, placed = ctx.start_vars[job.key], ctx.placed_vars[job.key]
    if end <= first:
        return
    # Cost of a job that starts in the range: its length times the distance of
    # its middle to the end of the range (doubled to stay whole). A job that
    # starts before the range costs nothing: it uses the unusable early band.
    inside = model.NewBoolVar(f"ec_in_{job.key}")
    model.Add(start >= first).OnlyEnforceIf(inside)
    model.Add(start <= first - 1).OnlyEnforceIf(inside.Not())
    top = dur * (2 * end)
    distance = model.NewIntVar(0, top, f"ec_d_{job.key}")
    model.AddMaxEquality(distance, [0, dur * (2 * end - 2 * start - dur)])
    charged = model.NewIntVar(0, top, f"ec_c_{job.key}")
    model.Add(charged >= distance).OnlyEnforceIf([inside, placed])
    ctx.add_term("early_capacity", -charged)
