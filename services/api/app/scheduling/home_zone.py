"""A cleaner's home zone (SCHS-29; SCHR-ZONE-01, -07, -09).

Edit surface only: nothing here plans a day. The home zone is a zone of the
cleaner's own society. Several cleaners may share one. A Trainee has none of
their own: it follows the paired Member (SCHR-ZONE-09, Derived)."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory.models import Zone
from app.platform.errors import ApiError
from app.scheduling.models import SchedulingCrew


def paired_member(db: Session, sc: SchedulingCrew) -> SchedulingCrew | None:
    if sc.role != "Trainee" or sc.paired_member_id is None:
        return None
    return db.get(SchedulingCrew, sc.paired_member_id)


def effective_zone_id(db: Session, sc: SchedulingCrew) -> uuid.UUID | None:
    """The zone the planner treats as home: own for a Member or Manager, the
    paired Member's for a Trainee."""
    if sc.role == "Trainee":
        mate = paired_member(db, sc)
        return mate.home_zone_id if mate else None
    return sc.home_zone_id


def zones_of(db: Session, society_id: uuid.UUID) -> list[Zone]:
    return list(db.scalars(select(Zone).where(
        Zone.society_id == society_id, Zone.active.is_(True)).order_by(Zone.name)))


def set_home_zone(db: Session, sc: SchedulingCrew, zone_id: uuid.UUID | None) -> None:
    """Sets or clears the home zone. Refuses a Trainee and a zone of another society."""
    if sc.role == "Trainee":
        raise ApiError("validation_failed", "A Trainee follows the paired Member's home zone.",
                       422, {"home_zone_id": "Set the home zone on the paired Member."})
    if zone_id is not None:
        zone = db.get(Zone, zone_id)
        if zone is None or zone.society_id != sc.society_id or not zone.active:
            raise ApiError("validation_failed", "Choose a zone of this crew member's society.",
                           422, {"home_zone_id": "Choose a zone of this society."})
    sc.home_zone_id = zone_id
