"""The job-card rows for one day (P1-2), read from the same job rows the Schedule board shows.

Only crew work is listed: a job with a crew member that is not skipped. The car
model is read from the vehicle row itself, so the card shows the model and not
the make (P2-7). Read only."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Subscription, Vehicle
from app.identity.models import Login
from app.scheduling import service as scheduling_service
from app.scheduling.models import Schedule, SchedulingCrew, Visit

# The same short codes the board shows on a card (Board.tsx, CODES).
SERVICE_CODES = {"Cleaning-External": "EXT", "Cleaning-Internal": "INT", "Deep Spa": "SPA"}


@dataclass(frozen=True)
class CardRow:
    window: str
    zone: str
    registration: str
    model: str
    customer: str
    service_code: str
    service_name: str
    cutoff: str
    parking: str
    status: str
    notes: tuple[str, ...]
    special_notes: str = ""


@dataclass(frozen=True)
class CrewCards:
    crew_id: uuid.UUID
    name: str
    rows: tuple[CardRow, ...]


def service_code(service: str) -> str:
    """EXT, INT or SPA for a service. Any other service keeps its first three letters."""
    return SERVICE_CODES.get(service) or re.sub(r"[^A-Za-z]", "", service)[:3].upper()


def zone_short(zone: str) -> str:
    """"Zone 3" is "Z3", as on the card. Any other name keeps its first letters."""
    m = re.match(r"^\s*zone\s*(.+)$", zone, re.IGNORECASE)
    return f"Z{m.group(1).strip()}" if m else zone.strip()[:4]


def _window(job: dict) -> str:
    if job["start_time"]:
        return f"{job['start_time']}-{job['end_time']}"
    return f"{job['duration_minutes']} min"


def _notes(job: dict) -> tuple[str, ...]:
    """The flags and notes the card shows, in the card's own words."""
    notes = []
    if job["status"] != "Scheduled":
        notes.append(job["status"])
    if job["late"]:
        notes.append("Late")
    if job["manual"]:
        notes.append("By hand")
    if job.get("cross_zone_reason"):
        notes.append("Outside zone")
    if job.get("hand_breaches"):
        notes.append("Placed by hand against a rule")
    return tuple(notes)


def _special_notes(*texts: str | None) -> str:
    """The non-empty texts of the vehicle note and the interior-day note, joined with "; "."""
    return "; ".join(t.strip() for t in texts if t and t.strip())


def _row(job: dict, model: str, special_notes: str = "") -> CardRow:
    return CardRow(
        window=_window(job),
        zone=zone_short(job["zone"]) if job["zone"] else "",
        registration=job["registration"],
        model=model,
        customer=job["customer_name"],
        service_code=service_code(job["service"]),
        service_name=job["service"],
        cutoff=f"Cutoff {job['finish_by']}" if job["finish_by"] else "",
        parking=job["parking"] or "",
        status=job["status"],
        notes=_notes(job),
        special_notes=special_notes,
    )


def crew_cards(
    db: Session, schedule: Schedule, day: date, crew_id: uuid.UUID | None = None
) -> list[CrewCards]:
    """Each crew member's cards for `day`, crew in name order and cards in time order.
    Crew with no card that day are left out. `crew_id` limits the list to one member."""
    jobs = [
        j for j in scheduling_service.job_rows(db, Visit.schedule_id == schedule.id, Visit.date == day)
        if j["crew_id"] is not None and j["status"] != "Skipped"
        and (crew_id is None or j["crew_id"] == crew_id)
    ]
    if not jobs:
        return []
    vehicle_ids = {j["vehicle_id"] for j in jobs}
    models = dict(db.execute(select(Vehicle.id, Vehicle.model).where(Vehicle.id.in_(vehicle_ids))).all())
    vehicle_notes = dict(db.execute(select(Vehicle.id, Vehicle.notes).where(Vehicle.id.in_(vehicle_ids))).all())
    interior_notes = dict(db.execute(
        select(Subscription.vehicle_id, Subscription.interior_day_notes)
        .where(Subscription.vehicle_id.in_(vehicle_ids))
    ).all())
    by_crew: dict[uuid.UUID, list[CardRow]] = {}
    names: dict[uuid.UUID, str] = {}
    for job in sorted(jobs, key=lambda j: (j["start_minute"] is None, j["start_minute"] or 0)):
        by_crew.setdefault(job["crew_id"], []).append(_row(
            job, models.get(job["vehicle_id"]) or "",
            _special_notes(vehicle_notes.get(job["vehicle_id"]), interior_notes.get(job["vehicle_id"])),
        ))
        names[job["crew_id"]] = job["crew_name"] or ""
    return sorted(
        (CrewCards(crew_id=cid, name=names[cid], rows=tuple(rows)) for cid, rows in by_crew.items()),
        key=lambda c: (c.name.lower(), str(c.crew_id)),
    )


def crew_name(db: Session, crew_id: uuid.UUID) -> str | None:
    """The display name of a scheduling crew member, or None when there is none."""
    return db.scalar(
        select(Login.display_name)
        .join(SchedulingCrew, SchedulingCrew.login_id == Login.id)
        .where(SchedulingCrew.id == crew_id)
    )
