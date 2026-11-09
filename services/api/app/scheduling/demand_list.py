"""The Demand tab on the capacity page (P3-2.2): the jobs due on one date, for
one service or all of them, in the order the admin reads them. Read only.

Order: Exteriors by cutoff, then Interiors by cutoff, then the other services
by cutoff. A job with no cutoff (an add-on has none yet, ADM-SCH-30) goes last
in its group. Skipped demand is left out, as the capacity totals leave it out."""
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Vehicle
from app.scheduling import service
from app.scheduling.outcomes import SHORT_NAME

GROUP_RANK = {"Cleaning-External": 0, "Cleaning-Internal": 1}
GROUP_LABEL = {"Cleaning-External": "EXT", "Cleaning-Internal": "INT"}
OTHER_GROUP = "Other"


@dataclass(frozen=True)
class DemandRow:
    """One job that is due, as the Demand tab lists it."""

    group: str
    service: str
    service_label: str
    vehicle_id: uuid.UUID
    registration: str
    vehicle: str
    cutoff: str | None
    source: str


def hhmm(minute: int | None) -> str | None:
    if minute is None:
        return None
    return f"{minute // 60:02d}:{minute % 60:02d}"


def sort_key(row: DemandRow, cutoff_minute: int | None) -> tuple:
    """Group first (EXT, INT, other), then cutoff with no cutoff last, then a
    fixed tie-break so the order is the same on every call."""
    rank = GROUP_RANK.get(row.service, len(GROUP_RANK))
    return (rank, cutoff_minute is None, cutoff_minute or 0, row.registration, row.service,
            str(row.vehicle_id))


def due_on(db: Session, society_id: uuid.UUID, day: date, service_name: str | None = None) -> list[DemandRow]:
    """The jobs due on `day` for the site, optionally for one service only, in
    the Demand tab's order."""
    demand = [d for d in service.build_demand(db, society_id, [day])
              if not d.skipped and (service_name is None or d.service == service_name)]
    vehicles = {
        v.id: v for v in db.scalars(
            select(Vehicle).where(Vehicle.id.in_({d.vehicle_id for d in demand})))
    } if demand else {}
    keyed = []
    for d in demand:
        veh = vehicles.get(d.vehicle_id)
        row = DemandRow(
            group=GROUP_LABEL.get(d.service, OTHER_GROUP),
            service=d.service,
            service_label=SHORT_NAME.get(d.service, d.service),
            vehicle_id=d.vehicle_id,
            registration=veh.registration if veh else "",
            vehicle=service.vehicle_label(veh) if veh else "",
            cutoff=hhmm(d.finish_by),
            source="Add-on" if (d.addon_request_id or d.addon_booking_id) else "Subscription",
        )
        keyed.append((sort_key(row, d.finish_by), row))
    keyed.sort(key=lambda pair: pair[0])
    return [row for _, row in keyed]
