"""Ascending cutoff order (SCHR-CUT-10, SCHR-INT-12, SCHR-HIER-09; owner decisions of
9 Nov 2026, items 2 and Q3).

The jobs of a day are sorted by a key, and each neighbour pair in that order gives one
reward, `cutoff_order`, when both jobs are placed and the earlier job starts no later
than the next one. The pairs chain, so a full run of placed jobs is rewarded for the
whole order. A reward is only earned, never forced: a pair that is not placed or not
in order simply earns nothing, so the rule cannot make a job unplaced or late.

The key:

* Interiors (in Pass B, with a known service week) first by the oldest service week,
  then by the earlier cutoff (owner, Q3). Other jobs (Exteriors, Deep Spa and an
  Interior with no known week) share the last week tier, so an Exterior is ordered
  by its cutoff alone.
* then the cutoff (a job with no cutoff last), then the car and the service, then the
  job key (SCHS-58: the same input gives the same plan).

Derived: the order is kept across cleaners, not only within one cleaner. The model
does not know yet which cleaner a job will get when the chain is built, and a
per-cleaner chain would multiply the constraints. A cross-zone rescue (SCHR-ZONE-12)
is still allowed, because `zone` ranks above this objective.

The objective ranks below placed, protected lateness, the home zone, the cleaner break
and the fifo week order (SCHR-INT-12), and above the other objectives (see
`scheduler.objective_order`). The weight is `scheduler.weight_cutoff_order` (default
1000). In the ordered solve only the order matters. The single weighted solve (a direct
call without an order) uses the same weight, so the rule stays below the 10**7
lateness weight there. Applies in both passes. A pass with fewer than two placeable
jobs adds nothing.

Derived, to report: this rule sits below `fifo`, so the oldest service week is placed
first when Interiors compete for time. Within one week the ledger-age tie-break of
SCHR-INT-12 still decides which Interior is placed; the cutoff orders the start.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext, SolverJob

NAME = "cutoff_order"
PRIORITY = 45
NO_CUTOFF = 10**9
NEWEST = 10**9  # the last week tier: Exteriors, Deep Spa and Interiors with no known week


def _week_tier(job: SolverJob, weeks: dict) -> int:
    """The service week ordinal of an Interior, or the last tier for any other job."""
    if not job.interior:
        return NEWEST
    week = job.week or weeks.get(job.vehicle)
    return week.toordinal() if week is not None else NEWEST


def add_day_terms(ctx: ModelContext) -> None:
    jobs = [j for j in ctx.free if j.key in ctx.placed_vars]
    if len(jobs) < 2:
        return
    # The service week of an Interior comes from the fifo inputs (the ledger row chosen
    # for the car that day), as in the fifo rule.
    weeks = (ctx.inputs.get("fifo") or {}).get("weeks", {})
    # The car and the service before the job key: a job key is new each time a day is
    # planned again, so the chain must not depend on it (SCHS-58).
    jobs.sort(key=lambda j: (
        _week_tier(j, weeks),
        NO_CUTOFF if j.finish_by is None else j.finish_by,
        j.vehicle, j.service or "", j.key))
    model = ctx.model
    for earlier, later in zip(jobs, jobs[1:], strict=False):
        both = model.NewBoolVar(f"co_{earlier.key}_{later.key}")
        model.AddImplication(both, ctx.placed_vars[earlier.key])
        model.AddImplication(both, ctx.placed_vars[later.key])
        model.Add(ctx.start_vars[earlier.key] <= ctx.start_vars[later.key]).OnlyEnforceIf(both)
        ctx.add_term("cutoff_order", both)
