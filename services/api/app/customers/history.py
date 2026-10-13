"""Imported service records: preserve unknown completion/date/proof honestly."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import AddonRequest, Customer, Vehicle
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError

router = APIRouter()


def imported_history(db, customer_id):
    out = []
    for row in db.scalars(select(AddonRequest).where(
        AddonRequest.customer_id == customer_id, AddonRequest.source_ref.is_not(None)
    ).order_by(AddonRequest.service_date.desc().nulls_last(), AddonRequest.id)):
        vehicle = db.get(Vehicle, row.vehicle_id) if row.vehicle_id else None
        if vehicle and vehicle.customer_id != customer_id:
            vehicle = None
        out.append({"id": str(row.id), "source": "imported", "vehicle_id": str(vehicle.id)
                    if vehicle else None, "vehicle": vehicle.registration or vehicle.model
                    if vehicle else "Unmatched vehicle",
                    "service": row.service, "date": row.service_date,
                    "payment_status": row.payment_status, "amount_rupees": row.price_rupees,
                    "notes": row.notes, "completion_status": None, "proof": []})
    return out


@router.get("/history/imported")
def my_imported_history(user: User = Depends(require_role("customer")),
                        db: Session = Depends(get_db)):
    customer = db.scalar(select(Customer).where(Customer.login_id == user.id))
    if customer is None:
        raise ApiError("not_found", "Customer not found.", 404)
    return imported_history(db, customer.id)
