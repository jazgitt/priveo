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
    event,
    false,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

SERVICES = ("Cleaning-External", "Cleaning-Internal", "Deep Spa")
# Minutes of crew time each job takes (ADM-SVS-09).
DURATIONS = {"Cleaning-External": 20, "Cleaning-Internal": 20, "Deep Spa": 120}
JOB_STATUSES = ("Scheduled", "In progress", "Completed", "Skipped", "Could not complete")
CREW_ROLES = ("Member", "Trainee", "Manager")


class SchedulingCrew(Base):
    """A crew member as the scheduler sees them: the society, the role, the
    pairing, the working hours and whether they count. This is the one
    operational record: `CrewService` creates it with the crew member and
    keeps it in step (ADM-CRW). Trainees count zero capacity and are never
    assigned (ADM-CAP-02, ADM-CRW-14)."""

    __tablename__ = "scheduling_crew"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), unique=True)
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), index=True)
    role: Mapped[str] = mapped_column(String(8), default="Member")
    # The working window, in minutes after midnight. Used on every day when
    # `working_hours` is empty. Otherwise the earliest start and latest end of
    # the working days, as a summary.
    start_minute: Mapped[int] = mapped_column(Integer, default=360)
    end_minute: Mapped[int] = mapped_column(Integer, default=660)
    # One entry for each weekday: {"day", "working", "start", "end"} (ADM-CRW-04).
    working_hours: Mapped[list | None] = mapped_column(JSON)
    # A Trainee is paired with a Member and sees that Member's jobs (CRW-SCH-10).
    paired_member_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scheduling_crew.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SchedulingCrewException(Base):
    """A day a crew member is away (Sick, Leave) or starts late (ADM-CRW-08)."""

    __tablename__ = "scheduling_crew_exceptions"
    __table_args__ = (UniqueConstraint("crew_id", "on_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    crew_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scheduling_crew.id"), index=True)
    on_date: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(16))  # Sick | Leave | Late start
    # Late start only: the minute the crew member can begin.
    from_minute: Mapped[int | None] = mapped_column(Integer)


class Schedule(Base):
    """The plan for one society and one period. Draft until frozen (ADM-SCH-11)."""

    __tablename__ = "schedules"
    __table_args__ = (UniqueConstraint("society_id", "start_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(8), default="Draft")  # Draft | Frozen
    frozen_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    frozen_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class AutomaticPlanningRun(Base):
    """One automatic attempt per society/period; retries retain their draft."""
    __tablename__ = "automatic_planning_runs"
    __table_args__ = (UniqueConstraint("society_id", "start_date", name="auto_planning_once"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("schedules.id"))
    status: Mapped[str] = mapped_column(String(16), default="Pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    error: Mapped[str] = mapped_column(String(160), default="")


class Visit(Base):
    """One vehicle on one date. Completed only when all its jobs are done or
    skipped (CLAUDE.md domain facts)."""

    __tablename__ = "visits"
    __table_args__ = (
        UniqueConstraint("schedule_id", "vehicle_id", "date", "addon_key", name="uq_visit_service"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.id"), index=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="Scheduled")
    # Empty for the plan visit, booking UUID for a separate add-on visit.
    addon_key: Mapped[str] = mapped_column(String(64), default="")


class Job(Base):
    """One service on a visit, with its own crew member and time (CRW-SCH-05)."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("visits.id"), index=True)
    service: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(20), default="Scheduled")
    duration_minutes: Mapped[int] = mapped_column(Integer)
    # Empty while the job is Unscheduled or on the Needs scheduling list.
    crew_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scheduling_crew.id"), index=True)
    start_minute: Mapped[int | None] = mapped_column(Integer)
    # The customer's cutoff time, in minutes after midnight.
    finish_by_minute: Mapped[int | None] = mapped_column(Integer)
    addon_request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("addon_requests.id"))
    addon_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("addon_bookings.id"), index=True
    )
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id"), unique=True
    )
    # Set when the admin placed or removed it by hand. A re-run keeps it (ADM-SCH-14).
    manual: Mapped[bool] = mapped_column(Boolean, default=False)
    # Placed, but it finishes after the customer's cutoff time (ADM-SCH-07).
    late: Mapped[bool] = mapped_column(Boolean, default=False)
    # Why it is Unscheduled (ADM-SCH-08).
    note: Mapped[str] = mapped_column(Text, default="")
    # Position in the crew member's day (1, 2, ...), the order they must work
    # in (S-13, C-01). Null while the job has no crew member.
    sequence: Mapped[int | None] = mapped_column(Integer)
    # The admin released this job from the queue lock (C-04, B-06).
    queue_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Immutable issued definition. Legacy backfill is explicitly identified.
    checklist_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)


@event.listens_for(Job, "before_insert")
def snapshot_job_checklist(_mapper, connection, job):
    """Capture every creation path, including scheduling and operations retries."""
    if job.checklist_snapshot is not None:
        return
    from app.directory import defaults
    from app.directory.models import ChecklistItem

    rows = connection.execute(select(
        ChecklistItem.key, ChecklistItem.label, ChecklistItem.active
    ).where(ChecklistItem.service == job.service).order_by(
        ChecklistItem.sort_order, ChecklistItem.key
    )).all()
    items = ([{"key": r.key, "label": r.label} for r in rows if r.active]
             if rows else [{"key": k, "label": label}
                           for k, label in defaults.CHECKLISTS.get(job.service, ())])
    job.checklist_snapshot = {"legacy": False, "items": items}


class SchedulingEvent(Base):
    """Who froze, unfroze, changed or re-ran a schedule, and when (ADM-SCH-19)."""

    __tablename__ = "scheduling_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.id"), index=True)
    admin_login_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    kind: Mapped[str] = mapped_column(String(24))
    detail: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
