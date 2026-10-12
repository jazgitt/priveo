"""What a customer reads of their own vehicles and visits (HOME-03, HOME-04,
CAL-01, CAL-02, CAL-05, SVC-01 to SVC-09, HIST-01, HIST-02, VEH-02, VEH-03,
VEH-06)."""
import calendar
import uuid
from collections.abc import Callable
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customer_reads.calendar_view import CalendarView
from app.customer_reads.repository import (
    TERMINAL_VISIT_STATUSES,
    Job,
    Visit,
    VisitReadRepository,
)
from app.customer_reads.schemas import (
    CalendarMonth,
    HistoryItem,
    HistoryMetaOut,
    JobOut,
    NextServiceItem,
    ProofOut,
    TodayCleanOut,
    VehicleDetail,
    VehicleSummary,
    VisitChecklistItem,
    VisitDetail,
    VisitRatingGiven,
)
from app.customers.models import Customer, Subscription, Vehicle
from app.customers.service import show_registration, show_time
from app.directory.models import Society
from app.media.service import has_confirmed, vehicle_photo_urls
from app.media.store import ObjectStore, get_object_store
from app.platform import clock
from app.platform.errors import ApiError
from app.support.models import VisitRating

# How far ahead the Home card looks for the next visit.
NEXT_SERVICE_DAYS = 60
# History pages are read this many at a time when looking for the oldest month.
_META_PAGE = 100


def _month_range(month: str) -> tuple[date, date]:
    try:
        year, number = (int(p) for p in month.split("-"))
        first = date(year, number, 1)
    except ValueError:
        raise ApiError("validation_failed", "Month must look like 2026-11.", 422,
                       {"month": "Use yyyy-mm."}) from None
    return first, date(year, number, calendar.monthrange(year, number)[1])


