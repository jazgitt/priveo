import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

CREW_ROLES = ("Manager", "Member", "Trainee")  # ADM-CRW-02


class CrewMember(Base):
    """A crew member the admin onboarded (ADM-CRW-01). Signs in with the mobile
    number, which is also the login ID (CRW-ACC-03). Whether they may sign in
    is `logins.active` (CRW-ACC-08)."""

    __tablename__ = "crew_members"
    __table_args__ = (
        CheckConstraint("role in ('Manager', 'Member', 'Trainee')",
                        name="crew_members_role_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    # One crew member per mobile number (ADM-CRW-06).
    mobile: Mapped[str] = mapped_column(String(10), unique=True)
    # Exactly one society, not changeable for now (ADM-CRW-13).
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    # One entry for each weekday: {"day", "working", "start", "end"} (ADM-CRW-04).
    working_hours: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
