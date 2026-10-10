"""What a customer reads of their own vehicles and visits (HOME-04, CAL-01,
CAL-02, CAL-05, SVC-01, SVC-04, SVC-09, VEH-02, VEH-03, VEH-06)."""
import calendar
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customer_reads.repository import (
    TERMINAL_VISIT_STATUSES,
    Job,
    Visit,
    VisitReadRepository,
)
from app.customer_reads.schemas import (
    CalendarMonth,
    CalendarVisit,
    HistoryItem,
    JobOut,
    NextServiceItem,
    ProofOut,
    VehicleDetail,
    VehicleSummary,
    VisitDetail,
)
from app.customers.models import Customer, Subscription, Vehicle
from app.customers.service import show_registration, show_time
from app.directory.models import Society
from app.platform.errors import ApiError

# How far ahead the Home card looks for the next visit.
NEXT_SERVICE_DAYS = 60


class CustomerReads:
    def __init__(self, db: Session, visits: VisitReadRepository):
        self._db = db
        self._visits = visits

    def _customer(self, login_id: uuid.UUID) -> Customer:
        customer = self._db.scalar(select(Customer).where(Customer.login_id == login_id))
        if customer is None:
            raise ApiError("no_customer_record",
                           "Your details are not set up yet. Contact Priveo.", 404)
        return customer

    def _owned(self, customer: Customer) -> list[tuple[Vehicle, Subscription | None]]:
        rows = self._db.execute(
            select(Vehicle, Subscription)
            .outerjoin(Subscription, Subscription.vehicle_id == Vehicle.id)
            .where(Vehicle.customer_id == customer.id, Vehicle.active.is_(True))
            .order_by(Vehicle.created_at, Vehicle.source_ref, Vehicle.id)).all()
        # Vehicles with a subscription come first, as on Home.
        return sorted(((v, s) for v, s in rows), key=lambda pair: pair[1] is None)

    def _scope(self, login_id: uuid.UUID, vehicle_id: str | None) -> list[str]:
        """The vehicle IDs a read covers: one given vehicle, or all of them."""
        ids = [str(v.id) for v, _ in self._owned(self._customer(login_id))]
        if vehicle_id is None:
            return ids
        if vehicle_id not in ids:
            raise ApiError("vehicle_not_found", "This vehicle was not found.", 404)
        return [vehicle_id]

    def _jobs_by_visit(self, visits: list[Visit]) -> dict[str, list[Job]]:
        grouped: dict[str, list[Job]] = {v.id: [] for v in visits}
        for job in self._visits.jobs([v.id for v in visits]):
            grouped.setdefault(job.visit_id, []).append(job)
        return grouped

    # Calendar -----------------------------------------------------------------

    def calendar(self, login_id: uuid.UUID, month: str, vehicle_id: str | None) -> CalendarMonth:
        try:
            year, number = (int(p) for p in month.split("-"))
            first = date(year, number, 1)
        except ValueError:
            raise ApiError("validation_failed", "Month must look like 2026-11.", 422,
                           {"month": "Use yyyy-mm."}) from None
        last = date(year, number, calendar.monthrange(year, number)[1])
        visits = self._visits.visits_in_range(self._scope(login_id, vehicle_id), first, last)
        jobs = self._jobs_by_visit(visits)
        return CalendarMonth(month=f"{year:04d}-{number:02d}", visits=[
            CalendarVisit(visit_id=v.id, vehicle_id=v.vehicle_id, date=v.date, status=v.status,
                          services=[j.service for j in jobs[v.id]])
            for v in visits])

    def next_services(self, login_id: uuid.UUID, today: date) -> list[NextServiceItem]:
        """The next visit that is not over, for each of the customer's vehicles."""
        ids = self._scope(login_id, None)
        visits = self._visits.visits_in_range(ids, today, today + timedelta(NEXT_SERVICE_DAYS))
        jobs = self._jobs_by_visit(visits)
        result: dict[str, NextServiceItem] = {}
        for v in visits:
            if v.status in TERMINAL_VISIT_STATUSES or v.vehicle_id in result:
                continue
            service = jobs[v.id][0].service if jobs[v.id] else ""
            result[v.vehicle_id] = NextServiceItem(
                vehicle_id=v.vehicle_id, visit_id=v.id, date=v.date, service=service,
                status=v.status)
        return [result[i] for i in ids if i in result]

    # Visit details and history ----------------------------------------------------

    def visit_detail(self, login_id: uuid.UUID, visit_id: str) -> VisitDetail:
        owned = {str(v.id): v for v, _ in self._owned(self._customer(login_id))}
        visit = self._visits.visit(visit_id)
        # A visit of someone else's vehicle is the same as no visit.
        if visit is None or visit.vehicle_id not in owned:
            raise ApiError("visit_not_found", "This visit was not found.", 404)
        vehicle = owned[visit.vehicle_id]
        jobs = self._jobs_by_visit([visit])[visit.id]
        return VisitDetail(
            id=visit.id, vehicle_id=visit.vehicle_id,
            vehicle_registration=show_registration(vehicle.registration),
            vehicle_model=vehicle.model, date=visit.date, status=visit.status,
            jobs=[JobOut(id=j.id, service=j.service, status=j.status,
                         proof=[ProofOut(kind=p.kind, url=p.url) for p in j.proof])
                  for j in jobs])

    def history(self, login_id: uuid.UUID, vehicle_id: str | None, limit: int,
                offset: int) -> list[HistoryItem]:
        visits = self._visits.history(self._scope(login_id, vehicle_id),
                                      TERMINAL_VISIT_STATUSES, limit, offset)
        jobs = self._jobs_by_visit(visits)
        return [HistoryItem(
            visit_id=v.id, vehicle_id=v.vehicle_id, date=v.date, status=v.status,
            services=[j.service for j in jobs[v.id]],
            photo_count=sum(1 for j in jobs[v.id] for p in j.proof if p.kind == "photo"))
            for v in visits]

    # Vehicles -----------------------------------------------------------------

    @staticmethod
    def _summary(vehicle: Vehicle, sub: Subscription | None, society: str) -> VehicleSummary:
        return VehicleSummary(
            id=str(vehicle.id), registration=show_registration(vehicle.registration),
            model=vehicle.model, society=society,
            subscription_status=sub.status if sub else None)

    def vehicles(self, login_id: uuid.UUID) -> list[VehicleSummary]:
        customer = self._customer(login_id)
        society = self._db.get(Society, customer.society_id).name
        return [self._summary(v, s, society) for v, s in self._owned(customer)]

    def vehicle(self, login_id: uuid.UUID, vehicle_id: str) -> VehicleDetail:
        customer = self._customer(login_id)
        society = self._db.get(Society, customer.society_id).name
        for v, s in self._owned(customer):
            if str(v.id) == vehicle_id:
                return VehicleDetail(
                    **self._summary(v, s, society).model_dump(),
                    make=v.make, variant=v.variant, category=v.category,
                    parking_basement=v.parking_basement, parking_number=v.parking_number,
                    parking="-".join(p for p in (v.parking_basement, v.parking_number) if p),
                    monthly_price_rupees=s.monthly_price_rupees if s else None,
                    cutoff_time=show_time(s.cutoff_time) if s else None,
                    interior_day=s.interior_day if s else None)
        raise ApiError("vehicle_not_found", "This vehicle was not found.", 404)
