import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow


class Notification(Base):
    """One message in a person's in-app inbox (NOTIF-02)."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    # service_completed, service_skipped, complaint_update, renewal_reminder,
    # monthly_check_in.
    event: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text, default="")
    # What the message is about, so the app can open it (a visit ID).
    visit_id: Mapped[str | None] = mapped_column(String(64))
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
