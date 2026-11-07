"""Structured unassigned reasons and the shortfall (SCHS-21).

After a day is solved, every job the solver left unassigned gets the stable code
of its reason (`codes.ReasonCode`) on `Job.reason_code` and a finding with the
same code, and a job that was placed loses any code it carried. The text stays
in `Job.note`. Runs only at `scheduler.rules_version` 2 (the hook is skipped
otherwise). The shortfall of a run, in cars and minutes, is `run_shortfall`;
the run endpoint adds it to its answer for a site on version 2."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.scheduling import hooks
from app.scheduling.models import SERVICES, Job, Schedule, Visit

ORDER = 50


def after_solve(ctx, day, items, result) -> None:
    held = getattr(ctx, "interior_held", {})
    for job, visit in items:
        key = str(job.id)
        if (visit.vehicle_id, day) in held and key not in result.placed:
            # Optional Interior held off the preferred day (18.5): Unscheduled, with the reason.
            job.note = held[(visit.vehicle_id, day)]
            job.reason_code = None
            continue
        code = result.unplaced_codes.get(key)
        if code is not None:
            job.reason_code = code.value
            ctx.add_finding(code.value, code.text or "", job.id)
        elif key in result.placed:
            job.reason_code = None


def run_shortfall(db: Session, schedule: Schedule) -> dict:
    """Unassigned Exteriors of a schedule, the cars they belong to and their
    minutes. All null when the site is not on rules version 2. A job the admin
    took off by hand is the admin's choice and is not counted."""
    if hooks._version(db, schedule.society_id) != 2:
        return {"unassigned_exteriors": None, "shortfall_cars": None, "shortfall_minutes": None}
    exterior = SERVICES[0]
    rows = db.execute(
        select(Visit.vehicle_id, Job.duration_minutes)
        .join(Job, Job.visit_id == Visit.id)
        .where(Visit.schedule_id == schedule.id, Job.service == exterior,
               Job.status == "Scheduled", Job.crew_id.is_(None), Job.manual.is_(False))).all()
    cars: set[uuid.UUID] = {r[0] for r in rows}
    return {"unassigned_exteriors": len(rows), "shortfall_cars": len(cars),
            "shortfall_minutes": sum(r[1] for r in rows)}
