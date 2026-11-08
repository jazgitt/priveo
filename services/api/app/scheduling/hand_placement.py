"""Hand placement warns and flags (SCHS-22, SCHR-HIER-08, SCHR-CUT-05).

The admin may place a job against any rule (owner, 05-Nov-26): the screen is warned of each breach, the admin
confirms with `override`, and every breach is stored as a finding
(`schedule_findings`) with a code that starts with `PREFIX`. The planner never
produces such a placement. Findings with this prefix are kept when a run
rewrites the findings of a schedule (`run_context.RunContext.save`), and are
replaced when the same job is placed again or taken off.

A breach is a (code, message) pair. The codes are the refusal codes `move_job`
has always used for a rule (outside the hours, outside the slot, the crew member
not working), plus `break` (the job overlaps the cleaner's break) and
`customer_cutoff` (the job ends after the Customer cutoff on a strict
day, SCHR-CUT-05). An overlap with another job is not a breach: it is refused
outright (owner, 8-Nov-26), so it is never stored here.
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.scheduling.models import ScheduleFinding

PREFIX = "hand_"
WARNING_CODE = "placement_warning"

Breach = tuple[str, str]


def finding_code(breach_code: str) -> str:
    return PREFIX + breach_code


def clear(db: Session, job_id: uuid.UUID) -> None:
    """Forget the breaches stored for a job (it was placed again or taken off)."""
    db.execute(delete(ScheduleFinding).where(
        ScheduleFinding.job_id == job_id, ScheduleFinding.code.like(PREFIX + "%")))


def messages_of(db: Session, job_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    """The breaches stored for each job, for the Board's mark on a card (SCHS-22)."""
    if not job_ids:
        return {}
    out: dict[uuid.UUID, list[str]] = {}
    rows = db.execute(select(ScheduleFinding.job_id, ScheduleFinding.detail).where(
        ScheduleFinding.job_id.in_(job_ids), ScheduleFinding.code.like(PREFIX + "%"))
        .order_by(ScheduleFinding.created_at)).all()
    for job_id, detail in rows:
        out.setdefault(job_id, []).append(detail)
    return out


def record(db: Session, schedule_id: uuid.UUID, job_id: uuid.UUID, breaches: list[Breach]) -> None:
    clear(db, job_id)
    for code, message in breaches:
        db.add(ScheduleFinding(schedule_id=schedule_id, job_id=job_id,
                               code=finding_code(code), detail=message))
