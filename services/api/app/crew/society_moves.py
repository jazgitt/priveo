"""A crew member's society over time (ADM-CRW-13, ADM-CRW-22).

A move is added as a new dated row in `crew_society_assignments`. Nothing
already recorded is edited, so past associations never change. When a move
takes effect the crew member's current society and the scheduler's record
follow it, and their open jobs from that date on go back to the Needs
scheduling list (they belong to the old society's schedules).

`apply_due_moves` is cheap and safe to repeat. It runs when the admin opens
crew data, before the scheduler loads a society's crew, and in the daily cron.
"""
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember, CrewSocietyAssignment
from app.scheduling import service as scheduling
from app.scheduling.models import SchedulingCrew


def add_first_assignment(db: Session, crew: CrewMember, on: date, by: uuid.UUID | None) -> None:
    """The society the crew member was onboarded into."""
    db.add(CrewSocietyAssignment(
        crew_id=crew.id, society_id=crew.society_id, effective_from=on, created_by=by))
    db.flush()


def ensure_first_assignment(db: Session, crew: CrewMember) -> None:
    """A crew member made before moves existed (or by another route) gets their
    first stay from the day they were onboarded."""
    if db.scalar(select(CrewSocietyAssignment.id).where(
            CrewSocietyAssignment.crew_id == crew.id).limit(1)) is None:
        add_first_assignment(db, crew, crew.created_at.date(), None)


def pending_move(db: Session, crew_id: uuid.UUID, today: date) -> CrewSocietyAssignment | None:
    return db.scalar(select(CrewSocietyAssignment).where(
        CrewSocietyAssignment.crew_id == crew_id, CrewSocietyAssignment.effective_from > today))


def history(db: Session, crew_id: uuid.UUID) -> list[CrewSocietyAssignment]:
    return list(db.scalars(
        select(CrewSocietyAssignment).where(CrewSocietyAssignment.crew_id == crew_id)
        .order_by(CrewSocietyAssignment.effective_from)))


def end_dates(rows: list[CrewSocietyAssignment]) -> list[date | None]:
    """Each stay ends the day before the next one starts."""
    return [rows[i + 1].effective_from - timedelta(days=1) if i + 1 < len(rows) else None
            for i in range(len(rows))]


def apply_one(db: Session, crew: CrewMember, row: CrewSocietyAssignment, today: date) -> list[dict]:
    """Makes `row` the crew member's society. Returns the jobs released."""
    crew.society_id = row.society_id
    sc = db.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == crew.login_id))
    released: list[dict] = []
    if sc is not None:
        sc.society_id = row.society_id
        if crew.role == "Trainee":
            mate = db.get(CrewMember, row.paired_member_id) if row.paired_member_id else None
            mate_sc = db.scalar(select(SchedulingCrew).where(
                SchedulingCrew.login_id == mate.login_id)) if mate else None
            sc.paired_member_id = mate_sc.id if mate_sc else None
        else:
            sc.paired_member_id = None
        # Dates before today are history and stay as they were.
        released = scheduling.release_open_jobs(db, sc, max(row.effective_from, today))
    db.flush()
    return released


def apply_due_moves(db: Session, today: date, commit: bool = True) -> int:
    """Applies every move whose date has come. Returns how many were applied.
    With `commit` false the caller commits."""
    rows = list(db.scalars(
        select(CrewSocietyAssignment).where(CrewSocietyAssignment.effective_from <= today)
        .order_by(CrewSocietyAssignment.crew_id, CrewSocietyAssignment.effective_from)))
    latest: dict[uuid.UUID, CrewSocietyAssignment] = {}
    for row in rows:
        latest[row.crew_id] = row
    applied = 0
    for crew_id, row in latest.items():
        crew = db.get(CrewMember, crew_id)
        if crew is not None and crew.society_id != row.society_id:
            apply_one(db, crew, row, today)
            applied += 1
    if applied and commit:
        db.commit()
    return applied
