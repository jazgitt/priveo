"""A vehicle's service history for the admin, with the state of each service
(A-01, HIST-04, ADM-CUS-29). The state is derived from the jobs, as everywhere
else (`scheduling.outcomes`). Not Completed shows to the customer as Missed.
No customer name or mobile number is returned."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Vehicle
from app.directory import lookup
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling.models import Job, Schedule, Visit
from app.scheduling.outcomes import OUTCOMES, visit_outcomes
from app.visits.models import JobOutcome

admin = APIRouter(prefix="/v1/admin", tags=["customer-administration"])


@admin.get("/vehicles/{vehicle_id}/service-history")
def service_history(
    vehicle_id: uuid.UUID,
    state: str | None = None,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Newest first. `counts` is for the whole history; `total` is after the filter."""
    if db.get(Vehicle, vehicle_id) is None:
        raise ApiError("not_found", "Vehicle not found.", 404)
    if state is not None and state not in OUTCOMES:
        raise ApiError("validation_failed", f"State must be one of: {', '.join(OUTCOMES)}.", 422)
    rows = db.execute(
        select(Visit, Schedule.status).join(Schedule, Schedule.id == Visit.schedule_id)
        .where(Visit.vehicle_id == vehicle_id).order_by(Visit.date.desc(), Visit.id)).all()
    outcomes = visit_outcomes(db, [v.id for v, _ in rows])
    counts = dict.fromkeys(OUTCOMES, 0)
    for v, _ in rows:
        counts[outcomes[v.id].outcome] += 1
    # The date a missed service was moved to: the visit of its follow-up job.
    missed_ids = {j.id: j.visit_id for j in db.scalars(
        select(Job).where(Job.visit_id.in_([v.id for v, _ in rows]),
                          Job.status == "Could not complete"))} if rows else {}
    revised: dict[uuid.UUID, date] = {}
    if missed_ids:
        for source, day in db.execute(
                select(Job.source_job_id, Visit.date).join(Visit, Visit.id == Job.visit_id)
                .where(Job.source_job_id.in_(list(missed_ids)))):
            visit_id = missed_ids[source]
            revised[visit_id] = min(day, revised.get(visit_id, day))
    # Days migrated from the owner's sheet are live visits; their jobs carry the legacy marker
    # (customers.history_convert). They show as "imported" with the reason of a skipped day.
    visit_ids = [v.id for v, _ in rows]
    jobs_of: dict[uuid.UUID, list[Job]] = {}
    for j in db.scalars(select(Job).where(Job.visit_id.in_(visit_ids))) if visit_ids else []:
        jobs_of.setdefault(j.visit_id, []).append(j)
    imported = {vid for vid, js in jobs_of.items()
                if any((j.checklist_snapshot or {}).get("legacy") for j in js)}
    skip_reason: dict[uuid.UUID, str] = {}
    if imported:
        for visit_id, key, note in db.execute(
                select(Job.visit_id, JobOutcome.reason_key, JobOutcome.note)
                .join(JobOutcome, JobOutcome.job_id == Job.id)
                .where(Job.visit_id.in_(list(imported)), JobOutcome.kind == "skipped")):
            skip_reason[visit_id] = (lookup.reason_label(db, key) if key else None) or note
    merged = [(v.date, (v, s)) for v, s in rows if state is None or outcomes[v.id].outcome == state]
    merged.sort(key=lambda m: m[0], reverse=True)
    items = []
    for _day, (v, schedule_status) in merged[offset:offset + limit]:
        o = outcomes[v.id]
        is_imported = v.id in imported
        items.append({
            "visit_id": str(v.id), "date": v.date.isoformat(), "state": o.outcome,
            "planned": o.planned, "delivered": o.delivered,
            "missed": [{"service": m["service"], "reason": m["reason"], "note": m["note"],
                        "rescheduled": m["rescheduled"]} for m in o.missed],
            "original_date": v.date.isoformat() if v.id in revised else None,
            "revised_date": revised[v.id].isoformat() if v.id in revised else None,
            "schedule_status": schedule_status,
            "source": "imported" if is_imported else "live",
            "reason": skip_reason.get(v.id, "") if is_imported else "",
        })
    return {"counts": counts, "total": len(merged), "items": items}
