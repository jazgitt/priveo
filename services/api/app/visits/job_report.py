"""Operations > Reports: which service was completed, per vehicle and day. Read only."""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.customers.models import Customer, Subscription, Vehicle
from app.identity.service import User
from app.platform.clock import today_ist
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling.models import Job, Schedule, Visit

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])

MAX_DAYS = 31
_EXT, _INT, _SPA = "Cleaning-External", "Cleaning-Internal", "Deep Spa"


class StatusReportRow(BaseModel):
    vehicle_id: uuid.UUID
    registration: str
    customer_name: str
    # Date (yyyy-mm-dd) to "EXT", "INT", "Both" or "SPA" (plus "+SPA" when a Deep Spa was also done).
    cells: dict[str, str]


class StatusReport(BaseModel):
    dates: list[date]
    rows: list[StatusReportRow]


def cell_label(services: set[str]) -> str:
    """The mark for the completed services of one vehicle on one day."""
    base = ("Both" if {_EXT, _INT} <= services else "EXT" if _EXT in services
            else "INT" if _INT in services else "")
    spa = "SPA" if _SPA in services else ""
    return "+".join(p for p in (base, spa) if p)


@router.get("/job-status-report", response_model=StatusReport)
def job_status_report(
    date_from: date,
    date_to: date,
    society_id: uuid.UUID | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if date_from > date_to:
        raise ApiError("validation_failed", "The last date must follow the first date.", 422)
    if (date_to - date_from).days + 1 > MAX_DAYS:
        raise ApiError("validation_failed", f"Choose a period of at most {MAX_DAYS} days.", 422)
    q = (
        select(Job.service, Job.status, Visit.date, Vehicle, Customer)
        .join(Visit, Visit.id == Job.visit_id)
        .join(Schedule, Schedule.id == Visit.schedule_id)
        .join(Vehicle, Vehicle.id == Visit.vehicle_id)
        .join(Customer, Customer.id == Vehicle.customer_id)
        .where(Visit.date >= date_from, Visit.date <= date_to)
    )
    if society_id:
        q = q.where(Schedule.society_id == society_id)
    done: dict[tuple[uuid.UUID, date], set[str]] = {}
    people: dict[uuid.UUID, tuple[Vehicle, Customer]] = {}
    for service, status, day, vehicle, customer in db.execute(q):
        people[vehicle.id] = (vehicle, customer)
        if status == "Completed":
            done.setdefault((vehicle.id, day), set()).add(service)
    rows = []
    for vid, (v, c) in people.items():
        cells = {d.isoformat(): cell_label(s) for (x, d), s in done.items() if x == vid}
        rows.append(StatusReportRow(
            vehicle_id=vid, registration=v.registration or "", customer_name=f"{c.first_name} {c.last_name}".strip(),
            cells={d: m for d, m in cells.items() if m}))
    rows.sort(key=lambda r: (r.registration, str(r.vehicle_id)))
    n = (date_to - date_from).days + 1
    return StatusReport(dates=[date_from + timedelta(days=i) for i in range(n)], rows=rows)


class CutoffRow(BaseModel):
    vehicle_id: uuid.UUID
    customer_name: str
    model: str
    registration: str
    # "HH:MM", or empty when the subscription has no cutoff.
    exterior_cutoff: str
    # A weekday, "Custom" or empty.
    interior_preferred_day: str


class CutoffReport(BaseModel):
    as_of: date
    rows: list[CutoffRow]


@router.get("/cutoff-report", response_model=CutoffReport)
def cutoff_report(
    society_id: uuid.UUID | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Each active vehicle with its Exterior cutoff and Interior preferred day, as they
    stand on the day the report is run."""
    q = (
        select(Vehicle, Customer, Subscription)
        .join(Customer, Customer.id == Vehicle.customer_id)
        .join(Subscription, Subscription.vehicle_id == Vehicle.id)
        .where(Vehicle.active.is_(True), Subscription.status == "Active")
    )
    if society_id:
        q = q.where(func.coalesce(Vehicle.society_id, Customer.society_id) == society_id)
    rows = [
        CutoffRow(
            vehicle_id=v.id, customer_name=f"{c.first_name} {c.last_name}".strip(),
            model=" ".join(p for p in (v.make, v.model) if p), registration=v.registration or "",
            exterior_cutoff=s.cutoff_time.strftime("%H:%M") if s.cutoff_time else "",
            interior_preferred_day=s.interior_day or "")
        for v, c, s in db.execute(q)
    ]
    rows.sort(key=lambda r: (r.exterior_cutoff == "", r.exterior_cutoff, r.registration))
    return CutoffReport(as_of=today_ist(), rows=rows)
