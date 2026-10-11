import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

PAYMENT_STATUSES = ("Due", "Over due", "Initiated", "Received")


class Payment(Base):
    """One amount a customer pays by UPI: a plan cycle or an add-on (PAY-09,
    ADM-PAY-10). The status is set by the backend; the app only shows it."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("subscription_id", "cycle_start", name="payments_cycle_unique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vehicles.id"), index=True)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subscriptions.id"))
    # Plan | Add-on
    kind: Mapped[str] = mapped_column(String(8))
    description: Mapped[str] = mapped_column(String(120))
    # Whole rupees, GST included.
    amount_rupees: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="Due")
    due_date: Mapped[date] = mapped_column(Date)
    # The 30 days this payment pays for (plan payments).
    cycle_start: Mapped[date | None] = mapped_column(Date)
    cycle_end: Mapped[date | None] = mapped_column(Date)
    # The day the payment became Over due. The 7 days to Inactive count from it.
    overdue_since: Mapped[date | None] = mapped_column(Date)
    initiated_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    received_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    # Set when an unpaid add-on is cancelled: it is no longer owed.
    voided_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class PaymentEvent(Base):
    """Every status change: who and when (ADM-PAY-05). No login means the backend."""

    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(10))
    to_status: Mapped[str] = mapped_column(String(10))
    by_login_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    note: Mapped[str] = mapped_column(String(200), default="")


class Invoice(Base):
    """A GST invoice for a Received payment (ADM-PAY-08, ADM-PAY-09)."""

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id"), unique=True)
    # PRV + MM + YY + last 4 of the mobile + 4 random digits.
    number: Mapped[str] = mapped_column(String(24), unique=True)
    issued_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    issued_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    amount_rupees: Mapped[int] = mapped_column(Integer)
    # What was invoiced, as it was on the day.
    customer_name: Mapped[str] = mapped_column(String(160))
    vehicle_label: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(String(120))


class MoneyAlert(Base):
    """An alert for the admin (ADM-PAY-11, ADM-SUB-03). Push, the web bell and
    email are delivered by the notifications module later; this is the record."""

    __tablename__ = "money_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # payment_initiated | auto_inactive
    kind: Mapped[str] = mapped_column(String(24))
    message: Mapped[str] = mapped_column(Text)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id"))
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("subscriptions.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class SubscriptionEvent(Base):
    """Every change of a subscription's status (ADM-SUB-05)."""

    __tablename__ = "subscription_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id"), index=True)
    from_status: Mapped[str] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16))
    by_login_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    reason: Mapped[str] = mapped_column(String(200), default="")
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
