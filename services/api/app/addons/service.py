"""Deep Spa requests (ADD-01 to ADD-10, ADD-14, ADD-15)."""

import uuid
from datetime import date, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.addons.models import ADDON_STATUSES, AddonBooking
from app.addons.schemas import (
    AddonChangeIn,
    AddonOffer,
    AddonOut,
    AddonsOut,
    AdminAddonIn,
    AdminAddonOut,
    StandaloneIn,
)
from app.billing.config import MoneySettings
from app.billing.models import Payment
from app.billing.service import BillingService, customer_name, vehicle_label
from app.changes.access import owned_vehicle, parse_id
from app.changes.cycle import paused_days
from app.changes.rules import Clock, is_open, require_open, today_of
from app.customers.models import Customer, Subscription, Vehicle
from app.customers.service import read_cutoff
from app.directory import lookup
from app.directory.models import AddonCatalogueItem, Society
from app.identity.models import Login
from app.notifications import emit  # notify hook
from app.platform.db import utcnow
from app.platform.errors import ApiError
from app.scheduling.models import Job, Schedule, SchedulingCrew, Visit

OPEN_STATUSES = ("Requested", "Scheduled")


def _time(text: str | None, field: str = "finish_by") -> time:
    value = read_cutoff(text)  # 30-minute steps, like the cutoff time
    if value is None:
        raise ApiError(
            "validation_failed",
            "Choose a finish-by time in 30-minute steps.",
            422,
            {field: "invalid"},
        )
    return value


