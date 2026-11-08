"""Links an Interior job to its ledger row (SCHS-36, SCHR-INT-11, INT-24).

After a day is solved, every Interior job of the plan that holds no row yet gets
one: the row the demand provider chose for that car and day
(`ctx.interior_rows`), else the oldest Pending row of the car (an Interior placed
by hand, or a next-day retry). The row becomes Planned and the job carries the
row's service week."""
from __future__ import annotations

from sqlalchemy import select

from app.scheduling import entitlements
from app.scheduling.models import InteriorEntitlement

ORDER = 60


def after_solve(ctx, day, items, result) -> None:
    chosen = getattr(ctx, "interior_rows", {})
    for job, visit in items:
        if not entitlements.uses_entitlement(job) or job.status not in ("Scheduled", "In progress"):
            continue
        if ctx.db.scalar(select(InteriorEntitlement.id).where(InteriorEntitlement.job_id == job.id)):
            continue
        row = None
        row_id = chosen.get((visit.vehicle_id, visit.date))
        if row_id is not None:
            row = ctx.db.get(InteriorEntitlement, row_id)
            if row is not None and row.status != entitlements.PENDING:
                row = None
        if row is None:
            row = entitlements.oldest_owed(ctx.db, visit.vehicle_id)
        if row is not None:
            entitlements.plan(ctx.db, row, job)
