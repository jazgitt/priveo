"""Ascending cutoff order: a job with an earlier cutoff starts first (SCHR-CUT-10,
SCHR-HIER-09; owner decision 09-Nov-26, item 2).

The jobs of a day that have a cutoff are sorted by (cutoff, car, service, key).
Each neighbour pair in that order gives one reward, `cutoff_order`, when both jobs
are placed and the earlier-cutoff job starts no later than the next one. The
pairs chain, so a full run of placed jobs is rewarded for the whole ascending order.
A reward is only earned, never forced: a pair that is not placed or not in order
simply earns nothing, so the rule cannot make a job unplaced or late.

Derived: the order is kept across cleaners, not only within one cleaner. The
model does not know yet which cleaner a job will get when the chain is built, and
a per-cleaner chain would multiply the constraints. In practice the board reads in
cutoff order over the day, and a cross-zone rescue (SCHR-ZONE-12) is still allowed,
because `zone` ranks above this objective.

The objective ranks below placed, protected lateness and the home zone, and above
break, fifo, late and the early objectives (see `scheduler.objective_order`). The
weight is `scheduler.weight_cutoff_order` (default 1000). In the ordered solve only
the order matters. The single weighted solve (a direct call without an order)
uses the same weight, so the rule stays below the 10**7 lateness weight there.
Applies in both passes. A pass with fewer than two cutoff jobs adds nothing.

Derived, to report: this rule sits above `fifo` and `late`. In Pass B that can
trade the oldest-week-first choice (SCHR-INT-12) when Interiors compete for the
same free time, and it can trade weekend lateness (not protected lateness, which
ranks above). The owner's order puts it there.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext

NAME = "cutoff_order"
PRIORITY = 45


def add_day_terms(ctx: ModelContext) -> None:
    jobs = [j for j in ctx.free if j.finish_by is not None and j.key in ctx.placed_vars]
    if len(jobs) < 2:
        return
    # The car and the service before the job key: a job key is new each time a
    # day is planned again, so the chain must not depend on it (SCHS-58).
    jobs.sort(key=lambda j: (j.finish_by, j.vehicle, j.service or "", j.key))
    model = ctx.model
    for earlier, later in zip(jobs, jobs[1:], strict=False):
        both = model.NewBoolVar(f"co_{earlier.key}_{later.key}")
        model.AddImplication(both, ctx.placed_vars[earlier.key])
        model.AddImplication(both, ctx.placed_vars[later.key])
        model.Add(ctx.start_vars[earlier.key] <= ctx.start_vars[later.key]).OnlyEnforceIf(both)
        ctx.add_term("cutoff_order", both)
