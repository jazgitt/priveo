import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    # Empty means every active society (ADM-SCH-01).
    society_id: uuid.UUID | None = None
    start_date: date
    # A week by default (ADM-SCH-09).
    days: int = Field(default=7, ge=1, le=31)


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


class DayCapacity(BaseModel):
    date: date
    capacity_minutes: int
    demand_minutes: int
    scheduled_minutes: int
    over_capacity: bool


class CrewOut(BaseModel):
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


class Board(BaseModel):
    schedule: ScheduleOut
    days: list[DayCapacity]
    crew: list[CrewOut]
    jobs: list[AdminJob]


class NeedsScheduling(BaseModel):
    jobs: list[AdminJob]


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
