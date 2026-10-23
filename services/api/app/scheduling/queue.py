"""The crew member's ordered daily queue (S-13, C-01, C-02, C-04, B-06).

A crew member works their day's jobs in order. A job is locked while an
earlier job of the same crew member and date is still open (Scheduled or In
progress). Completed, Could not complete (any reason) and Skipped count as
dispositioned. The admin can reorder the day or unlock one job, always with a
reason, an audit row and a notification. Manager and admin routes are not
gated: they are the overrides. The whole gate follows the flag
`crew.sequential_queue`.
"""
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Vehicle
from app.directory.service import audit
from app.features import service as features
from app.notifications import emit  # notify hook
from app.platform.errors import ApiError
from app.scheduling.models import Job, SchedulingCrew, Visit

FLAG = "crew.sequential_queue"
DISPOSITIONED = ("Completed", "Could not complete", "Skipped")


@dataclass
class Entry:
    job: Job
    visit: Visit
    locked: bool = False
    current: bool = False
    blocker: Job | None = None


def _order_key(row: tuple[Job, Visit]):
    job = row[0]
    return (
        job.sequence is None,
        job.sequence or 0,
        job.start_minute is None,
        job.start_minute or 0,
        str(job.id),
    )


def day_jobs(db: Session, crew_id: uuid.UUID, day: date) -> list[tuple[Job, Visit]]:
    """The crew member's non-skipped jobs of the date, in queue order."""
    rows = db.execute(
        select(Job, Visit)
        .join(Visit, Visit.id == Job.visit_id)
        .where(Job.crew_id == crew_id, Visit.date == day, Job.status != "Skipped")
    ).all()
    return sorted(((j, v) for j, v in rows), key=_order_key)


def entries(db: Session, crew_id: uuid.UUID, day: date, enforce: bool | None = None) -> list[Entry]:
    if enforce is None:
        enforce = features.is_enabled(db, FLAG)
    out: list[Entry] = []
    first_open: Job | None = None
    for job, visit in day_jobs(db, crew_id, day):
        e = Entry(job, visit)
        if job.status not in DISPOSITIONED:
            if first_open is None:
                first_open = job
                e.current = True
            elif enforce and not job.queue_unlocked:
                e.locked, e.blocker = True, first_open
        out.append(e)
    return out


def states_for(db: Session, jobs: list[Job]) -> dict[uuid.UUID, Entry]:
    """Queue state for each assigned job, one lookup per crew member and date."""
    if not jobs:
        return {}
    enforce = features.is_enabled(db, FLAG)
    visit_dates = {
        v.id: v.date
        for v in db.scalars(select(Visit).where(Visit.id.in_({j.visit_id for j in jobs})))
    }
    out: dict[uuid.UUID, Entry] = {}
    seen: set = set()
    for job in jobs:
        if job.crew_id is None:
            continue
        key = (job.crew_id, visit_dates[job.visit_id])
        if key in seen:
            continue
        seen.add(key)
        for e in entries(db, key[0], key[1], enforce):
            out[e.job.id] = e
    return out


def require_unlocked(db: Session, job: Job) -> None:
    """The crew's own routes call this; a locked job answers 409 queue_locked."""
    if job.crew_id is None or job.status in DISPOSITIONED:
        return
    day = db.get(Visit, job.visit_id).date
    for e in entries(db, job.crew_id, day):
        if e.job.id == job.id and e.locked:
            blocker_visit = db.get(Visit, e.blocker.visit_id)
            reg = db.get(Vehicle, blocker_visit.vehicle_id).registration
            raise ApiError("queue_locked", f"Finish {reg or 'the earlier job'} first.", 409)


def resequence(db: Session, crew_id: uuid.UUID | None, day: date) -> None:
    """Number the crew member's day in start order. The caller commits."""
    if crew_id is None:
        return
    rows = db.execute(
        select(Job, Visit)
        .join(Visit, Visit.id == Job.visit_id)
        .where(Job.crew_id == crew_id, Visit.date == day, Job.status != "Skipped")
    ).all()
    rows.sort(key=lambda r: (r[0].start_minute is None, r[0].start_minute or 0, str(r[0].id)))
    for n, (job, _v) in enumerate(rows, 1):
        job.sequence = n


