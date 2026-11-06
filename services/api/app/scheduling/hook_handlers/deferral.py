"""Deferral replanning (SCHS-47, SCHR-DEF-02, DEF-03).

When an Interior job becomes Deferred (the car or keys were not available,
SCHS-31), the ledger row it held goes back to Pending with its ORIGINAL service
week. The next run plans it again on a later day with the priority of its week
(`demand_providers/entitlement.py`), so it is never lost and never shown as
Completed. Runs only for a site on `scheduler.rules_version` 2 (`hooks`).
It does not commit."""
from __future__ import annotations

from app.scheduling import entitlements
from app.scheduling.hook_handlers.ledger import row_of

ORDER = 45


def on_status_change(db, job, source: str) -> None:
    if job.status != "Deferred" or not entitlements.uses_entitlement(job):
        return
    row = row_of(db, job)
    if row is not None and row.status == entitlements.PLANNED:
        entitlements.defer(db, row)
