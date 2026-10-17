import uuid
from datetime import date, datetime

from sqlalchemy import JSON, CheckConstraint, Date, ForeignKey, String, UniqueConstraint, Uuid
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
    # The society the crew member belongs to today (ADM-CRW-13). It follows the
    # latest `CrewSocietyAssignment` that has taken effect.
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    # One entry for each weekday: {"day", "working", "start", "end"} (ADM-CRW-04).
    working_hours: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class CrewSocietyAssignment(Base):
    """One stay of a crew member in a society, from `effective_from` until the
    next assignment starts (ADM-CRW-13, ADM-CRW-22). The first row is the
    society they were onboarded into. Rows are only added, never edited, so the
    past associations never change. A row dated in the future is a move that
    has not happened yet and can be cancelled."""

    __tablename__ = "crew_society_assignments"
    __table_args__ = (
        UniqueConstraint("crew_id", "effective_from", name="uq_crew_society_from"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    crew_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crew_members.id"), index=True)
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"))
    effective_from: Mapped[date] = mapped_column(Date)
    # For a Trainee: the Member of the new society they are paired with.
    paired_member_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crew_members.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