def resequence_all(db: Session, groups: set[tuple[uuid.UUID | None, date]]) -> None:
    db.flush()
    for crew_id, day in groups:
        resequence(db, crew_id, day)
    db.flush()


# ---- Admin controls ---------------------------------------------------------


def _reason(reason: str) -> str:
    if not reason or not reason.strip():
        raise ApiError("validation_failed", "Enter a reason.", 422, {"reason": "Enter a reason."})
    return reason.strip()


def _regs(db: Session, rows: list[tuple[Job, Visit]]) -> list[str]:
    ids = {v.vehicle_id for _j, v in rows}
    regs = (
        {v.id: v.registration or "" for v in db.scalars(select(Vehicle).where(Vehicle.id.in_(ids)))}
        if ids
        else {}
    )
    return [regs.get(v.vehicle_id, "") for _j, v in rows]


def reorder(
    db: Session,
    admin_id: uuid.UUID,
    crew_id: uuid.UUID,
    day: date,
    ordered_job_ids: list[uuid.UUID],
    reason: str,
) -> list[uuid.UUID]:
    reason = _reason(reason)
    if db.get(SchedulingCrew, crew_id) is None:
        raise ApiError("crew_not_found", "That crew member was not found.", 404)
    current = day_jobs(db, crew_id, day)
    old_ids = [j.id for j, _v in current]
    if len(set(ordered_job_ids)) != len(ordered_job_ids) or set(ordered_job_ids) != set(old_ids):
        raise ApiError(
            "validation_failed",
            "Give every job of that crew member's day, once each.",
            422,
            {"ordered_job_ids": "Must list exactly the jobs of the day."},
        )
    by_id = {j.id: j for j, _v in current}
    old_regs = _regs(db, current)
    for n, jid in enumerate(ordered_job_ids, 1):
        by_id[jid].sequence = n
    new_rows = sorted(current, key=lambda r: ordered_job_ids.index(r[0].id))
    audit(
        db,
        admin_id,
        "queue",
        f"{crew_id}:{day.isoformat()}",
        "reorder",
        {
            "reason": reason,
            "old_order": [str(i) for i in old_ids],
            "new_order": [str(i) for i in ordered_job_ids],
            "old_registrations": old_regs,
            "new_registrations": _regs(db, new_rows),
        },
    )
    db.commit()
    emit.queue_changed(
        db, crew_id, day, "The admin changed the order of your jobs.", f"reorder:{uuid.uuid4()}"
    )
    return ordered_job_ids


def unlock(db: Session, admin_id: uuid.UUID, job_id: uuid.UUID, reason: str) -> Job:
    reason = _reason(reason)
    job = db.get(Job, job_id)
    if job is None:
        raise ApiError("not_found", "That job does not exist.", 404)
    if job.crew_id is None:
        raise ApiError("job_not_assigned", "That job has no crew member.", 409)
    if job.status != "Scheduled":
        raise ApiError("job_not_open", "That job has already started or finished.", 409)
    visit = db.get(Visit, job.visit_id)
    order = [str(j.id) for j, _v in day_jobs(db, job.crew_id, visit.date)]
    job.queue_unlocked = True
    reg = _regs(db, [(job, visit)])[0]
    audit(
        db,
        admin_id,
        "queue",
        f"{job.crew_id}:{visit.date.isoformat()}",
        "unlock",
        {
            "reason": reason,
            "job_id": str(job.id),
            "registration": reg,
            "old_order": order,
            "new_order": order,
        },
    )
    db.commit()
    emit.queue_changed(
        db,
        job.crew_id,
        visit.date,
        f"The admin unlocked {reg or 'a job'} for you to do out of turn.",
        f"unlock:{job.id}:{uuid.uuid4()}",
    )
    return job