class AddonService:
    def __init__(
        self, db: Session, now_fn: Clock, settings: MoneySettings, billing: BillingService
    ):
        self._db = db
        self._now = now_fn
        self._settings = settings
        self._billing = billing

    @property
    def _hour(self) -> int:
        return lookup.setting(self._db, "schedule.customer_change_hour")

    def offers(self) -> list[AddonOffer]:
        all_rows = list(
            self._db.scalars(
                select(AddonCatalogueItem).order_by(
                    AddonCatalogueItem.sort_order, AddonCatalogueItem.name
                )
            )
        )
        if all_rows:
            return [
                AddonOffer(
                    code=r.code,
                    service=r.service,
                    name=r.name,
                    description=r.description,
                    price_rupees=r.price_rupees,
                    list_price_rupees=r.list_price_rupees,
                    duration_minutes=r.duration_minutes,
                )
                for r in all_rows
                if r.active
            ]
        price, list_price = lookup.addon_price(self._db)
        return [
            AddonOffer(
                service="Deep Spa",
                name="Deep Spa",
                description="A two-hour deep clean of the inside and outside of the car.",
                price_rupees=price,
                list_price_rupees=list_price,
                duration_minutes=120,
            )
        ]

    def _offer(self, addon: str, service: str) -> AddonOffer:
        """The add-on being bought: by its catalogue ID, or else the first one for
        the service (older apps send only the service)."""
        for o in self.offers():
            if (o.code == addon) if addon else (o.service == service):
                return o
        raise ApiError(
            "validation_failed", "That add-on is not offered.", 422,
            {"addon" if addon else "service": "unknown"},
        )

    def _payment_status(self, b: AddonBooking) -> str | None:
        if b.payment_id is None:
            return None
        p = self._db.get(Payment, b.payment_id)
        return p.status if p and p.voided_at is None else None

    def _out(self, b: AddonBooking) -> AddonOut:
        assignment = self._db.execute(
            select(Job, Visit, Login.display_name)
            .join(Visit, Visit.id == Job.visit_id)
            .outerjoin(SchedulingCrew, SchedulingCrew.id == Job.crew_id)
            .outerjoin(Login, Login.id == SchedulingCrew.login_id)
            .where(
                Job.addon_booking_id == b.id, Visit.date == b.proposed_date, Job.status != "Skipped"
            )
            .limit(1)
        ).first()
        return AddonOut(
            id=str(b.id),
            service=b.service,
            addon_name=b.addon_name or b.service,
            vehicle_id=str(b.vehicle_id) if b.vehicle_id else None,
            standalone=b.standalone,
            date=b.proposed_date,
            finish_by=b.finish_by.strftime("%H:%M"),
            status=b.status,
            price_rupees=b.price_rupees,
            payment_id=str(b.payment_id) if b.payment_id else None,
            payment_status=self._payment_status(b),
            can_change=b.status in OPEN_STATUSES
            and is_open(b.proposed_date, self._now(), self._hour),
            created_at=b.created_at,
            requested_date=b.requested_date,
            requested_finish_by=b.requested_finish_by.strftime("%H:%M")
            if b.requested_finish_by
            else None,
            change_requested=b.requested_date is not None,
            crew_name=assignment[2] if assignment else None,
            start_time=(
                f"{assignment[0].start_minute // 60:02d}:{assignment[0].start_minute % 60:02d}"
            )
            if assignment and assignment[0].start_minute is not None
            else None,
            visit_id=str(assignment[1].id) if assignment else None,
        )

    def mine(self, customer: Customer) -> AddonsOut:
        rows = self._db.scalars(
            select(AddonBooking)
            .where(AddonBooking.customer_id == customer.id)
            .order_by(AddonBooking.created_at.desc())
        )
        return AddonsOut(offers=self.offers(), requests=[self._out(b) for b in rows])

    # --- the customer ------------------------------------------------------

    def request(
        self,
        customer: Customer,
        vehicle: Vehicle,
        sub: Subscription | None,
        body_service: str,
        day: date,
        finish_by: str,
        key: str | None,
        admin: bool = False,
        addon: str = "",
    ) -> AddonOut:
        again = self._by_key(customer, key)
        if again is not None:
            return self._out(again)
        now = self._now()
        today = today_of(now)
        # ADD-01: for a vehicle whose subscription is Active. A pause blocks only
        # the dates it covers, so a spa can be booked for a date after it.
        if sub is None or sub.status != "Active":
            raise ApiError(
                "subscription_not_active",
                "Add-ons are for a vehicle with an active subscription.",
                409,
            )
        if day in paused_days(self._db, vehicle.id):
            raise ApiError(
                "inside_pause",
                "The service is paused on that date. Choose a date after the pause ends.",
                409,
                {"date": "inside_pause"},
            )
        offer = self._offer(addon, body_service)
        price = offer.price_rupees
        finish = _time(finish_by)
        require_open(day, now, bound=not admin, hour=self._hour)
        payment = self._billing.open_addon_payment(
            customer, vehicle, f"{offer.name} on {day.strftime('%d-%b-%y')}", price
        )
        b = AddonBooking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service=offer.service,
            addon_code=offer.code,
            addon_name=offer.name,
            proposed_date=day,
            finish_by=finish,
            price_rupees=price,
            payment_id=payment.id,
            idempotency_key=key or None,
        )
        self._db.add(b)
        self._db.commit()
        from app.scheduling.service import reconcile_vehicle

        reconcile_vehicle(self._db, vehicle.id)
        return self._out(b)

    def standalone(
        self, customer: Customer, login_id: uuid.UUID, body: StandaloneIn, key: str | None,
        *, admin: bool = False
    ) -> AddonOut:
        """P12: identical Spa payment/scheduling lifecycle, without a plan."""
        again = self._by_key(customer, key)
        if again is not None:
            return self._out(again)
        offer = self._offer(body.addon, body.service)
        price = offer.price_rupees
        finish = _time(body.finish_by)
        _, vehicle, sub = owned_vehicle(self._db, login_id, body.vehicle_id)
        if sub is not None:
            raise ApiError("has_subscription", "Book Spa through the active-subscription add-on flow.", 409)
        require_open(body.date, self._now(), bound=not admin, hour=self._hour)
        payment = self._billing.open_addon_payment(
            customer, vehicle, f"{offer.name} on {body.date:%d-%b-%y}", price)
        mobile = (body.contact_mobile or customer.mobile).strip()
        b = AddonBooking(
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            service=offer.service,
            addon_code=offer.code,
            addon_name=offer.name,
            standalone=True,
            proposed_date=body.date,
            finish_by=finish,
            contact_mobile=mobile,
            notes=body.notes.strip(),
            price_rupees=price,
            payment_id=payment.id,
            idempotency_key=key or None,
        )
        self._db.add(b)
        self._db.commit()
        from app.scheduling.service import reconcile_vehicle
        reconcile_vehicle(self._db, vehicle.id)
        return self._out(b)

    def _by_key(self, customer: Customer, key: str | None) -> AddonBooking | None:
        if not key:
            return None
        found = self._db.scalar(select(AddonBooking).where(AddonBooking.idempotency_key == key))
        if found is not None and found.customer_id != customer.id:
            raise ApiError("idempotency_conflict", "That request key was used already.", 409)
        return found

    def _own(self, customer: Customer, addon_id: str) -> AddonBooking:
        b = self._db.get(AddonBooking, parse_id(addon_id, "request"))
        if b is None or b.customer_id != customer.id:
            raise ApiError("not_found", "That request was not found.", 404)
        return b

    def change(self, customer: Customer, addon_id: str, body: AddonChangeIn) -> AddonOut:
        """Change the date or the finish-by time until 9 PM the day before (ADD-10)."""
        b = self._own(customer, addon_id)
        if b.status not in OPEN_STATUSES:
            raise ApiError("not_open", "This request can no longer be changed.", 409)
        now = self._now()
        require_open(b.proposed_date, now, bound=True, hour=self._hour)
        target_date = body.date or b.proposed_date
        target_time = _time(body.finish_by) if body.finish_by else b.finish_by
        require_open(target_date, now, bound=True, hour=self._hour)
        if self._frozen(b) or self._frozen(b, target_date):
            b.requested_date, b.requested_finish_by = target_date, target_time
            self._db.commit()
            from app.notifications.emit import _alert_once

            _alert_once(
                self._db,
                "addon_change",
                "Add-on change requested",
                f"{b.service}: {target_date} finish by {target_time:%H:%M}",
                "addon",
                str(b.id),
                once=False,
            )
            return self._out(b)
        if body.date is not None and body.date != b.proposed_date:
            require_open(body.date, now, bound=True, hour=self._hour)
            b.proposed_date = body.date
        if body.finish_by is not None:
            b.finish_by = _time(body.finish_by)
        self._db.commit()
        if b.vehicle_id:
            from app.scheduling.service import reconcile_vehicle

            reconcile_vehicle(self._db, b.vehicle_id)
        return self._out(b)

    def _frozen(self, b: AddonBooking, day: date | None = None) -> bool:
        if b.vehicle_id is None:
            return False
        vehicle = self._db.get(Vehicle, b.vehicle_id)
        c = self._db.get(Customer, b.customer_id)
        return (
            self._db.scalar(
                select(Schedule.id).where(
                    Schedule.society_id == (vehicle.society_id or c.society_id),
                    Schedule.start_date <= (day or b.proposed_date),
                    Schedule.end_date >= (day or b.proposed_date),
                    Schedule.status == "Frozen",
                )
            )
            is not None
        )

    def cancel(self, customer: Customer, addon_id: str) -> AddonOut:
        b = self._own(customer, addon_id)
        if b.status not in OPEN_STATUSES:
            raise ApiError("not_open", "This request can no longer be cancelled.", 409)
        require_open(b.proposed_date, self._now(), bound=True, hour=self._hour)
        self._cancel(b)
        return self._out(b)

    def _cancel(self, b: AddonBooking) -> None:
        if self._db.scalar(
            select(Job.id).where(
                Job.addon_booking_id == b.id, Job.status.in_(("In progress", "Completed"))
            )
        ):
            raise ApiError("job_started", "This job has already started or finished.", 409)
        b.status = "Cancelled"
        b.requested_date, b.requested_finish_by = None, None
        b.cancelled_at = utcnow()
        self._billing.void_unpaid(b.payment_id)  # A cancelled add-on is not charged.
        self._db.commit()
        emit.addon_cancelled(self._db, b)  # notify hook

    # --- the admin ---------------------------------------------------------

    def _admin_out(self, b: AddonBooking) -> AdminAddonOut:
        c = self._db.get(Customer, b.customer_id)
        v = self._db.get(Vehicle, b.vehicle_id) if b.vehicle_id else None
        society = self._db.get(Society, (v.society_id if v else None) or c.society_id)
        return AdminAddonOut(
            **self._out(b).model_dump(),
            customer_name=customer_name(c),
            flat=c.flat,
            society=society.name if society else "",
            vehicle=vehicle_label(v),
            contact_mobile=b.contact_mobile,
            notes=b.notes,
        )

    def admin_list(
        self,
        status: str | None,
        standalone: bool | None,
        society_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        service: str | None = None,
    ) -> list[AdminAddonOut]:
        q = select(AddonBooking).order_by(AddonBooking.proposed_date, AddonBooking.created_at)
        if status:
            q = q.where(AddonBooking.status == status)
        if standalone is not None:
            q = q.where(AddonBooking.standalone == standalone)
        if date_from and date_to and date_from > date_to:
            raise ApiError("validation_failed", "The date range is reversed.", 422)
        if date_from:
            q = q.where(AddonBooking.proposed_date >= date_from)
        if date_to:
            q = q.where(AddonBooking.proposed_date <= date_to)
        if service:
            q = q.where(AddonBooking.service == service)
        if society_id:
            q = (
                q.join(Customer, Customer.id == AddonBooking.customer_id)
                .outerjoin(Vehicle, Vehicle.id == AddonBooking.vehicle_id)
                .where(func.coalesce(Vehicle.society_id, Customer.society_id) == society_id)
            )
        return [self._admin_out(b) for b in self._db.scalars(q.limit(200))]

    def admin_update(self, addon_id: str, body: AdminAddonIn) -> AdminAddonOut:
        """Not bound by the 9 PM rule (ADM-ADD-04)."""
        b = self._db.get(AddonBooking, parse_id(addon_id, "request"))
        if b is None:
            raise ApiError("not_found", "That request was not found.", 404)
        changing = body.date is not None or body.finish_by is not None or body.resolve_change
        if changing and b.status not in OPEN_STATUSES:
            raise ApiError("not_open", "This booking has finished or was cancelled.", 409)
        target = body.date or (b.requested_date if body.resolve_change else None)
        if changing and (self._frozen(b) or (target and self._frozen(b, target))):
            raise ApiError(
                "schedule_frozen", "Unfreeze the schedule before changing this booking.", 409
            )
        if body.reject_change:
            b.requested_date, b.requested_finish_by = None, None
        if body.resolve_change:
            if b.requested_date is None:
                raise ApiError("not_requested", "There is no change request.", 409)
            body.date, body.finish_by = b.requested_date, b.requested_finish_by.strftime("%H:%M")
            b.requested_date, b.requested_finish_by = None, None
        if body.status is not None and body.status not in ADDON_STATUSES:
            raise ApiError(
                "validation_failed", "That status is not valid.", 422, {"status": "invalid"}
            )
        if body.status == "Scheduled" and not self._db.scalar(
            select(Job.id).where(
                Job.addon_booking_id == b.id, Job.crew_id.is_not(None), Job.status == "Scheduled"
            )
        ):
            raise ApiError("not_assigned", "Schedule the job before marking it Scheduled.", 409)
        if body.status in ("Completed", "Missed"):
            wanted = "Completed" if body.status == "Completed" else "Could not complete"
            if not self._db.scalar(
                select(Job.id).where(Job.addon_booking_id == b.id, Job.status == wanted)
            ):
                raise ApiError(
                    "job_not_finished", "The job status is set by service completion.", 409
                )
        if body.date is not None:
            if body.date < today_of(self._now()):
                raise ApiError("date_in_past", "That date has passed.", 409)
            b.proposed_date = body.date
        if body.finish_by is not None:
            b.finish_by = _time(body.finish_by)
        if body.status == "Cancelled" and b.status != "Cancelled":
            self._cancel(b)
        elif body.status is not None:
            b.status = body.status
        self._db.commit()
        if b.vehicle_id and changing:
            from app.scheduling.service import reconcile_vehicle

            reconcile_vehicle(self._db, b.vehicle_id)
        return self._admin_out(b)
