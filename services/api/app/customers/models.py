import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, Time, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class Customer(Base):
    """A customer the admin created (AUTH-14). Signs in with the email."""

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), unique=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80), default="")
    # Lower case. An email belongs to one customer only (ADM-CUS-03).
    email: Mapped[str] = mapped_column(String(254), unique=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    # A contact number. It is not checked for duplicates (ADM-CUS-03).
    mobile: Mapped[str] = mapped_column(String(10))
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), index=True)
    flat: Mapped[str] = mapped_column(String(40), default="")
    # Optional. The society's own details fill them in the portal until the admin changes them.
    address_line1: Mapped[str] = mapped_column(String(120), default="", server_default="")
    address_line2: Mapped[str] = mapped_column(String(120), default="", server_default="")
    # Set when the customer accepts the terms at first sign-in (AUTH-04).
    terms_accepted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    # Set when the customer confirms the review of their details (ONB-25).
    onboarding_confirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # "admin" for customers made in the portal, "migration" for the first load.
    source: Mapped[str] = mapped_column(String(16), default="admin")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    # Immutable once added; legacy records fall back to the customer's society.
    society_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("societies.id"), index=True)
    photo_upload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_uploads.id", name="fk_vehicle_photo", use_alter=True))
    rc_upload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_uploads.id", name="fk_vehicle_rc", use_alter=True))
    rc_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # Upper case, no spaces. Empty only for migrated vehicles whose number
    # was missing or incomplete; the admin fills it in.
    registration: Mapped[str | None] = mapped_column(String(12), unique=True)
    make: Mapped[str] = mapped_column(String(60), default="")
    model: Mapped[str] = mapped_column(String(80))
    variant: Mapped[str] = mapped_column(String(80), default="")
    category: Mapped[str] = mapped_column(String(40), default="")
    parking_basement: Mapped[str] = mapped_column(String(20), default="")
    parking_number: Mapped[str] = mapped_column(String(20), default="")
    # What the source said, when it did not fit the fields above.
    notes: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # The row this came from in a one-time load, so the load can run again.
    source_ref: Mapped[str | None] = mapped_column(String(40), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class VehicleParkingChange(Base):
    """A change of a vehicle's parking slot (S-07, ADM-CUS-27). With an end date it
    is temporary; without one it is permanent from the start date. A cancelled
    change stays as history. For a day, the latest change that covers it wins."""

    __tablename__ = "vehicle_parking_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"), index=True)
    basement: Mapped[str] = mapped_column(String(20))
    number: Mapped[str] = mapped_column(String(20))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(160), default="", server_default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    cancelled_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class Subscription(Base):
    """One per vehicle (ADM-CUS-05)."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"), unique=True)
    # Empty for migrated subscriptions until the plans are set up.
    plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plans.id"))
    pending_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plans.id"))
    pending_from: Mapped[date | None] = mapped_column(Date)
    # Whole rupees, GST included. Kept on the subscription, so a customer
    # keeps the price they joined at.
    monthly_price_rupees: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="Active")
    # The 30-day billing cycle counts from this date.
    first_service_date: Mapped[date] = mapped_column(Date)
    cutoff_time: Mapped[time | None] = mapped_column(Time)
    interior_day: Mapped[str | None] = mapped_column(String(9))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class PlanChange(Base):
    """One plan change of a subscription, with the plan it left and the plan it
    goes to (S-11, ADM-SUB-08). Scheduled until its date comes and the daily
    job applies it; a cancelled change stays as history. The names and prices
    are kept as they were when the change was made."""

    __tablename__ = "subscription_plan_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id"), index=True)
    from_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plans.id"))
    from_plan_name: Mapped[str] = mapped_column(String(80), default="")
    from_price_rupees: Mapped[int | None] = mapped_column(Integer)
    to_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id"))
    to_plan_name: Mapped[str] = mapped_column(String(80))
    to_price_rupees: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date)
    # True when the admin chose the date; false when it is the next renewal.
    chosen: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    status: Mapped[str] = mapped_column(String(10), default="Scheduled")  # Scheduled | Applied | Cancelled
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class AddonRequest(Base):
    """A Deep Spa or other add-on bought separately from the plan."""

    __tablename__ = "addon_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    # Empty when a migrated row could not be matched to one of the vehicles.
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"))
    service: Mapped[str] = mapped_column(String(40))
    price_rupees: Mapped[int | None] = mapped_column(Integer)
    service_date: Mapped[date | None] = mapped_column(Date)
    # Due, Over due, Initiated or Received. Empty when the source did not say.
    payment_status: Mapped[str | None] = mapped_column(String(16))
    notes: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str | None] = mapped_column(String(40), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class EmailChange(Base):
    """A new email waiting for its 6-digit code (ACC-08). The old email stays
    the sign-in until the code is entered. Only a keyed hash is stored."""

    __tablename__ = "email_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    new_email: Mapped[str] = mapped_column(String(254))
    code_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
    wrong_attempts: Mapped[int] = mapped_column(Integer, default=0)
    # Set when the code is used, replaced or given up on.
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
