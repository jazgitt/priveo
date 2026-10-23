"""The derived outcome of a visit: planned, delivered and missed services.

Nothing is stored. The outcome is worked out from the job statuses, the
follow-up jobs the admin created on reschedule (`Job.source_job_id`) and the
add-on booking status. A visit is Completed only when all its jobs are done or
skipped; some done and some not done is Partially Completed, and it is never
hidden from follow-up.
"""
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.directory import lookup
from app.scheduling.models import Job, Visit

OUTCOMES = (
    "Scheduled",
    "Completed",
    "Partially Completed",
    "Not Completed",
    "Rescheduled",
    "Cancelled",
)
SHORT_NAME = {
    "Cleaning-External": "Exterior",
    "Cleaning-Internal": "Interior",
    "Deep Spa": "Deep Spa",
}
_OPEN = ("Scheduled", "In progress")


def outcome_of(
    statuses: Sequence[str], *, rescheduled: bool = False, cancelled: bool = False
) -> str:
    """The outcome from job statuses (the scheduler's names).

    DERIVED: a visit whose jobs are all skipped is shown as Cancelled, because
    nothing was delivered or owed. A partial visit stays Partially Completed
    even when its missed job has a follow-up, so it is never hidden."""
    if cancelled:
        return "Cancelled"
    if not statuses or any(s in _OPEN for s in statuses):
        return "Scheduled"
    if all(s == "Skipped" for s in statuses):
        return "Cancelled"
    missed = any(s == "Could not complete" for s in statuses)
    if not missed:
        return "Completed"
    if any(s == "Completed" for s in statuses):
        return "Partially Completed"
    return "Rescheduled" if rescheduled else "Not Completed"


@dataclass
class VisitOutcome:
    outcome: str = "Scheduled"
    planned: list[str] = field(default_factory=list)
    delivered: list[str] = field(default_factory=list)
    # {"service", "reason_key", "reason", "note", "rescheduled"}
    missed: list[dict] = field(default_factory=list)

    @property
    def partial(self) -> bool:
        return self.outcome == "Partially Completed"


def customer_summary(planned: Iterable[str], delivered: Iterable[str], missed: list[dict]) -> str:
    """Plain customer copy, no crew names: "Exterior done. Interior not done
    today: Car is locked." Empty when nothing was missed."""
    if not missed:
        return ""
    parts = []
    done = [SHORT_NAME.get(s, s) for s in delivered]
    if done:
        parts.append(f"{' and '.join(done)} done.")
    for m in missed:
        name = SHORT_NAME.get(m["service"], m["service"])
        why = m.get("reason") or m.get("note") or ""
        parts.append(f"{name} not done today{': ' + why if why else ''}.")
    return " ".join(parts)


def visit_outcomes(db: Session, visit_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, VisitOutcome]:
    from app.visits.models import JobOutcome

    ids = list(set(visit_ids))
    if not ids:
        return {}
    jobs = list(db.scalars(select(Job).where(Job.visit_id.in_(ids))))
    job_ids = [j.id for j in jobs]
    followed = (
        set(db.scalars(select(Job.source_job_id).where(Job.source_job_id.in_(job_ids))))
        if job_ids
        else set()
    )
    notes = (
        {o.job_id: o for o in db.scalars(select(JobOutcome).where(JobOutcome.job_id.in_(job_ids)))}
        if job_ids
        else {}
    )
    booking_ids = {j.addon_booking_id for j in jobs if j.addon_booking_id}
    cancelled_bookings = (
        set(
            db.scalars(
                select(AddonBooking.id).where(
                    AddonBooking.id.in_(booking_ids), AddonBooking.status == "Cancelled"
                )
            )
        )
        if booking_ids
        else set()
    )
    by_visit: dict[uuid.UUID, list[Job]] = {i: [] for i in ids}
    for j in jobs:
        by_visit[j.visit_id].append(j)
    out = {}
    for vid, rows in by_visit.items():
        missed_rows = [j for j in rows if j.status == "Could not complete"]
        rescheduled = bool(missed_rows) and all(j.id in followed for j in missed_rows)
        cancelled = bool(rows) and all(j.addon_booking_id in cancelled_bookings for j in rows)
        o = VisitOutcome(
            outcome=outcome_of(
                [j.status for j in rows], rescheduled=rescheduled, cancelled=cancelled
            ),
            planned=[j.service for j in rows],
            delivered=[j.service for j in rows if j.status == "Completed"],
        )
        for j in missed_rows:
            rec = notes.get(j.id)
            key = rec.reason_key if rec else None
            o.missed.append(
                {
                    "service": j.service,
                    "reason_key": key,
                    "reason": (lookup.reason_label(db, key) or key or "") if key else "",
                    "note": rec.note if rec else "",
                    "rescheduled": j.id in followed,
                }
            )
        out[vid] = o
    return out


def outcome_of_visit(db: Session, visit: Visit | uuid.UUID) -> VisitOutcome:
    vid = visit.id if isinstance(visit, Visit) else visit
    return visit_outcomes(db, [vid])[vid]
