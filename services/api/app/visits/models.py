"""What the crew record while doing a job (CRW-SVC, CRW-CNC, CRW-MGR).

The visits and jobs themselves belong to the scheduling module
(`app.scheduling.models`). These tables hang off its jobs.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

import app.scheduling.models  # noqa: F401  (the jobs table these link to)
from app.platform.db import Base, UtcDateTime, utcnow


class JobChecklistProgress(Base):
    """One checked item of a job's checklist, with the time (CRW-SVC-03).
    An item with no row is not checked. The items themselves are the service's
    checklist in `app.directory.lookup.checklist_for`."""

    __tablename__ = "job_checklist_progress"
    __table_args__ = (UniqueConstraint("job_id", "item_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(40))
    checked_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    checked_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"))


class JobOutcome(Base):
    """Why a job did not get done: could not complete (CRW-CNC-02) or skipped
    by a Manager (CRW-MGR-02)."""

    __tablename__ = "job_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), unique=True)
    kind: Mapped[str] = mapped_column(String(24))  # could_not_complete | skipped
    reason_key: Mapped[str | None] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(Text, default="")
    upload_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    by_login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"))
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class JobReassignment(Base):
    """A Manager moved a job to another crew member (CRW-MGR-03)."""

    __tablename__ = "job_reassignments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), index=True)
    from_crew_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scheduling_crew.id"))
    to_crew_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scheduling_crew.id"))
    by_login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"))
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class CrewPhoto(Base):
    """A crew member's profile photo: a confirmed upload (CRW-PRF-02)."""

    __tablename__ = "crew_photos"

    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), primary_key=True)
    upload_id: Mapped[uuid.UUID] = mapped_column(Uuid)


class JobTiming(Base):
    """When the crew started and finished a job (CRW-SVC-09). The scheduling
    jobs table holds the planned time only."""

    __tablename__ = "job_timings"

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"), primary_key=True)
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class CrewManagerChange(Base):
    """A Manager marked attendance or changed working hours for a crew member
    of their society: who and when (CRW-MGR-04, CRW-MGR-05)."""

    __tablename__ = "crew_manager_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), index=True)
    crew_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scheduling_crew.id"), index=True)
    by_login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"))
    kind: Mapped[str] = mapped_column(String(12))  # attendance | hours
    # Attendance: the first date changed. Hours: the day the change was made.
    on_date: Mapped[date] = mapped_column(Date)
    detail: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
