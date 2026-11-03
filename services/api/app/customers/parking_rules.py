"""What a parking entry may be (owner, 3 Nov 2026).

The number is free text, up to the column's 60 characters, for example
"214" or "Under D25". The basement may be left empty when the vehicle has a
zone; a vehicle without a zone still needs a basement of its society.
"""
from sqlalchemy.orm import Session

from app.directory import lookup

PARKING_NUMBER_MAX = 60


def clean_number(text: str | None) -> str | None:
    """The number with its spaces tidied, or None when it is empty or too long."""
    value = " ".join((text or "").split())
    return value if 0 < len(value) <= PARKING_NUMBER_MAX else None


def basement_ok(db: Session, society_id, basement: str, *, has_zone: bool) -> bool:
    if not basement:
        return has_zone
    return basement in lookup.society_basements(db, society_id)


def zone_names(db: Session, vehicles) -> dict:
    """The zone name of each vehicle that has one, by vehicle ID."""
    from sqlalchemy import select

    from app.directory.models import Zone

    ids = {v.zone_id for v in vehicles if v.zone_id}
    if not ids:
        return {}
    names = dict(db.execute(select(Zone.id, Zone.name).where(Zone.id.in_(ids))).all())
    return {v.id: names[v.zone_id] for v in vehicles if v.zone_id in names}


def with_zone(zone: str | None, parking: str) -> str:
    """The zone and the parking slot shown together, for example "Zone 3 · B2-14".
    Either may be missing (owner, 3 Nov 2026: zone and parking always appear together)."""
    return " · ".join(p for p in (zone, parking) if p)