class CustomerReads:
    def __init__(self, db: Session, visits: VisitReadRepository,
                 store: ObjectStore | None = None,
                 now_fn: Callable[[], datetime] | None = None):
        self._db = db
        self._visits = visits
        self._store = store or get_object_store()
        self._view = CalendarView(db, visits, now_fn or (lambda: clock.now_ist()))

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
            date(year, number, 1)
        except ValueError:
            raise ApiError("validation_failed", "Month must look like 2026-11.", 422,
                           {"month": "Use yyyy-mm."}) from None
        ids = self._scope(login_id, vehicle_id)
        return self._view.month(year, number, ids, self._owned_by_id(login_id))

    def _owned_by_id(self, login_id: uuid.UUID):
        return {str(v.id): (v, s) for v, s in self._owned(self._customer(login_id))}

    def next_services(self, login_id: uuid.UUID, today: date) -> list[NextServiceItem]:
        """The next visit that is not over, for each of the customer's vehicles.
        Without a planned visit, the next day the subscription implies."""
        ids = self._scope(login_id, None)
        return self._view.next_services(today, ids, self._owned_by_id(login_id))

    # Visit details and history ----------------------------------------------------

    @staticmethod
    def _finished_at(visit: Visit, jobs: list[Job]) -> datetime | None:
        """The finish time of a Completed visit: its last job's finish."""
        if visit.status != "Completed":
            return None
        times = [j.finished_at for j in jobs if j.finished_at is not None]
        return max(times) if times else None

    def _ratings(self, customer: Customer, visit_ids: list[str]) -> dict[str, VisitRating]:
        if not visit_ids:
            return {}
        rows = self._db.scalars(select(VisitRating).where(
            VisitRating.customer_id == customer.id, VisitRating.visit_id.in_(visit_ids)))
        return {r.visit_id: r for r in rows}

    def visit_detail(self, login_id: uuid.UUID, visit_id: str) -> VisitDetail:
        customer = self._customer(login_id)
        owned = {str(v.id): v for v, _ in self._owned(customer)}
        visit = self._visits.visit(visit_id)
        # A visit of someone else's vehicle is the same as no visit.
        if visit is None or visit.vehicle_id not in owned:
            raise ApiError("visit_not_found", "This visit was not found.", 404)
        vehicle = owned[visit.vehicle_id]
        jobs = self._jobs_by_visit([visit])[visit.id]
        society = self._db.get(Society, vehicle.society_id or customer.society_id).name
        given = self._ratings(customer, [visit.id]).get(visit.id)
        return VisitDetail(
            id=visit.id, vehicle_id=visit.vehicle_id,
            vehicle_registration=show_registration(vehicle.registration),
            vehicle_model=vehicle.model, date=visit.date, status=visit.status,
            finished_at=self._finished_at(visit, jobs),
            rating=(VisitRatingGiven(rating=given.rating, tags=list(given.tags or []))
                    if given else None),
            jobs=[JobOut(
                id=j.id, service=j.service, status=j.status,
                proof=[ProofOut(kind=p.kind, url=p.url, stage=p.stage, taken_at=p.taken_at)
                       for p in j.proof],
                crew_name=j.crew_name, crew_society=society if j.crew_name else "",
                started_at=j.started_at, finished_at=j.finished_at,
                checklist=[VisitChecklistItem(key=c.key, label=c.label,
                                              checked_at=c.checked_at) for c in j.checklist],
                checklist_done=sum(1 for c in j.checklist if c.checked_at is not None),
                checklist_total=len(j.checklist)) for j in jobs])

    def history(self, login_id: uuid.UUID, vehicle_id: str | None, limit: int,
                offset: int, month: str | None = None) -> list[HistoryItem]:
        customer = self._customer(login_id)
        start, end = _month_range(month) if month is not None else (None, None)
        visits = self._visits.history(self._scope(login_id, vehicle_id),
                                      TERMINAL_VISIT_STATUSES, limit, offset, start, end)
        jobs = self._jobs_by_visit(visits)
        ratings = self._ratings(customer, [v.id for v in visits])
        return [HistoryItem(
            visit_id=v.id, vehicle_id=v.vehicle_id, date=v.date, status=v.status,
            services=[j.service for j in jobs[v.id]],
            photo_count=sum(1 for j in jobs[v.id] for p in j.proof if p.kind == "photo"),
            finished_at=self._finished_at(v, jobs[v.id]),
            rating=ratings[v.id].rating if v.id in ratings else None)
            for v in visits]

    def history_meta(self, login_id: uuid.UUID, vehicle_id: str | None) -> HistoryMetaOut:
        """Member-since and the months the history covers (HIST-02)."""
        customer = self._customer(login_id)
        ids = self._scope(login_id, vehicle_id)
        starts = [s.first_service_date for _, s in self._owned(customer)
                  if s is not None and s.first_service_date is not None]
        since = min(starts) if starts else customer.created_at.date()
        newest = self._visits.history(ids, TERMINAL_VISIT_STATUSES, 1, 0)
        oldest = None
        offset = 0
        while newest:
            page = self._visits.history(ids, TERMINAL_VISIT_STATUSES, _META_PAGE, offset)
            if not page:
                break
            oldest = page[-1]
            offset += _META_PAGE
        return HistoryMetaOut(
            member_since=since,
            latest_month=newest[0].date.strftime("%Y-%m") if newest else None,
            earliest_month=oldest.date.strftime("%Y-%m") if oldest else None)

    def today(self, login_id: uuid.UUID, today: date) -> list[TodayCleanOut]:
        """Each vehicle's visit that was Completed today (HOME-03)."""
        customer = self._customer(login_id)
        ids = self._scope(login_id, None)
        visits = [v for v in self._visits.visits_in_range(ids, today, today)
                  if v.status == "Completed"]
        jobs = self._jobs_by_visit(visits)
        ratings = self._ratings(customer, [v.id for v in visits])
        return [TodayCleanOut(
            vehicle_id=v.vehicle_id, visit_id=v.id, date=v.date,
            finished_at=self._finished_at(v, jobs[v.id]),
            checks_done=sum(1 for j in jobs[v.id] for c in j.checklist
                            if c.checked_at is not None),
            checks_total=sum(len(j.checklist) for j in jobs[v.id]),
            photo_count=sum(1 for j in jobs[v.id] for p in j.proof if p.kind == "photo"),
            rating=ratings[v.id].rating if v.id in ratings else None) for v in visits]

    # Vehicles -----------------------------------------------------------------

    @staticmethod
    def _summary(vehicle: Vehicle, sub: Subscription | None, society: str,
                 photo_url: str | None = None) -> VehicleSummary:
        return VehicleSummary(
            id=str(vehicle.id), registration=show_registration(vehicle.registration),
            model=vehicle.model, society=society,
            subscription_status=sub.status if sub else None, photo_url=photo_url)

    def vehicles(self, login_id: uuid.UUID) -> list[VehicleSummary]:
        customer = self._customer(login_id)
        owned = self._owned(customer)
        photos = vehicle_photo_urls(self._db, self._store, [v.id for v, _ in owned])
        return [self._summary(v, s,
                self._db.get(Society, v.society_id or customer.society_id).name,
                photos.get(v.id)) for v, s in owned]

    def vehicle(self, login_id: uuid.UUID, vehicle_id: str) -> VehicleDetail:
        customer = self._customer(login_id)
        society = self._db.get(Society, customer.society_id).name
        for v, s in self._owned(customer):
            if str(v.id) == vehicle_id:
                society = self._db.get(Society, v.society_id or customer.society_id).name
                photo = vehicle_photo_urls(self._db, self._store, [v.id]).get(v.id)
                return VehicleDetail(
                    **self._summary(v, s, society, photo).model_dump(),
                    make=v.make, variant=v.variant, category=v.category,
                    parking_basement=v.parking_basement, parking_number=v.parking_number,
                    parking="-".join(p for p in (v.parking_basement, v.parking_number) if p),
                    rc_status=("Verified" if v.rc_verified else "Uploaded"
                               if v.rc_upload_id or has_confirmed(self._db, f"rc/{v.id}")
                               else "Not uploaded"),
                    monthly_price_rupees=s.monthly_price_rupees if s else None,
                    cutoff_time=show_time(s.cutoff_time) if s else None,
                    interior_day=s.interior_day if s else None)
        raise ApiError("vehicle_not_found", "This vehicle was not found.", 404)
