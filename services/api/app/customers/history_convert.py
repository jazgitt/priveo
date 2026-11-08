"""Migrated service history is live history (owner decision, 8 Nov 2026).

A day from the owner's calendar sheet (before the app, or during the catch-up
period) becomes the same rows a live day has: a Schedule (one day, Frozen), a
Visit, its Jobs and, for a plan Interior, the entitlement that week owes. The
jobs carry no crew, no times and no timing rows, so no crew screen, customer
notification or rating prompt treats them as work that happened in the app.
Jobs are marked `checklist_snapshot["legacy"] = True` so the history screens
can label the source "imported".

Mapping (owner answers, 8 Nov 2026):
- a weekly off writes nothing: no visit, the same as a live weekly off;
- "Exterior" writes a completed Exterior job, "Exterior + Interior" a completed
  Exterior and Interior;
- any other skip writes a skipped Exterior job. The sheet's reason text (for
  example "Rain") is kept in the outcome note; it is not mapped to a reason key,
  so the reason list in the configuration can supply the key later;
- a week that owes an Interior gets a Completed entitlement row dated to the day
  (the oldest Pending row of that week is completed when one exists); weeks
  without an Interior get nothing, so no backlog is created;
- a day that already has a live visit is never written (returns "live");
- a migrated visit is never rateable (`is_imported_visit`, used by the rating endpoint).

Nothing here sends a notification or calls the status hooks: those stamp
today's date and message the customer about work that is already done.
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.customers.models import Subscription, Vehicle
from app.directory import lookup
from app.identity.models import Login
from app.platform.db import utcnow
from app.scheduling import entitlements
from app.scheduling.models import InteriorEntitlement, Job, Schedule, Visit
from app.visits.models import JobOutcome

EXTERIOR, INTERIOR = "Cleaning-External", "Cleaning-Internal"
EXTERIOR_LABEL, BOTH_LABEL = "Exterior", "Exterior + Interior"
WEEKLY_OFF = "Weekly off"
LEGACY_SNAPSHOT = {"legacy": True, "items": []}

WRITTEN, LIVE, NOTHING = "written", "live", "nothing"


def admin_login_id(db: Session) -> uuid.UUID:
    """The admin who is recorded as the author of imported skips."""
    login = db.scalar(select(Login.id).where(Login.role == "admin").order_by(Login.created_at))
    if login is None:
        raise ValueError("There is no admin login to record the imported skips against.")
    return login


def _schedule_for(db: Session, society_id: uuid.UUID, day: date) -> Schedule:
    found = db.scalar(select(Schedule).where(
        Schedule.society_id == society_id, Schedule.start_date <= day, Schedule.end_date >= day))
    if found is not None:
        return found
    schedule = Schedule(society_id=society_id, start_date=day, end_date=day,
                        status="Frozen", frozen_at=utcnow())
    db.add(schedule)
    db.flush()
    return schedule


def _service_rows(services: str, outcome: str) -> list[str]:
    if outcome == "Skipped":
        return [EXTERIOR]
    return [EXTERIOR, INTERIOR] if services == BOTH_LABEL else [EXTERIOR]


def _owes_interior_row(db: Session, vehicle_id: uuid.UUID, week: date) -> InteriorEntitlement | None:
    """A Pending row of that week to complete, or None."""
    return db.scalar(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == vehicle_id,
        InteriorEntitlement.service_week_start == week,
        InteriorEntitlement.status == entitlements.PENDING).order_by(InteriorEntitlement.seq))


def _record_interior(db: Session, vehicle: Vehicle, job: Job, day: date, society_id: uuid.UUID) -> None:
    """The Interior that day counts against its service week, as a live one would."""
    week = entitlements.week_start(db, day, society_id)
    pending = _owes_interior_row(db, vehicle.id, week)
    if pending is not None:
        entitlements.complete(db, pending, job, day)
        return
    taken = db.scalar(select(func.count(InteriorEntitlement.id)).where(
        InteriorEntitlement.vehicle_id == vehicle.id,
        InteriorEntitlement.service_week_start == week))
    if taken:
        return  # the week already has its row: an extra Interior does not add debt or credit
    sub_id = db.scalar(select(Subscription.id).where(Subscription.vehicle_id == vehicle.id)
                       .order_by(Subscription.created_at.desc()))
    db.add(InteriorEntitlement(
        subscription_id=sub_id, vehicle_id=vehicle.id, service_week_start=week, seq=1,
        status=entitlements.COMPLETED, job_id=job.id, completed_on=day))
    job.service_week_start = week
    db.flush()


def is_imported_visit(db: Session, visit_id: uuid.UUID) -> bool:
    """True when the visit is a migrated day (its jobs carry the legacy marker)."""
    jobs = db.scalars(select(Job.checklist_snapshot).where(Job.visit_id == visit_id)).all()
    return any((snap or {}).get("legacy") for snap in jobs)


def write_record(db: Session, vehicle: Vehicle, day: date, *, services: str, outcome: str,
                 skip_reason: str, admin_id: uuid.UUID) -> str:
    """Write one migrated day as live rows. Returns WRITTEN, LIVE (a live visit
    already exists that day, nothing written) or NOTHING (a weekly off)."""
    from app.scheduling import service as scheduling

    if skip_reason == WEEKLY_OFF:
        return NOTHING
    live = db.scalar(select(Visit.id).where(Visit.vehicle_id == vehicle.id, Visit.date == day))
    if live is not None:
        return LIVE
    society_id = entitlements.society_of(db, vehicle.id)
    schedule = _schedule_for(db, society_id, day)
    visit = Visit(schedule_id=schedule.id, vehicle_id=vehicle.id, date=day, addon_key="")
    db.add(visit)
    db.flush()
    job_status = "Skipped" if outcome == "Skipped" else "Completed"
    jobs = []
    for service in _service_rows(services, outcome):
        job = Job(visit_id=visit.id, service=service, status=job_status,
                  duration_minutes=lookup.duration_minutes(db, service),
                  checklist_snapshot=dict(LEGACY_SNAPSHOT))
        db.add(job)
        jobs.append(job)
    db.flush()
    if job_status == "Skipped":
        db.add(JobOutcome(job_id=jobs[0].id, kind="skipped", reason_key=None,
                          note=skip_reason, by_login_id=admin_id))
    for job in jobs:
        if job.service == INTERIOR and job_status == "Completed":
            _record_interior(db, vehicle, job, day, society_id)
    scheduling.refresh_visit_status(db, visit.id)
    return WRITTEN


# ---- the sheet's status for a day that already has a scheduled visit ----------
# The owner's answers (9 Nov 2026): a "Priveo Missed" cell is Could not complete;
# "int,ext" on a visit with no Interior adds a completed Interior; "ext" on a visit
# with an Interior marks the Interior skipped; a skip keeps the sheet's reason text.
# Nothing here sends a notification: the status hooks that do are not called.

MISSED = "Missed"
MISSED_STATUS = "Could not complete"


def parse_cell(value: str) -> tuple[str, str, str] | None:
    """(services, outcome, reason) for a sheet cell, or None when it is not a
    service value. Any "skipped - <text>" is accepted: the text is kept as the reason."""
    text = " ".join(value.split())
    low = text.lower()
    if low == "ext":
        return EXTERIOR_LABEL, "Completed", ""
    if low == "int,ext":
        return BOTH_LABEL, "Completed", ""
    if low == "skipped":
        return "", "Skipped", ""
    if "priveo missed" in low:
        return "", MISSED, ""
    if low.startswith("skipped"):
        return "", "Skipped", text[len("skipped"):].lstrip(" -").strip()
    return None


def scheduled_visit(db: Session, vehicle_id: uuid.UUID, day: date) -> Visit | None:
    """The plan visit of the car that day, while it is still Scheduled."""
    return db.scalar(select(Visit).where(
        Visit.vehicle_id == vehicle_id, Visit.date == day, Visit.addon_key == "",
        Visit.status == "Scheduled"))


def _add_interior(db: Session, visit: Visit) -> Job:
    from app.directory import lookup

    job = Job(visit_id=visit.id, service=INTERIOR, status="Scheduled",
              duration_minutes=lookup.duration_minutes(db, INTERIOR))
    db.add(job)
    db.flush()
    return job


def apply_status(db: Session, visit: Visit, services: str, outcome: str, reason: str,
                 admin_id: uuid.UUID) -> Counter:
    """Set the jobs of a scheduled visit to what the sheet says. Returns counts."""
    from app.scheduling import service as scheduling
    from app.scheduling.hook_handlers import ledger

    counts: Counter = Counter()
    jobs = {j.service: j for j in db.scalars(select(Job).where(Job.visit_id == visit.id))}
    if EXTERIOR not in jobs:
        counts["no_exterior_job"] += 1
        return counts
    if outcome == "Completed":
        want = {EXTERIOR: "Completed"}
        if services == BOTH_LABEL:
            if INTERIOR not in jobs:
                jobs[INTERIOR] = _add_interior(db, visit)
                counts["interior_added"] += 1
            want[INTERIOR] = "Completed"
        elif INTERIOR in jobs:
            want[INTERIOR] = "Skipped"
            counts["interior_skipped"] += 1
    elif outcome == "Skipped":
        want = {service: "Skipped" for service in jobs}
    else:  # Missed
        want = {service: MISSED_STATUS for service in jobs}
    for service, status in want.items():
        job = jobs[service]
        if job.status == status:
            continue
        job.status = status
        db.flush()
        if status in ("Skipped", MISSED_STATUS):
            kind = "skipped" if status == "Skipped" else "could_not_complete"
            note = reason if status == "Skipped" else ""
            db.add(JobOutcome(job_id=job.id, kind=kind, reason_key=None, note=note,
                              by_login_id=admin_id))
            db.flush()
        ledger.on_status_change(db, job, "sheet")
        if service == INTERIOR and status == "Completed":
            row = ledger.row_of(db, job)  # the live hook stamps today: the sheet dates it to the day done
            if row is not None:
                row.completed_on = visit.date
        counts[status] += 1
    scheduling.refresh_visit_status(db, visit.id)
    return counts
