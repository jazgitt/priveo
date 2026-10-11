import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, ForeignKey, String, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow


class ScheduleChange(Base):
    """A skip, a pause or a cutoff-time change for one vehicle (SKIP-, PAUSE-,
    CAL-08). The visits themselves belong to the scheduling module; this is
    the customer's (or admin's) request and its outcome."""

    __tablename__ = "schedule_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"), index=True)
    # skip | pause | cutoff
    kind: Mapped[str] = mapped_column(String(8))
    # A skip or a cutoff change is one date: start_date == end_date.
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    # Only for kind "cutoff".
    cutoff_time: Mapped[time | None] = mapped_column(Time)
    # skip, pause: Active | Cancelled | Merged (a skip taken into a pause).
    # cutoff: Applied | Requested (the schedule was frozen, CAL-07).
    status: Mapped[str] = mapped_column(String(12), default="Active")
    actor: Mapped[str] = mapped_column(String(8))  # customer | admin
    actor_login_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    # The app's retry key, so a retry on a poor network never doubles it.
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
