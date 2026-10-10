import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

ROLES = ("customer", "crew", "admin")


class Login(Base):
    """One person's sign-in. The role decides which screens they see."""

    __tablename__ = "logins"
    __table_args__ = (
        CheckConstraint("role in ('customer', 'crew', 'admin')", name="logins_role_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String(16))
    # Lower-case email (customer), 10-digit mobile (crew) or user ID (admin).
    login_id: Mapped[str] = mapped_column(String(254), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    # Empty until a password is set. Only the Argon2 hash is stored.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    password_changed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    # Crew and admin: locked until the password is reset (CRW-ACC-07).
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Customer: blocked for a while after too many wrong attempts (AUTH-13).
    blocked_until: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class AuthSession(Base):
    """One signed-in phone or browser. Ending it signs that device out at once."""

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    channel: Mapped[str] = mapped_column(String(8))  # mobile | web
    # SHA-256 of the current refresh token. The token itself is never stored.
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    ended_reason: Mapped[str | None] = mapped_column(String(32))


class AuthEvent(Base):
    """A record of sign-in activity: who, what and when."""

    __tablename__ = "auth_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
