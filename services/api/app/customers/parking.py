"""A vehicle's parking slot on a day, with temporary and permanent changes
(S-07, ADM-CUS-27, CRW-SCH-17). The admin sets a change; the crew job card and
the admin schedule show the slot that is valid for the job's date."""
import uuid
from collections.abc import Iterable
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Customer, Vehicle, VehicleParkingChange
from app.directory import lookup
from app.directory.models import DirectoryAudit
from app.identity.service import User
from app.platform.clock import today_ist
from app.platform.db import get_db, utcnow
from app.platform.deps import require_role
from app.platform.errors import ApiError

admin = APIRouter(prefix="/v1/admin", tags=["customer-administration"])

Slot = tuple[str, str]


def label(slot: Slot) -> str:
    return "-".join(p for p in slot if p)


def covers(change: VehicleParkingChange, day: date) -> bool:
    return (change.cancelled_at is None and change.start_date <= day
            and (change.end_date is None or day <= change.end_date))


def slots(db: Session, pairs: Iterable[tuple[Vehicle, date]]) -> dict[tuple[uuid.UUID, date], Slot]:
    """The slot of each (vehicle, day): the latest change that covers the day, else
    the vehicle's own slot."""
    pairs = list(pairs)
    ids = {v.id for v, _ in pairs}
    changes: dict[uuid.UUID, list[VehicleParkingChange]] = {}
    if ids:
        for c in db.scalars(
            select(VehicleParkingChange)
            .where(VehicleParkingChange.vehicle_id.in_(ids),
                   VehicleParkingChange.cancelled_at.is_(None))
            .order_by(VehicleParkingChange.created_at.desc(), VehicleParkingChange.id)
        ):
            changes.setdefault(c.vehicle_id, []).append(c)
    out: dict[tuple[uuid.UUID, date], Slot] = {}
    for vehicle, day in pairs:
        hit = next((c for c in changes.get(vehicle.id, []) if covers(c, day)), None)
        out[(vehicle.id, day)] = ((hit.basement, hit.number) if hit
                                  else (vehicle.parking_basement, vehicle.parking_number))
    return out


class ParkingChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    basement: str
    number: str = Field(min_length=1, max_length=20)
    from_date: date
    # Empty: permanent from `from_date`.
    to_date: date | None = None
    note: str = Field(default="", max_length=160)


def _row(c: VehicleParkingChange, today: date) -> dict:
    if c.cancelled_at is not None:
        state = "Cancelled"
    elif c.end_date is not None and c.end_date < today:
        state = "Ended"
    elif c.start_date > today:
        state = "Upcoming"
    else:
        state = "Current"
    return {
        "id": str(c.id), "basement": c.basement, "number": c.number,
        "from_date": c.start_date.isoformat(),
        "to_date": c.end_date.isoformat() if c.end_date else None,
        "kind": "Temporary" if c.end_date else "Permanent",
        "note": c.note, "state": state, "created_at": c.created_at,
    }


def _vehicle(db: Session, vehicle_id: uuid.UUID) -> Vehicle:
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise ApiError("not_found", "Vehicle not found.", 404)
    return v


@admin.get("/vehicles/{vehicle_id}/parking-changes")
def list_changes(vehicle_id: uuid.UUID, user: User = Depends(require_role("admin")),
                 db: Session = Depends(get_db)):
    """The vehicle's own slot, the slot valid today and every change, newest first."""
    v = _vehicle(db, vehicle_id)
    today = today_ist()
    rows = db.scalars(
        select(VehicleParkingChange).where(VehicleParkingChange.vehicle_id == v.id)
        .order_by(VehicleParkingChange.created_at.desc(), VehicleParkingChange.id)).all()
    return {
        "base": label((v.parking_basement, v.parking_number)),
        "today": label(slots(db, [(v, today)])[(v.id, today)]),
        "changes": [_row(c, today) for c in rows],
    }


@admin.post("/vehicles/{vehicle_id}/parking-changes", status_code=201)
def add_change(vehicle_id: uuid.UUID, body: ParkingChangeIn,
               user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    v = _vehicle(db, vehicle_id)
    society_id = v.society_id
    if society_id is None:
        society_id = db.get(Customer, v.customer_id).society_id
    if body.basement.upper() not in lookup.society_basements(db, society_id):
        raise ApiError("validation_failed", "Choose a basement.", 422)
    number = body.number.strip()
    if not number:
        raise ApiError("validation_failed", "Enter the parking number.", 422)
    if body.to_date is not None and body.to_date < body.from_date:
        raise ApiError("validation_failed", "The end date is before the start date.", 422)
    if (body.to_date or body.from_date) < today_ist():
        raise ApiError("validation_failed", "The change is already over. Choose a later date.", 422)
    change = VehicleParkingChange(
        vehicle_id=v.id, basement=body.basement.upper(), number=number,
        start_date=body.from_date, end_date=body.to_date, note=body.note.strip(),
        created_by=user.id)
    db.add(change)
    db.flush()
    db.add(DirectoryAudit(
        admin_login_id=user.id, entity="parking", entity_id=str(v.id), action="create",
        detail={"change": str(change.id), "slot": label((change.basement, change.number)),
                "from": change.start_date.isoformat(),
                "to": change.end_date.isoformat() if change.end_date else None}))
    db.commit()
    return _row(change, today_ist())


@admin.delete("/vehicles/{vehicle_id}/parking-changes/{change_id}", status_code=204)
def cancel_change(vehicle_id: uuid.UUID, change_id: uuid.UUID,
                  user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Cancel a change. It stays in the history."""
    change = db.get(VehicleParkingChange, change_id)
    if change is None or change.vehicle_id != vehicle_id:
        raise ApiError("not_found", "Parking change not found.", 404)
    if change.cancelled_at is None:
        change.cancelled_at = utcnow()
        db.add(DirectoryAudit(
            admin_login_id=user.id, entity="parking", entity_id=str(vehicle_id),
            action="cancel", detail={"change": str(change.id)}))
        db.commit()
