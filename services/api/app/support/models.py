"""Tables of the support module: complaints, feedback, ratings, check-ins and
admin alerts.

A visit is defined by another slice, so a visit is referred to by a plain
`visit_id` string with no foreign key.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

# ISS-01. A fixed list in MVP.
ISSUE_CATEGORIES = (
    "Cleaning quality", "Missed service", "Damage concern", "Crew behaviour", "Billing", "Other")
# CMP-02, ADM-CMP-03.
COMPLAINT_STATUSES = ("Raised", "In progress", "Resolved")

OPTION_KINDS = ("feedback_category", "positive_tag", "checkin_category")


class SupportOption(Base):
    """One entry of an admin-editable list (ADM-FDB-06): a feedback category
    (FDBK-06), a positive rating tag (SVC-11) or a check-in category (CHK-03).
    A deactivated entry is hidden from customers but never deleted
    (ADM-FDB-07)."""

    __tablename__ = "support_options"
    __table_args__ = (UniqueConstraint("kind", "name", name="support_options_kind_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(300), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Shown as #C-NNNN (ISS-06).
    number: Mapped[int] = mapped_column(Integer, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    visit_id: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text)
    # Storage keys of photos already uploaded by the media slice (ISS-04).
    photo_keys: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="Raised")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    # Set once the 4-hour alert went out (ADM-CMP-08), so it goes out once.
    overdue_alerted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class ComplaintUpdate(Base):
    """One entry in a complaint's thread: an admin's status change or note, or
    the customer's message."""

    __tablename__ = "complaint_updates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), index=True)
    # "customer" or "admin".
    author_role: Mapped[str] = mapped_column(String(16))
    # Which admin made it (ADM-CMP-07).
    author_login_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    note: Mapped[str] = mapped_column(Text, default="")
    # The status the complaint moved to, when this entry changed it.
    status: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class Feedback(Base):
    """General feedback from the side tab or Support (FDBK-02)."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    # The name as it was when given, so a renamed category stays readable.
    category: Mapped[str | None] = mapped_column(String(80))
    rating: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    testimonial_permission: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class VisitRating(Base):
    """The customer's rating of a visit as a whole (SVC-07). It is never tied to
    a crew member (CRW-RAT-01)."""

    __tablename__ = "visit_ratings"
    __table_args__ = (UniqueConstraint("customer_id", "visit_id", name="visit_ratings_once"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    visit_id: Mapped[str] = mapped_column(String(64), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    # Positive tags at 5 stars, issue tags below (SVC-11, SVC-14).
    tags: Mapped[list] = mapped_column(JSON, default=list)
    comment: Mapped[str] = mapped_column(Text, default="")
    testimonial_permission: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class CheckIn(Base):
    """A monthly check-in, saved against the subscription and the renewal cycle
    it was given in (CHK-04)."""

    __tablename__ = "checkins"
    __table_args__ = (
        UniqueConstraint("subscription_id", "cycle_start", name="checkins_once_a_cycle"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    subscription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    # First day of the 30-day cycle that this check-in is about.
    cycle_start: Mapped[date] = mapped_column(Date)
    # [{"category": "Value for money", "rating": 4}, ...]
    answers: Mapped[list] = mapped_column(JSON, default=list)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class AdminAlert(Base):
    """An alert for the admin (ADM-ACC-09, ADM-SCH-24). Shown in the app and the
    web bell with an unread count. Other modules raise alerts through
    `app.support.alerts.raise_alert`."""

    __tablename__ = "admin_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(500), default="")
    # What it is about, so the app can open it: "complaint" and an ID.
    ref_type: Mapped[str | None] = mapped_column(String(24))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, index=True)
    read_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class AdminAlertEmail(Base):
    """Durable recipient delivery; inbox alerts survive provider failures."""
    __tablename__ = "admin_alert_emails"
    __table_args__ = (UniqueConstraint("alert_id", "login_id", name="admin_alert_email_once"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("admin_alerts.id"), index=True)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    recipient_email: Mapped[str] = mapped_column(String(254))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    stopped_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
