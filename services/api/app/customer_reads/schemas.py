from datetime import date, datetime

from pydantic import BaseModel


class ProofOut(BaseModel):
    kind: str  # photo | video
    # A signed, expiring read URL. On the dev server it is relative to the API.
    url: str
    # Before | During | After. The gallery marks After photos (SVC-04, SVC-05).
    stage: str | None = None
    taken_at: datetime | None = None


class VisitChecklistItem(BaseModel):
    key: str
    label: str
    checked_at: datetime | None = None


class JobOut(BaseModel):
    id: str
    service: str
    status: str
    proof: list[ProofOut]
    # The crew card of this job (SVC-02): first name only, never a mobile
    # number, and no crew rating.
    crew_name: str | None = None
    crew_society: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
    checklist: list[VisitChecklistItem] = []
    checklist_done: int = 0
    checklist_total: int = 0


class VisitRatingGiven(BaseModel):
    rating: int
    tags: list[str]


class CalendarVisit(BaseModel):
    visit_id: str
    vehicle_id: str
    date: date
    status: str
    services: list[str]


class CalendarMonth(BaseModel):
    month: str  # yyyy-mm
    visits: list[CalendarVisit]


class NextServiceItem(BaseModel):
    vehicle_id: str
    visit_id: str
    date: date
    service: str
    status: str


class VisitDetail(BaseModel):
    id: str
    vehicle_id: str
    vehicle_registration: str
    vehicle_model: str
    date: date
    status: str
    jobs: list[JobOut]
    # When the last job of a Completed visit finished (SVC-01).
    finished_at: datetime | None = None
    # The rating the customer gave this visit, or None (SVC-07).
    rating: VisitRatingGiven | None = None


class HistoryItem(BaseModel):
    visit_id: str
    vehicle_id: str
    date: date
    status: str
    services: list[str]
    photo_count: int
    finished_at: datetime | None = None
    rating: int | None = None


class HistoryMetaOut(BaseModel):
    """What the history footer and month paging need (HIST-02)."""

    member_since: date | None
    # The newest and oldest month (yyyy-mm) with a visit that is over.
    latest_month: str | None
    earliest_month: str | None


class TodayCleanOut(BaseModel):
    """A visit that finished today, for the Home strip (HOME-03)."""

    vehicle_id: str
    visit_id: str
    date: date
    finished_at: datetime | None
    checks_done: int
    checks_total: int
    photo_count: int
    # The rating already given, so Home can hide "Rate today's clean".
    rating: int | None = None


class VehicleSummary(BaseModel):
    id: str
    registration: str
    model: str
    society: str
    subscription_status: str | None
    # A signed, expiring read URL of the vehicle photo, or None (VEH-01).
    photo_url: str | None = None


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
