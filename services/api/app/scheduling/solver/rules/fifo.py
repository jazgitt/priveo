"""Oldest service week first in the Interior pass (SCHS-46; SCHR-INT-10, INT-12,
INT-13, SCHR-WKE-05).

In Pass B the plan's own Interiors compete for the cleaners' free time. When not
all can be placed, the objective `fifo` (weight `scheduler.weight_fifo`) picks
them in this order:

1. the older service week first, so overdue work (a carry from an earlier week,
   INT-13) always goes ahead of the new Interior of the current week and an older
   week beats a newer one whatever the number of jobs,
2. in the same week, the entitlement that has waited longest (its ledger row is
   the oldest),
3. then the tighter weekday cutoff,
4. then the stable order of the job key (HIER-06).

A weekend day uses the same order (WKE-05). The weekday-before-weekend choice
(INT-10) is made when the day is chosen for the entitlement
(`demand_providers/entitlement.py`); this module only orders the jobs of one day.

The service week of a job is `job.week` when the job has one, else the week of the
ledger row the demand provider chose for the car that day (`day_inputs`). The
module does nothing outside the Interior pass, and nothing when a day has fewer
than two Interiors to place.

Derived: the objective is a weighted sum with values that make each tier outweigh
all the tiers below it, so the order is strict. Values are capped near 2**40; if
there are more weeks than the cap allows, the oldest weeks share one tier.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext, SolverCrew

NAME = "fifo"
PRIORITY = 70
VALUE_CAP = 2**40
NO_CUTOFF = 10**9


def day_inputs(run_ctx, day: date, crew: list[SolverCrew]) -> dict | None:
    """The service week and the age of the ledger row chosen for each car on `day`."""
    if not run_ctx.active:
        return None
    chosen = {v: r for (v, d), r in getattr(run_ctx, "interior_rows", {}).items() if d == day}
    if not chosen:
        return None
    from app.scheduling.models import InteriorEntitlement

    weeks, created = {}, {}
    for vehicle, row_id in chosen.items():
        row = run_ctx.db.get(InteriorEntitlement, row_id)
        if row is not None:
            weeks[str(vehicle)] = row.service_week_start
            created[str(vehicle)] = row.created_at.timestamp() if row.created_at else 0.0
    return {"weeks": weeks, "created": created}


def tier_values(count: int, tiers: int) -> list[int]:
    """The base value of each tier, oldest first. A tier outweighs every set of jobs below it."""
    values = [0] * tiers
    for i in range(tiers - 2, -1, -1):
        values[i] = min(count * (values[i + 1] + count), VALUE_CAP)
    return values


def add_day_terms(ctx: ModelContext) -> None:
    if ctx.pass_name != "interior":
        return
    data = ctx.inputs.get(NAME) or {}
    weeks, created = data.get("weeks", {}), data.get("created", {})
    jobs = [j for j in ctx.free if j.interior and j.key in ctx.placed_vars]
    if len(jobs) < 2:
        return
    week_of = {j.key: j.week or weeks.get(j.vehicle) for j in jobs}
    known = sorted({w for w in week_of.values() if w is not None})
    tier_of = {w: i for i, w in enumerate(known)}
    newest = len(known)  # a job with no known week counts as the newest
    base = tier_values(len(jobs), newest + 1)
    by_tier: dict[int, list] = {}
    for j in jobs:
        week = week_of[j.key]
        by_tier.setdefault(tier_of[week] if week is not None else newest, []).append(j)
    terms = []
    for tier, members in by_tier.items():
        members.sort(key=lambda j: (created.get(j.vehicle, 0.0),
                                    NO_CUTOFF if j.finish_by is None else j.finish_by, j.key))
        for rank, j in enumerate(members):
            terms.append((base[tier] + len(jobs) - rank) * ctx.placed_vars[j.key])
    ctx.add_term("fifo", sum(terms))
