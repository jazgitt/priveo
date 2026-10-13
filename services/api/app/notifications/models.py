import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow


class Notification(Base):
    """One message in a person's in-app inbox (NOTIF-02, CRW-NOT-01 to 05)."""

    __tablename__ = "notifications"
    __table_args__ = (
        # One message for each thing that happened, so a job that runs twice
        # does not tell the person twice.
        UniqueConstraint("login_id", "dedupe_key", name="notifications_dedupe_unique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    # See app.notifications.events for the list.
    event: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text, default="")
    # What the message is about, so the app can open it (a visit ID).
    visit_id: Mapped[str | None] = mapped_column(String(64))
    # The same, for things other than a visit: visit, payment, complaint,
    # checkin or job, with its ID.
    ref_type: Mapped[str | None] = mapped_column(String(24))
    ref_id: Mapped[str | None] = mapped_column(String(64))
    dedupe_key: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class DeviceToken(Base):
    """A phone that can receive push messages for a login."""

    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    token: Mapped[str] = mapped_column(String(512), unique=True)
    platform: Mapped[str] = mapped_column(String(16))  # android or ios
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class NotificationPreference(Base):
    """A customer's on/off switch for one event (SET-02). No row means on
    (SET-03). Only the customer events can be switched off."""

    __tablename__ = "notification_preferences"

    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), primary_key=True)
    event: Mapped[str] = mapped_column(String(40), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
