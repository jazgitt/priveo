import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

ROLES = ("customer", "crew", "admin")


class Login(Base):
    """One person's sign-in. The role decides which screens they see."""

    __tablename__ = "logins"
    __table_args__ = (
        CheckConstraint("role in ('customer', 'crew', 'admin')", name="logins_role_check"),
        # The same mobile number can be a customer and a crew member: each has
        # its own login, and the sign-in screen says which one is meant.
        UniqueConstraint("role", "login_id", name="uq_logins_role_login_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String(16))
    # 10-digit mobile (customer and crew) or user ID (admin).
    login_id: Mapped[str] = mapped_column(String(254))
    display_name: Mapped[str] = mapped_column(String(120))
    # The password (crew, admin) or the 6-digit MPIN (customer). Only the
    # Argon2 hash is stored.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    password_changed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Customer: the MPIN is still the one the admin gave (the last 6 digits of
    # the mobile number), so the customer must choose their own before using
    # anything else. The API enforces it.
    must_change_mpin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    alert_email: Mapped[str] = mapped_column(String(254), default="", server_default="")
    alert_email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    # Crew and admin: locked until the admin lifts it. Only logins locked
    # before blocks became timed (CRW-ACC-07, revised 18-Oct-26) still have it.
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Blocked for a while after too many wrong attempts: a customer for 15
    # minutes (AUTH-13), crew and admin for longer each time (CRW-ACC-07).
    blocked_until: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class AuthSession(Base):
    """One signed-in phone or browser. Ending it signs that device out at once."""

    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    channel: Mapped[str] = mapped_column(String(8))  # mobile | web
    device_name: Mapped[str] = mapped_column(String(120), default="")
    platform: Mapped[str] = mapped_column(String(20), default="")
    app_version: Mapped[str] = mapped_column(String(40), default="")
    # SHA-256 of the current refresh token. The token itself is never stored.
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # The hash the current one replaced, and when. A phone that presents it long
    # after the swap means the token was copied (security review R-07).
    previous_refresh_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    rotated_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
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


class EmailCode(Base):
    """A 6-digit code emailed to a customer who forgot the MPIN (AUTH-16).
    Only a keyed hash is stored. (The "password_token" columns hold the
    one-time token that lets the customer set the new MPIN.)"""

    __tablename__ = "email_codes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
    wrong_attempts: Mapped[int] = mapped_column(Integer, default=0)
    verified_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    # After a correct code: the hash of the one-time token that lets the
    # customer set a password, and when that token stops working.
    password_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    password_token_expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    # Set when the code can no longer be used: used, replaced or cancelled.
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    ended_reason: Mapped[str | None] = mapped_column(String(32))
