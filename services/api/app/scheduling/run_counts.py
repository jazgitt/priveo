"""The extra counts of a run summary and of the schedule history (SCHS-40,
SCHR-OUT-07).

Besides placed, unscheduled and late, a run at `scheduler.rules_version` 2
reports the Interiors that are deferred or not planned, the jobs placed outside
the cleaner's home zone and the missed breaks. At version 1 every count is 0 and
the history text is unchanged.

DERIVED: "deferred Interiors" are the Interior jobs of the plan that sit in the
Deferred state, plus the open ones nobody was assigned to (the "Interiors not
planned" of the exception report), because both are Interiors the run did not
manage to put on a cleaner's day. A job the admin took off by hand is not counted.
"""
from __future__ import annotations

from app.scheduling import entitlements

BREAK_MISSED = "break_missed"
EXTERIOR = "Cleaning-External"
EMPTY = {"deferred_interiors": 0, "cross_zone_jobs": 0, "missed_breaks": 0}


def counts(ctx, jobs: list) -> dict[str, int]:
    if not ctx.active:
        return dict(EMPTY)
    interiors = [j for j in jobs if entitlements.uses_entitlement(j)]
    return {
        "deferred_interiors": sum(
            1 for j in interiors if j.status == "Deferred"
            or (j.status == "Scheduled" and j.crew_id is None and not j.manual)),
        "cross_zone_jobs": sum(
            1 for j in jobs if j.cross_zone_reason and j.status != "Skipped"),
        "missed_breaks": sum(1 for f in ctx.findings if f["code"] == BREAK_MISSED),
    }


def detail(ctx, found: dict, jobs: list) -> str:
    """The text added to the history record. Empty at version 1."""
    if not ctx.active:
        return ""
    exteriors = sum(
        1 for j in jobs if j.service == EXTERIOR and j.status == "Scheduled"
        and j.crew_id is None and not j.manual)
    return (f", unassigned exteriors {exteriors}, deferred interiors {found['deferred_interiors']}, "
            f"cross-zone {found['cross_zone_jobs']}, missed breaks {found['missed_breaks']}")
