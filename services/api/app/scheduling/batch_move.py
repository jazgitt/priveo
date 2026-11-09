"""Batch moves of scheduled jobs (scheduler board fixes, P0-5, P0-7, P0-8 backend).

POST /v1/admin/scheduling/jobs/batch-move applies every move in one transaction.
Decision 5 (owner, 9-Nov-26) sets the rules:

- A move with `crew_id` null takes the job off its crew (Unscheduled). Nothing
  else moves. A later run plans the card again unless it is locked (decision 2).
- A placement puts the job at `start_minute` in its crew lane. Cards in its way
  shift inside that lane, and every shifted card is marked By hand (manual).
  A drop above the first card, or between two cards, pushes the cards below it.
  A forward move within one lane closes the gap the card leaves: the cards it
  passes move up, and the card lands after them (1 2 3 4 5 becomes 1 3 4 2 5).
- A locked card never moves. A placement that would move a locked card, or land
  on one, refuses the whole batch with 409 `overlap`. So does an overlap with
  another job of the same crew or the same car on that date.
- Crew hours and service hours are warnings, returned in `warnings` and stored
  as By-hand findings. They never refuse. Late placements are allowed.

Overlap and rule checks mirror `service.move_job` (same crew or same car, same
date, not skipped). `move_job` itself is not changed.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notifications import emit  # notify hook
from app.platform.errors import ApiError
from app.scheduling import hand_placement, queue, rules, service
from app.scheduling.models import Job, Schedule, Visit
from app.scheduling.schemas import AdminJob

CREW_HOURS = "crew_hours"
SERVICE_HOURS = "service_hours"
WARNING_TEXT = {
    CREW_HOURS: "That time is outside the crew member's hours.",
    SERVICE_HOURS: "That time is outside this service's working slots.",
}


class BatchMove(BaseModel):
    job_id: uuid.UUID
    # Empty takes the job off its crew member (Unscheduled).
    crew_id: uuid.UUID | None = None
    # Minutes after midnight. Required when crew_id is given.
    start_minute: int | None = Field(default=None, ge=0, lt=1440)


class BatchMoveRequest(BaseModel):
    moves: list[BatchMove] = Field(min_length=1, max_length=200)
    # Part of the contract. Warnings never refuse, so the flag changes no outcome today.
    override: bool = False


class BatchWarning(BaseModel):
    job_id: uuid.UUID
    code: str
    message: str


class BatchMoveOut(BaseModel):
    jobs: list[AdminJob]
    warnings: list[BatchWarning]


class BatchRefused(Exception):
    """The whole batch is refused. The router answers 409 with these job ids."""

    def __init__(self, job_ids: list[uuid.UUID]):
        super().__init__("overlap")
        self.job_ids = list(dict.fromkeys(job_ids))


@dataclass
class _Item:
    job_id: uuid.UUID
    start: int
    dur: int
    # A locked card (or one that has started or finished) never moves.
    locked: bool
    placed: bool = False


@dataclass
class _Outcome:
    changed: list[uuid.UUID] = field(default_factory=list)
    taken_off: list[tuple[uuid.UUID | None, Job]] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


def _lane_starts(existing: list[_Item], placed: list[_Item],
                 origin: int | None) -> dict[uuid.UUID, int]:
    """The new start of each card in one crew lane on one day. Cards not in the
    result keep their start. `origin` is the start the single placed card leaves
    in this same lane, or None."""
    out: dict[uuid.UUID, int] = {}
    if origin is not None and len(placed) == 1 and placed[0].start > origin:
        # Forward move: the cards it passes move up into the gap, and it lands after them.
        p = placed[0]
        cursor = origin
        for e in sorted((e for e in existing if origin < e.start < p.start), key=lambda e: e.start):
            out[e.job_id] = cursor
            cursor += e.dur
        items = [(cursor, 0, p)] + [(e.start, 1, e) for e in existing if e.start >= p.start]
    else:
        items = [(e.start, 1, e) for e in existing] + [(p.start, 0, p) for p in placed]
    # Walk the lane in order. Each card starts no earlier than the one before it ends.
    cursor: int | None = None
    prev: _Item | None = None
    prev_end = 0
    for key, _, item in sorted(items, key=lambda t: (t[0], t[1])):
        start = key if cursor is None else max(key, cursor)
        if item.placed and prev is not None and prev.locked and prev_end > key:
            raise BatchRefused([item.job_id, prev.job_id])
        out[item.job_id] = start
        cursor = start + item.dur
        prev, prev_end = item, cursor
    for e in existing:
        if e.locked and out.get(e.job_id, e.start) != e.start:
            raise BatchRefused([e.job_id])
    return out


def _overlap(a_start: int, a_dur: int, b_start: int, b_dur: int) -> bool:
    return a_start < b_start + b_dur and b_start < a_start + a_dur


def _lane_key(schedule_id, day, crew_id):
    return (schedule_id, day, crew_id)


def _apply(db: Session, moves: list[BatchMove], admin_id: uuid.UUID | None) -> _Outcome:
    batch_ids = {m.job_id for m in moves}
    loaded: dict[uuid.UUID, tuple[Job, Visit, Schedule]] = {}
    for m in moves:
        job = db.get(Job, m.job_id)
        if job is None:
            raise ApiError("not_found", "That job does not exist.", 404)
        visit = db.get(Visit, job.visit_id)
        schedule = db.get(Schedule, visit.schedule_id)
        if job.status != "Scheduled":
            raise ApiError("job_not_open", "That job has already started or finished.", 409)
        if m.crew_id is not None:
            if m.start_minute is None:
                raise ApiError("validation_failed", "Please give a start time.", 422,
                               {"start_minute": "Required."})
            if schedule.status == "Frozen":
                raise ApiError("schedule_frozen",
                               "This schedule is frozen. Unfreeze it with the code to move work.",
                               409)
        loaded[m.job_id] = (job, visit, schedule)

    out = _Outcome()
    placements = [m for m in moves if m.crew_id is not None]
    # Taking a job off never moves another card.
    take_offs = [m.job_id for m in moves if m.crew_id is None]

    # Each placement is put in its lane (schedule, date, crew). Only a single placement
    # can close the gap it leaves, so only then is its old start in the same lane kept.
    lanes: dict[tuple, list[_Item]] = {}
    origins: dict[tuple, int] = {}
    for m in placements:
        job, visit, schedule = loaded[m.job_id]
        key = _lane_key(schedule.id, visit.date, m.crew_id)
        lanes.setdefault(key, []).append(
            _Item(job.id, m.start_minute, job.duration_minutes, False, True))
        if len(placements) == 1 and job.crew_id == m.crew_id and job.start_minute is not None:
            origins[key] = job.start_minute

    # New start of every card that changes: the placed cards and the cards shifted in their lanes.
    new_place: dict[uuid.UUID, tuple[uuid.UUID, uuid.UUID, int]] = {}  # job -> (schedule, crew, start)
    for (sid, day, crew_id), placed_items in lanes.items():
        rows = db.execute(
            select(Job, Visit)
            .join(Visit, Job.visit_id == Visit.id)
            .where(Visit.schedule_id == sid, Visit.date == day, Job.crew_id == crew_id,
                   Job.status != "Skipped", Job.id.not_in(list(batch_ids)))
        ).all()
        existing: list[_Item] = []
        for job, visit in rows:
            if job.start_minute is None:
                continue
            existing.append(_Item(job.id, job.start_minute, job.duration_minutes,
                                  bool(job.hand_locked) or job.status != "Scheduled"))
            loaded.setdefault(job.id, (job, visit, db.get(Schedule, sid)))
        starts = _lane_starts(existing, placed_items, origins.get((sid, day, crew_id)))
        for item in placed_items:
            new_place[item.job_id] = (sid, crew_id, starts[item.job_id])
        for item in existing:
            if starts.get(item.job_id, item.start) != item.start:
                new_place[item.job_id] = (sid, crew_id, starts[item.job_id])

    # Overlaps with the cars and crew that do not move, and between the moved cards.
    # Checked on the final state, before anything is written.
    moved_ids = set(new_place)
    checked = batch_ids | moved_ids
    for jid, (sid, crew_id, start) in new_place.items():
        job, visit, _ = loaded[jid]
        others = db.execute(
            select(Job, Visit)
            .join(Visit, Job.visit_id == Visit.id)
            .where(Visit.schedule_id == sid, Visit.date == visit.date, Job.crew_id.is_not(None),
                   Job.status != "Skipped", Job.id.not_in(list(checked)))
        ).all()
        for other, other_visit in others:
            if other.crew_id != crew_id and other_visit.vehicle_id != visit.vehicle_id:
                continue
            if other.start_minute is not None and _overlap(
                    start, job.duration_minutes, other.start_minute, other.duration_minutes):
                raise BatchRefused([jid, other.id])
        for other_id, (o_sid, o_crew, o_start) in new_place.items():
            if other_id == jid or o_sid != sid:
                continue
            other_job, other_visit, _ = loaded[other_id]
            if other_visit.date != visit.date:
                continue
            if o_crew != crew_id and other_visit.vehicle_id != visit.vehicle_id:
                continue
            if _overlap(start, job.duration_minutes, o_start, other_job.duration_minutes):
                raise BatchRefused([jid, other_id])

    # Crew hours and service hours: warnings only, stored as By-hand findings.
    members: dict = {}
    warnings: dict[uuid.UUID, list[tuple[str, str]]] = {}
    for jid in sorted(new_place, key=str):
        job, visit, schedule = loaded[jid]
        sid, crew_id, start = new_place[jid]
        if sid not in members:
            members[sid] = service.load_crew(db, schedule.society_id)
        member = members[sid].get(crew_id)
        if member is None:
            raise ApiError("crew_not_found", "That crew member is not in this society.", 404)
        windows = service.availability(db, {crew_id: member}, [visit.date])[visit.date].get(crew_id)
        found = []
        if not windows or not service.fits_a_window(windows, start, job.duration_minutes):
            found.append(CREW_HOURS)
        end = start + job.duration_minutes
        if not any(s <= start and end <= e for s, e in
                   service.service_windows(db, schedule.society_id, job.service, visit.date)):
            found.append(SERVICE_HOURS)
        warnings[jid] = [(code, WARNING_TEXT[code]) for code in found]
        out.warnings.extend({"job_id": jid, "code": code, "message": text}
                            for code, text in warnings[jid])

    # Writes. Every check above has passed, so the batch applies as a whole.
    groups: set[tuple[uuid.UUID | None, date]] = set()
    for jid in sorted(new_place, key=str):
        job, visit, schedule = loaded[jid]
        sid, crew_id, start = new_place[jid]
        before = (job.crew_id, job.start_minute)
        groups.update({(job.crew_id, visit.date), (crew_id, visit.date)})
        end = start + job.duration_minutes
        job.crew_id, job.start_minute, job.manual = crew_id, start, True
        job.late = job.finish_by_minute is not None and end > job.finish_by_minute
        if jid in batch_ids:
            job.note, job.hand_locked, job.queue_unlocked = "", True, False
            detail = f"job {job.id} to {rules.hhmm(start)}"
        else:
            detail = f"job {job.id} shifted to {rules.hhmm(start)} by hand"
        hand_placement.record(db, sid, job.id, warnings[jid])
        record_change(db, sid, admin_id, detail, job, before, crew_id, start)
        service.refresh_visit_status(db, visit.id)
        out.changed.append(jid)

    for jid in take_offs:
        job, visit, schedule = loaded[jid]
        before = (job.crew_id, job.start_minute)
        groups.add((job.crew_id, visit.date))
        job.crew_id, job.start_minute, job.late = None, None, False
        job.sequence, job.queue_unlocked = None, False
        job.manual = True
        job.note = "Taken off the schedule by the admin."
        hand_placement.clear(db, job.id)
        record_change(db, schedule.id, admin_id, f"job {job.id} taken off", job, before, None, None)
        out.taken_off.append((before[0], job))
        out.changed.append(jid)

    queue.resequence_all(db, groups)
    db.flush()
    return out


def record_change(db: Session, schedule_id: uuid.UUID, admin_id: uuid.UUID | None, detail: str,
                  job: Job, before: tuple, crew_id: uuid.UUID | None, start: int | None) -> None:
    """One audit row per job, as move_job writes them."""
    service.record(db, schedule_id, admin_id, "move", detail, {
        "job": str(job.id),
        "crew_id": [str(before[0]) if before[0] else None, str(crew_id) if crew_id else None],
        "start_minute": [before[1], start]})


def apply(db: Session, body: BatchMoveRequest, admin_id: uuid.UUID | None) -> dict:
    """Applies the batch in one transaction and returns the changed jobs and the warnings."""
    ids = [m.job_id for m in body.moves]
    if len(set(ids)) != len(ids):
        raise ApiError("validation_failed", "A job appears more than once in the batch.", 422,
                       {"moves": "A job appears more than once."})
    try:
        out = _apply(db, body.moves, admin_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    for previous_crew_id, job in out.taken_off:
        emit.job_taken_off(db, job, previous_crew_id)
    rows = service.job_rows(db, Job.id.in_(out.changed)) if out.changed else []
    return {"jobs": rows, "warnings": out.warnings}
