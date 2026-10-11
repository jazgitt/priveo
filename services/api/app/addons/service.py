"""Deep Spa requests (ADD-01 to ADD-10, ADD-14, ADD-15)."""
import uuid
from datetime import date, time

from sqlalchemy import select
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
from app.directory.models import Society
from app.notifications import emit  # notify hook
from app.platform.db import utcnow
from app.platform.errors import ApiError

OPEN_STATUSES = ("Requested", "Scheduled")


def _time(text: str | None, field: str = "finish_by") -> time:
    value = read_cutoff(text)  # 30-minute steps, like the cutoff time
    if value is None:
        raise ApiError("validation_failed", "Choose a finish-by time in 30-minute steps.",
                       422, {field: "invalid"})
    return value


class AddonService:
    def __init__(self, db: Session, now_fn: Clock, settings: MoneySettings,
                 billing: BillingService):
        self._db = db
        self._now = now_fn
        self._settings = settings
        self._billing = billing

    def offers(self) -> list[AddonOffer]:
        s = self._settings
        return [AddonOffer(
            service="Deep Spa", name="Deep Spa",
            description="A two-hour deep clean of the inside and outside of the car.",
            price_rupees=s.deep_spa_price_rupees, list_price_rupees=s.deep_spa_list_price_rupees,
            duration_minutes=120)]

    def _price(self, service: str) -> int:
        for o in self.offers():
            if o.service == service:
                return o.price_rupees
        raise ApiError("validation_failed", "That add-on is not offered.", 422,
                       {"service": "unknown"})

    def _payment_status(self, b: AddonBooking) -> str | None:
        if b.payment_id is None:
            return None
        p = self._db.get(Payment, b.payment_id)
        return p.status if p and p.voided_at is None else None

    def _out(self, b: AddonBooking) -> AddonOut:
        return AddonOut(
            id=str(b.id), service=b.service, vehicle_id=str(b.vehicle_id) if b.vehicle_id else None,
            standalone=b.standalone, date=b.proposed_date,
            finish_by=b.finish_by.strftime("%H:%M"), status=b.status,
            price_rupees=b.price_rupees,
            payment_id=str(b.payment_id) if b.payment_id else None,
            payment_status=self._payment_status(b),
            can_change=b.status in OPEN_STATUSES and is_open(b.proposed_date, self._now()),
            created_at=b.created_at)

    def mine(self, customer: Customer) -> AddonsOut:
        rows = self._db.scalars(select(AddonBooking).where(
            AddonBooking.customer_id == customer.id).order_by(AddonBooking.created_at.desc()))
        return AddonsOut(offers=self.offers(), requests=[self._out(b) for b in rows])

    # --- the customer ------------------------------------------------------

    def request(self, customer: Customer, vehicle: Vehicle, sub: Subscription | None,
                body_service: str, day: date, finish_by: str, key: str | None) -> AddonOut:
        again = self._by_key(customer, key)
        if again is not None:
            return self._out(again)
        now = self._now()
        today = today_of(now)
        # ADD-01: for a vehicle whose subscription is Active, and not paused.
        if sub is None or sub.status != "Active" or today in paused_days(self._db, vehicle.id):
            raise ApiError("subscription_not_active",
                           "Add-ons are for a vehicle with an active subscription.", 409)
        price = self._price(body_service)
        finish = _time(finish_by)
        require_open(day, now, bound=True)  # ADD-04
        payment = self._billing.open_addon_payment(
            customer, vehicle, f"{body_service} on {day.strftime('%d-%b-%y')}", price)
        b = AddonBooking(
            customer_id=customer.id, vehicle_id=vehicle.id, service=body_service,
            proposed_date=day, finish_by=finish, price_rupees=price, payment_id=payment.id,
            idempotency_key=key or None)
        self._db.add(b)
        self._db.commit()
        return self._out(b)

    def standalone(self, customer: Customer, login_id: uuid.UUID, body: StandaloneIn,
                   key: str | None) -> AddonOut:
        """DERIVED / OPEN (ADD-15): a request with contact details, no payment
        and no price. Priveo calls the customer to agree the rest."""
        again = self._by_key(customer, key)
        if again is not None:
            return self._out(again)
        self._price(body.service)
        finish = _time(body.finish_by)
        vehicle_id = None
        if body.vehicle_id:
            _, vehicle, sub = owned_vehicle(self._db, login_id, body.vehicle_id)
            if sub is not None and sub.status == "Active":
                raise ApiError("has_subscription",
                               "This vehicle has a subscription. Book Deep Spa as an add-on.",
                               409)
            vehicle_id = vehicle.id
        if body.date <= today_of(self._now()):
            raise ApiError("validation_failed", "Choose tomorrow or a later date.", 422,
                           {"date": "too_soon"})
        mobile = (body.contact_mobile or customer.mobile).strip()
        b = AddonBooking(
            customer_id=customer.id, vehicle_id=vehicle_id, service=body.service,
            standalone=True, proposed_date=body.date, finish_by=finish,
            contact_mobile=mobile, notes=body.notes.strip(), idempotency_key=key or None)
        self._db.add(b)
        self._db.commit()
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
        require_open(b.proposed_date, now, bound=True)
        if body.date is not None and body.date != b.proposed_date:
            require_open(body.date, now, bound=True)
            b.proposed_date = body.date
        if body.finish_by is not None:
            b.finish_by = _time(body.finish_by)
        self._db.commit()
        return self._out(b)

    def cancel(self, customer: Customer, addon_id: str) -> AddonOut:
        b = self._own(customer, addon_id)
        if b.status not in OPEN_STATUSES:
            raise ApiError("not_open", "This request can no longer be cancelled.", 409)
        require_open(b.proposed_date, self._now(), bound=True)
        self._cancel(b)
        return self._out(b)

    def _cancel(self, b: AddonBooking) -> None:
        b.status = "Cancelled"
        b.cancelled_at = utcnow()
        self._billing.void_unpaid(b.payment_id)  # A cancelled add-on is not charged.
        self._db.commit()
        emit.addon_cancelled(self._db, b)  # notify hook

    # --- the admin ---------------------------------------------------------

    def _admin_out(self, b: AddonBooking) -> AdminAddonOut:
        c = self._db.get(Customer, b.customer_id)
        v = self._db.get(Vehicle, b.vehicle_id) if b.vehicle_id else None
        society = self._db.get(Society, c.society_id)
        return AdminAddonOut(
            **self._out(b).model_dump(), customer_name=customer_name(c), flat=c.flat,
            society=society.name if society else "", vehicle=vehicle_label(v),
            contact_mobile=b.contact_mobile, notes=b.notes)

    def admin_list(self, status: str | None, standalone: bool | None) -> list[AdminAddonOut]:
        q = select(AddonBooking).order_by(AddonBooking.proposed_date, AddonBooking.created_at)
        if status:
            q = q.where(AddonBooking.status == status)
        if standalone is not None:
            q = q.where(AddonBooking.standalone == standalone)
        return [self._admin_out(b) for b in self._db.scalars(q.limit(200))]

    def admin_update(self, addon_id: str, body: AdminAddonIn) -> AdminAddonOut:
        """Not bound by the 9 PM rule (ADM-ADD-04)."""
        b = self._db.get(AddonBooking, parse_id(addon_id, "request"))
        if b is None:
            raise ApiError("not_found", "That request was not found.", 404)
        if body.status is not None and body.status not in ADDON_STATUSES:
            raise ApiError("validation_failed", "That status is not valid.", 422,
                           {"status": "invalid"})
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
        return self._admin_out(b)

