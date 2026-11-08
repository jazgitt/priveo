import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    # Empty means every active society (ADM-SCH-01).
    society_id: uuid.UUID | None = None
    start_date: date
    # A week by default (ADM-SCH-09).
    days: int | None = Field(default=None, ge=1, le=31)


class RunResult(BaseModel):
    schedule_id: uuid.UUID
    society_id: uuid.UUID
    status: str
    placed: int
    unscheduled: int
    late: int
    # SCHS-21: unassigned Exteriors, the cars they belong to and their minutes.
    unassigned_exteriors: int | None = None
    shortfall_cars: int | None = None
    shortfall_minutes: int | None = None
    # SCHS-40: Interiors deferred or not planned, jobs placed outside the
    # cleaner's home zone, and missed breaks.
    deferred_interiors: int = 0
    cross_zone_jobs: int = 0
    missed_breaks: int = 0


class RunResponse(BaseModel):
    schedules: list[RunResult]


class MoveRequest(BaseModel):
    # Empty takes the job off its crew member.
    crew_id: uuid.UUID | None = None
    # Minutes after midnight.
    start_minute: int | None = Field(default=None, ge=0, lt=1440)
    # SCHS-22: place the job although it breaks a rule. Without
    # it a breach is answered with a placement_warning that lists the breaches.
    override: bool = False


class UnfreezeRequest(BaseModel):
    code: str


class ScheduleOut(BaseModel):
    id: uuid.UUID
    society_id: uuid.UUID
    society_name: str
    start_date: date
    end_date: date
    status: str
    frozen_at: datetime | None
    freeze_deadline: datetime


class CrewCapacityLine(BaseModel):
    """What one crew member adds to a day's capacity."""

    name: str
    role: str
    minutes: int
    # For example "05:00-13:00, 17:00-19:00".
    slots: str


class DemandLine(BaseModel):
    """Work due on a day for one service, from subscriptions or add-ons."""

    service: str
    source: str  # "Subscription" or "Add-on"
    jobs: int
    minutes: int


class CrewDayWindow(BaseModel):
    start: int  # minutes after midnight
    end: int


class CrewDayAvailability(BaseModel):
    """Whether a crew member can take work on a day, and why (ADM-SCH-32)."""

    crew_id: uuid.UUID
    status: str  # "Working", "Partial" (late start) or "Off"
    windows: list[CrewDayWindow]
    reason: str
    # The break to draw on the Board, in minutes after midnight (SCHS-35). Version 2 sites only.
    break_start: int | None = None
    break_end: int | None = None


class DayCapacity(BaseModel):
    date: date
    capacity_minutes: int
    demand_minutes: int
    scheduled_minutes: int
    over_capacity: bool
    # Version 2 sites (SCHS-34): the break taken out of capacity, and the free
    # minutes of the early band, available for onboarding.
    break_minutes: int = 0
    early_band_free_minutes: int = 0
    crew: list[CrewCapacityLine] = []
    demand: list[DemandLine] = []
    availability: list[CrewDayAvailability] = []


class ZoneRef(BaseModel):
    id: uuid.UUID
    name: str


class SchedulingCrewOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    start_minute: int
    end_minute: int
    # The home zones the planner uses (SCHS-29); a Trainee shows the Member's.
    home_zones: list[ZoneRef] = Field(default_factory=list)


class AdminJob(BaseModel):
    id: uuid.UUID
    visit_id: uuid.UUID
    schedule_id: uuid.UUID
    schedule_status: str
    date: date
    vehicle_id: uuid.UUID
    registration: str
    vehicle: str
    # The parking place, for example "B1-24" (basement and number), with the zone in
    # front when the vehicle has one: "Zone 3 · B1-24".
    parking: str = ""
    zone: str = ""
    customer_name: str
    service: str
    status: str
    duration_minutes: int
    crew_id: uuid.UUID | None
    crew_name: str | None
    start_minute: int | None
    start_time: str | None
    end_time: str | None
    finish_by: str | None
    late: bool
    manual: bool
    # Placed by hand with a crew member and start (item 15), and whether a run keeps it.
    placed_by_hand: bool = False
    hand_locked: bool = False
    reason: str
    # S-05: a moved service keeps both dates. `moved_to_date` is on the closed
    # original, `moved_from_date` on the job on the new date.
    moved_to_date: date | None = None
    moved_from_date: date | None = None
    # A skipped job only: "Skipped" or "Paused", and by whom (ADM-SCH-36).
    skip_kind: str = ""
    skip_reason: str = ""
    # Derived outcome of the whole visit (Scheduled, Completed, Partially
    # Completed, Not Completed, Rescheduled, Cancelled) with planned and
    # delivered services, so a partial visit is visible on the Board.
    visit_outcome: str = "Scheduled"
    planned_services: list[str] = []
    delivered_services: list[str] = []
    # Place in the crew member's day, and whether the admin unlocked it (S-13, C-04).
    sequence: int | None = None
    queue_unlocked: bool = False
    # SCHS-21: the code of the reason an unassigned job has no place.
    reason_code: str | None = None
    # SCHS-45: why the job sits outside its cleaner's home zone.
    cross_zone_reason: str | None = None
    # SCHS-22: the rules a job was placed against by hand and the admin confirmed; the Board marks it wine.
    hand_breaches: list[str] = []


class Board(BaseModel):
    schedule: ScheduleOut
    days: list[DayCapacity]
    crew: list[SchedulingCrewOut]
    jobs: list[AdminJob]


class NeedsScheduling(BaseModel):
    jobs: list[AdminJob]
    pending_addons: list[dict] = Field(default_factory=list)


class InteriorDayMissing(BaseModel):
    """A car whose plan includes Interior care but whose preferred Interior day is not set.
    Such a car is on the Needs Attention tab until the admin sets the day."""
    subscription_id: uuid.UUID
    vehicle_id: uuid.UUID
    registration: str
    customer_name: str
    vehicle: str
    plan_name: str


class FreezeDue(BaseModel):
    frozen: list[uuid.UUID]


class CustomerNextJob(BaseModel):
    job_id: uuid.UUID
    visit_id: uuid.UUID
    vehicle_id: uuid.UUID
    registration: str
    vehicle: str
    date: date
    service: str
    status: str
    # "HH:MM", empty until the job is assigned (CAL-10).
    start_time: str | None
    end_time: str | None
    crew_name: str | None
    # The customer's cutoff time, "HH:MM".
    finish_by: str | None


class CustomerNextService(BaseModel):
    job: CustomerNextJob | None


class CrewDayJob(BaseModel):
    id: uuid.UUID
    visit_id: uuid.UUID
    vehicle_id: uuid.UUID
    registration: str
    make: str
    model: str
    category: str
    parking_basement: str
    parking_number: str
    zone: str = ""
    society: str
    service: str
    status: str
    start_time: str | None
    end_time: str | None
    finish_by: str | None
    sequence: int | None = None
    locked: bool = False
    current: bool = False


class CrewDayBreak(BaseModel):
    start_time: str  # HH:MM
    end_time: str


class CrewDay(BaseModel):
    date: date
    society: str
    total: int
    done: int
    left: int
    jobs: list[CrewDayJob]
    # The break, shown as a block that holds no job (SCHS-35). Version 2 sites only.
    day_break: CrewDayBreak | None = None


class QueueReorder(BaseModel):
    crew_id: uuid.UUID
    date: date
    ordered_job_ids: list[uuid.UUID]
    reason: str


class QueueUnlock(BaseModel):
    reason: str


class QueueChange(BaseModel):
    message: str
    ordered_job_ids: list[uuid.UUID]
