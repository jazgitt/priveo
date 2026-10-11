from datetime import date

from pydantic import BaseModel


class ProofOut(BaseModel):
    kind: str
    url: str


class JobOut(BaseModel):
    id: str
    service: str
    status: str
    proof: list[ProofOut]


class CalendarJob(BaseModel):
    service: str
    status: str
    # Only once the schedule is frozen and the job has a crew member (CAL-10).
    crew_name: str | None = None
    start_time: str | None = None  # HH:MM
    end_time: str | None = None


class CalendarVisit(BaseModel):
    # Empty for a projected day: the scheduler has not planned it yet.
    visit_id: str | None
    vehicle_id: str
    date: date
    # Scheduled, In progress, Completed, Skipped, Missed, Paused or Projected.
    status: str
    services: list[str]
    # visit (planned by the scheduler) or projected (from the subscription).
    source: str = "visit"
    # What the day card shows: status, or Covered, Rescheduled or
    # Change requested (CAL-07, CAL-09).
    state: str = "Scheduled"
    # The cutoff time that holds for the date, HH:MM (CAL-06).
    cutoff_time: str | None = None
    # A cutoff change asked for after the freeze, waiting for Priveo (CAL-07).
    change_requested: bool = False
    requested_cutoff_time: str | None = None
    skip_id: str | None = None
    # A skip, an un-skip or a cutoff change is still allowed (SCHED-01).
    can_change: bool = False
    # The schedule is frozen, so a cutoff change is only a request.
    frozen: bool = False
    # A Missed visit: the date its work was done on (CAL-09).
    covered_on: date | None = None
    rescheduled_on: date | None = None
    jobs: list[CalendarJob] = []
    crew_name: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class CalendarRenewal(BaseModel):
    vehicle_id: str
    date: date


class CalendarMonth(BaseModel):
    month: str  # yyyy-mm
    visits: list[CalendarVisit]
    # The billing renewal dates that fall in the month (PAUSE-02).
    renewals: list[CalendarRenewal] = []


class NextServiceItem(BaseModel):
    vehicle_id: str
    # Empty when the day is projected from the subscription.
    visit_id: str | None
    date: date
    service: str
    status: str
    services: list[str] = []
    source: str = "visit"
    cutoff_time: str | None = None
    crew_name: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class VisitDetail(BaseModel):
    id: str
    vehicle_id: str
    vehicle_registration: str
    vehicle_model: str
    date: date
    status: str
    jobs: list[JobOut]


class HistoryItem(BaseModel):
    visit_id: str
    vehicle_id: str
    date: date
    status: str
    services: list[str]
    photo_count: int


class VehicleSummary(BaseModel):
    id: str
    registration: str
    model: str
    society: str
    subscription_status: str | None


class VehicleDetail(VehicleSummary):
    make: str
    variant: str
    category: str
    parking_basement: str
    parking_number: str
    parking: str
    monthly_price_rupees: int | None
    cutoff_time: str | None
    interior_day: str | None
