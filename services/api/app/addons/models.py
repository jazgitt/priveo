import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

ADDON_STATUSES = ("Requested", "Scheduled", "Completed", "Cancelled", "Missed")  # ADD-07


class AddonBooking(Base):
    """A Deep Spa request made in the app or taken by the admin (ADD-04). The
    older `addon_requests` table holds the migrated history; this one holds
    what is requested from now on, with its status and its payment."""

    __tablename__ = "addon_bookings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"))
    service: Mapped[str] = mapped_column(String(40))
    # A customer without a subscription (ADD-14). How these are paid is open (ADD-15).
    standalone: Mapped[bool] = mapped_column(Boolean, default=False)
    proposed_date: Mapped[date] = mapped_column(Date)
    finish_by: Mapped[time] = mapped_column(Time)
    requested_date: Mapped[date | None] = mapped_column(Date)
    requested_finish_by: Mapped[time | None] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(12), default="Requested")
    price_rupees: Mapped[int | None] = mapped_column(Integer)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id"))
    # Standalone only: how Priveo reaches the customer to agree the rest.
    contact_mobile: Mapped[str] = mapped_column(String(10), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    cancelled_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
