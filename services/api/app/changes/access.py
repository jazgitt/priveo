import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Customer, Subscription, Vehicle
from app.platform.errors import ApiError


def customer_of(db: Session, login_id: uuid.UUID) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.login_id == login_id))
    if customer is None:
        raise ApiError("no_customer_record",
                       "Your details are not set up yet. Contact Priveo.", 404)
    return customer


def parse_id(value: str, what: str = "record") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ApiError("not_found", f"That {what} was not found.", 404) from None


def _vehicle_row(db: Session, vehicle_id: str) -> tuple[Vehicle, Subscription | None]:
    vehicle = db.get(Vehicle, parse_id(vehicle_id, "vehicle"))
    if vehicle is None:
        raise ApiError("not_found", "That vehicle was not found.", 404)
    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == vehicle.id))
    return vehicle, sub


def owned_vehicle(db: Session, login_id: uuid.UUID,
                  vehicle_id: str) -> tuple[Customer, Vehicle, Subscription | None]:
    """A customer's own vehicle. Another customer's is reported as not found."""
    customer = customer_of(db, login_id)
    vehicle, sub = _vehicle_row(db, vehicle_id)
    if vehicle.customer_id != customer.id:
        raise ApiError("not_found", "That vehicle was not found.", 404)
    return customer, vehicle, sub


def any_vehicle(db: Session, vehicle_id: str) -> tuple[Customer, Vehicle, Subscription | None]:
    """For the admin."""
    vehicle, sub = _vehicle_row(db, vehicle_id)
    return db.get(Customer, vehicle.customer_id), vehicle, sub
