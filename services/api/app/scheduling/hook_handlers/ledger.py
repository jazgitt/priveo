"""The ledger follows job outcomes (SCHS-30, SCHR-INT-14 to INT-16, INT-24,
SCHR-DEF-06).

When an Interior job of the plan changes status, the entitlement row it uses
changes with it:

    Completed    the row is Completed with the job and today's date. It keeps
                 its ORIGINAL service week, so an overdue week-1 Interior done
                 in week 2 completes week 1 and leaves week 2 Pending
                 (INT-14, INT-15).
    Could not complete, Skipped
                 the row goes back to Pending with its service week. It never
                 expires (DEF-06, INT-16). A one-day skip and an operations skip
                 leave the week owed (INT-21; the skip is Derived from it).

A job with no row yet (placed by hand, or a next-day retry made by the admin)
that is completed is counted against the oldest Pending week of the car
(INT-24). The Deferred status is handled by `deferral.py` (SCHS-47).

The module runs only for a site on `scheduler.rules_version` 2 (`hooks`).
It does not commit.
"""
from __future__ import annotations

from sqlalchemy import select

from app.platform import clock
from app.scheduling import entitlements
from app.scheduling.models import InteriorEntitlement, Visit

ORDER = 40
RETURN_TO_PENDING = ("Could not complete", "Skipped")


def row_of(db, job) -> InteriorEntitlement | None:
    """The ledger row that holds this job."""
    return db.scalar(select(InteriorEntitlement).where(InteriorEntitlement.job_id == job.id))


def on_status_change(db, job, source: str) -> None:
    if not entitlements.uses_entitlement(job):
        return
    row = row_of(db, job)
    if job.status == "Completed":
        if row is None:
            vehicle_id = db.scalar(select(Visit.vehicle_id).where(Visit.id == job.visit_id))
            row = entitlements.oldest_owed(db, vehicle_id)  # INT-24
            if row is None:
                return  # nothing is owed: the Interior is not against the ledger
        entitlements.complete(db, row, job, clock.today_ist())
    elif job.status in RETURN_TO_PENDING and row is not None and row.status == entitlements.PLANNED:
        entitlements.defer(db, row)
