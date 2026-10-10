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
