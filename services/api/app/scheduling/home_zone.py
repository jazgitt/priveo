"""A cleaner's home zones (SCHS-29; SCHR-ZONE-01, -07, -09).

Edit surface only: nothing here plans a day. A home zone is a zone of the
cleaner's own society. A cleaner may have several, and several cleaners may
share one. A Trainee has none of their own: it follows the paired Member
(SCHR-ZONE-09, Derived)."""
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.directory.models import Zone
from app.platform.errors import ApiError
from app.scheduling.models import SchedulingCrew, SchedulingCrewHomeZone


def paired_member(db: Session, sc: SchedulingCrew) -> SchedulingCrew | None:
    if sc.role != "Trainee" or sc.paired_member_id is None:
        return None
    return db.get(SchedulingCrew, sc.paired_member_id)


def own_zones(db: Session, sc: SchedulingCrew) -> list[Zone]:
    """The zones set on this cleaner, by name. A Trainee's list is empty."""
    return list(db.scalars(
        select(Zone).join(SchedulingCrewHomeZone, SchedulingCrewHomeZone.zone_id == Zone.id)
        .where(SchedulingCrewHomeZone.crew_id == sc.id).order_by(Zone.name)))


def zone_names_by_crew(db: Session, crew_ids) -> dict[uuid.UUID, list[str]]:
    """The home zone names of many cleaners at once, by name (P2-5, one query)."""
    ids = [cid for cid in crew_ids if cid is not None]
    out: dict[uuid.UUID, list[str]] = {}
    if not ids:
        return out
    for crew_id, name in db.execute(
        select(SchedulingCrewHomeZone.crew_id, Zone.name)
        .join(Zone, Zone.id == SchedulingCrewHomeZone.zone_id)
        .where(SchedulingCrewHomeZone.crew_id.in_(ids))
        .order_by(Zone.name)
    ):
        out.setdefault(crew_id, []).append(name)
    return out


def effective_zones(db: Session, sc: SchedulingCrew) -> list[Zone]:
    """The zones the planner treats as home: own for a Member or Manager, the
    paired Member's for a Trainee."""
    if sc.role == "Trainee":
        mate = paired_member(db, sc)
        return own_zones(db, mate) if mate else []
    return own_zones(db, sc)


def effective_zone_ids(db: Session, sc: SchedulingCrew) -> list[uuid.UUID]:
    return [z.id for z in effective_zones(db, sc)]


def zones_of(db: Session, society_id: uuid.UUID) -> list[Zone]:
    return list(db.scalars(select(Zone).where(
        Zone.society_id == society_id, Zone.active.is_(True)).order_by(Zone.name)))


def set_home_zones(db: Session, sc: SchedulingCrew, zone_ids: list[uuid.UUID]) -> None:
    """Replaces the home zones (an empty list clears them). Refuses a Trainee and
    a zone of another society. Duplicates are dropped; order is kept."""
    if sc.role == "Trainee":
        raise ApiError("validation_failed", "A Trainee follows the paired Member's home zone.",
                       422, {"home_zone_ids": "Set the home zones on the paired Member."})
    wanted = list(dict.fromkeys(zone_ids))
    for zone_id in wanted:
        zone = db.get(Zone, zone_id)
        if zone is None or zone.society_id != sc.society_id or not zone.active:
            raise ApiError("validation_failed", "Choose zones of this crew member's society.",
                           422, {"home_zone_ids": "Choose zones of this society."})
    db.execute(delete(SchedulingCrewHomeZone).where(SchedulingCrewHomeZone.crew_id == sc.id))
    for zone_id in wanted:
        db.add(SchedulingCrewHomeZone(crew_id=sc.id, zone_id=zone_id))
    db.flush()
