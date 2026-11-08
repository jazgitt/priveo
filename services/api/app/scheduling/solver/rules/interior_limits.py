"""One Interior per service week and per car per day (SCHS-37, SCHR-HARD-10,
HARD-11, INT-18).

The solver plans one day. In that day a car gets at most one Interior of the
plan, and at most one against a service week. A car that already has an Interior
placed that day (kept by hand or frozen) gets no second one. Two Interiors in
one calendar week are fine when they are on separate days for different service
weeks: the days are separate solves, and the entitlement ledger holds one row for
each service week (`demand_providers/entitlement.py`), so no week is planned twice.

The caller marks a job `interior` only when the job uses the entitlement. A job that this rule leaves out is
reported as `entitlement_used`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.scheduling.codes import ReasonCode

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext

NAME = "interior_limits"
PRIORITY = 50


def add_day_terms(ctx: ModelContext) -> None:
    kept = {j.vehicle for j in ctx.kept if j.interior}
    kept_weeks = {(j.vehicle, j.week) for j in ctx.kept if j.interior and j.week is not None}
    by_car: dict[str, list] = {}
    by_week: dict[tuple, list] = {}
    for job in ctx.free:
        if not job.interior or job.key not in ctx.placed_vars:
            continue
        by_car.setdefault(job.vehicle, []).append(job)
        if job.week is not None:
            by_week.setdefault((job.vehicle, job.week), []).append(job)
    for car, jobs in by_car.items():
        _limit(ctx, jobs, 0 if car in kept else 1)
    for (car, week), jobs in by_week.items():
        _limit(ctx, jobs, 0 if (car, week) in kept_weeks else 1)


def _limit(ctx: ModelContext, jobs: list, room: int) -> None:
    if room == 0:
        for job in jobs:
            ctx.model.Add(ctx.placed_vars[job.key] == 0)
            ctx.reasons[job.key] = ReasonCode.ENTITLEMENT_USED
    elif len(jobs) > 1:
        ctx.model.Add(sum(ctx.placed_vars[j.key] for j in jobs) <= room)
        for job in jobs:
            ctx.reasons[job.key] = ReasonCode.ENTITLEMENT_USED
