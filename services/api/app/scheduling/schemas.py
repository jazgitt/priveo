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


class RunResponse(BaseModel):
    schedules: list[RunResult]


class MoveRequest(BaseModel):
    # Empty takes the job off its crew member.
    crew_id: uuid.UUID | None = None
    # Minutes after midnight.
    start_minute: int | None = Field(default=None, ge=0, lt=1440)


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


class DayCapacity(BaseModel):
    date: date
    capacity_minutes: int
    demand_minutes: int
    scheduled_minutes: int
    over_capacity: bool
    crew: list[CrewCapacityLine] = []
    demand: list[DemandLine] = []
    availability: list[CrewDayAvailability] = []


class SchedulingCrewOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    start_minute: int
    end_minute: int


class AdminJob(BaseModel):
    id: uuid.UUID
    visit_id: uuid.UUID
    schedule_id: uuid.UUID
    schedule_status: str
    date: date
    vehicle_id: uuid.UUID
    registration: str
    vehicle: str
    # The parking place, for example "B1-24" (basement and number).
    parking: str = ""
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
    reason: str
    # A skipped job only: "Skipped" or "Paused", and by whom (ADM-SCH-36).
    skip_kind: str = ""
    skip_reason: str = ""
    # Derived outcome of the whole visit (Scheduled, Completed, Partially
    # Completed, Not Completed, Rescheduled, Cancelled) with planned and
    # delivered services, so a partial visit is visible on the Board.
    visit_outcome: str = "Scheduled"
    planned_services: list[str] = []
    delivered_services: list[str] = []


class Board(BaseModel):
    schedule: ScheduleOut
    days: list[DayCapacity]
    crew: list[SchedulingCrewOut]
    jobs: list[AdminJob]


class NeedsScheduling(BaseModel):
    jobs: list[AdminJob]
    pending_addons: list[dict] = Field(default_factory=list)


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
    society: str
    service: str
    status: str
    start_time: str | None
    end_time: str | None
    finish_by: str | None


class CrewDay(BaseModel):
    date: date
    society: str
    total: int
    done: int
    left: int
    jobs: list[CrewDayJob]
