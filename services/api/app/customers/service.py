"""What a signed-in customer sees of their own record: the home screen and
the review of their details at first sign-in (ONB-25, ONB-26)."""

import re
import uuid
from datetime import time

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import WEEKDAYS, Customer, Subscription, Vehicle
from app.directory import lookup
from app.directory.models import Plan, Society
from app.home.schemas import CustomerHome, QuickAction, VehicleCard
from app.identity.models import Login
from app.media import service as media
from app.media.store import ObjectStore, get_object_store
from app.platform.db import utcnow
from app.platform.errors import ApiError

BASEMENTS = ("B1", "B2", "B3", "B4")  # ONB-13
_NAME = re.compile(r"[A-Za-z][A-Za-z .'-]{0,79}")  # ONB-02
_REGISTRATION = re.compile(r"([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{4})")

QUICK_ACTIONS = [
    QuickAction(key="skip_pause", label="Skip or Pause"),
    QuickAction(key="history", label="Service History"),
    QuickAction(key="rate_today", label="Rate today's clean"),
    QuickAction(key="report_issue", label="Report an Issue"),
]


class OnboardingVehicle(BaseModel):
    id: str
    registration: str
    model: str
    make: str = ""
    variant: str = ""
    parking_basements: list[str] = ["B1", "B2", "B3", "B4"]
    parking_basement: str
    parking_number: str
    has_subscription: bool
    plan_name: str | None
    monthly_price_rupees: int | None
    cutoff_time: str | None
    # Whether the plan includes interior cleaning, so the day is asked (ONB-18).
    asks_interior_day: bool
    interior_day: str | None
    # The vehicle photo is required before Home opens (ONB-22).
    has_photo: bool = False
    photo_url: str | None = None


class Onboarding(BaseModel):
    confirmed: bool
    step: int = 0
    first_name: str
    last_name: str
    email: str
    mobile: str
    society: str
    flat: str
    vehicles: list[OnboardingVehicle]


class VehicleAnswer(BaseModel):
    id: str
    parking_basement: str
    parking_number: str
    cutoff_time: str | None
    interior_day: str | None


class OnboardingAnswers(BaseModel):
    first_name: str
    last_name: str
    mobile: str
    vehicles: list[VehicleAnswer]


class VehicleDraft(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    parking_basement: str | None = None
    parking_number: str | None = None
    cutoff_time: str | None = None
    interior_day: str | None = None


class OnboardingDraft(BaseModel):
    model_config = {"extra": "forbid"}
    step: int
    first_name: str | None = None
    last_name: str | None = None
    mobile: str | None = None
    vehicles: list[VehicleDraft] = []


def show_registration(registration: str | None) -> str:
    """`HR26DK8337` as `HR 26 DK 8337`. Empty when the number is not on file."""
    if not registration:
        return ""
    m = _REGISTRATION.fullmatch(registration)
    return " ".join(p for p in m.groups() if p) if m else registration


def show_time(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None


def read_cutoff(text: str | None) -> time | None:
    """A time of day in 30-minute steps (ONB-16), or None when it is not one."""
    m = re.fullmatch(r"([01]\d|2[0-3]):(00|30)", (text or "").strip())
    return time(int(m.group(1)), int(m.group(2))) if m else None


class CustomerService:
    def __init__(self, db: Session, store: ObjectStore | None = None):
        self._db = db
        self._store = store or get_object_store()

    def _customer(self, login_id: uuid.UUID) -> Customer:
        customer = self._db.scalar(select(Customer).where(Customer.login_id == login_id))
        if customer is None:
            raise ApiError(
                "no_customer_record", "Your details are not set up yet. Contact Priveo.", 404
            )
        return customer

    def _vehicles(self, customer: Customer) -> list[tuple[Vehicle, Subscription | None]]:
        rows = self._db.execute(
            select(Vehicle, Subscription)
            .outerjoin(Subscription, Subscription.vehicle_id == Vehicle.id)
            .where(Vehicle.customer_id == customer.id, Vehicle.active.is_(True))
            .order_by(Vehicle.created_at, Vehicle.source_ref, Vehicle.id)
        ).all()
        # Vehicles with a subscription come first.
        return sorted(((v, s) for v, s in rows), key=lambda pair: pair[1] is None)

    def _plan(self, subscription: Subscription | None) -> Plan | None:
        if subscription is None or subscription.plan_id is None:
            return None
        return self._db.get(Plan, subscription.plan_id)

    def _asks_interior_day(self, subscription: Subscription | None) -> bool:
        if subscription is None:
            return False
        plan = self._plan(subscription)
        # Until the plans are set up, a subscription that came with an
        # interior day is taken to include interior cleaning.
        return plan.includes_interior if plan else subscription.interior_day is not None

    def home(self, login_id: uuid.UUID) -> CustomerHome:
        customer = self._customer(login_id)
        cards = []
        owned = self._vehicles(customer)
        photos = media.vehicle_photo_urls(self._db, self._store, [v.id for v, _ in owned])
        for vehicle, sub in owned:
            plan = self._plan(sub)
            parking = "-".join(p for p in (vehicle.parking_basement, vehicle.parking_number) if p)
            cards.append(
                VehicleCard(
                    id=str(vehicle.id),
                    registration=show_registration(vehicle.registration),
                    model=vehicle.model,
                    make=vehicle.make,
                    variant=vehicle.variant,
                    photo_url=photos.get(vehicle.id),
                    society=self._db.get(Society, vehicle.society_id or customer.society_id).name,
                    parking=parking,
                    subscription_status=sub.status if sub else None,
                    monthly_price_rupees=sub.monthly_price_rupees if sub else None,
                    plan_name=plan.name if plan else None,
                    cutoff_time=show_time(sub.cutoff_time) if sub else None,
                    interior_day=sub.interior_day if sub else None,
                    # Filled in once visits are scheduled.
                    next_service=None,
                )
            )
        return CustomerHome(
            greeting_name=customer.first_name,
            onboarding_confirmed=customer.onboarding_confirmed_at is not None,
            vehicles=cards,
            quick_actions=QUICK_ACTIONS,
        )

    def onboarding(self, login_id: uuid.UUID) -> Onboarding:
        customer = self._customer(login_id)
        vehicles = []
        owned = self._vehicles(customer)
        photos = media.vehicle_photo_urls(self._db, self._store, [v.id for v, _ in owned])
        for vehicle, sub in owned:
            plan = self._plan(sub)
            vehicles.append(
                OnboardingVehicle(
                    id=str(vehicle.id),
                    registration=show_registration(vehicle.registration),
                    model=vehicle.model,
                    make=vehicle.make, variant=vehicle.variant,
                    parking_basements=lookup.society_basements(
                        self._db, vehicle.society_id or customer.society_id),
                    parking_basement=vehicle.parking_basement,
                    parking_number=vehicle.parking_number,
                    has_subscription=sub is not None,
                    plan_name=plan.name if plan else None,
                    monthly_price_rupees=sub.monthly_price_rupees if sub else None,
                    cutoff_time=show_time(sub.cutoff_time) if sub else None,
                    asks_interior_day=self._asks_interior_day(sub),
                    interior_day=sub.interior_day if sub else None,
                    has_photo=vehicle.id in photos,
                    photo_url=photos.get(vehicle.id),
                )
            )
        return Onboarding(
            confirmed=customer.onboarding_confirmed_at is not None,
            step=customer.onboarding_step,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            mobile=customer.mobile,
            society=self._db.get(Society, customer.society_id).name,
            flat=customer.flat,
            vehicles=vehicles,
        )

    def save_draft(self, login_id: uuid.UUID, draft: OnboardingDraft) -> None:
        customer = self._customer(login_id)
        if customer.onboarding_confirmed_at is not None:
            raise ApiError("already_confirmed", "Your details are already confirmed.", 409)
        owned = {str(v.id): (v, sub) for v, sub in self._vehicles(customer)}
        if not 0 <= draft.step <= 2 + 4 * len(owned):
            raise ApiError("validation_failed", "Invalid review step.", 422)
        changes = []
        for answer in draft.vehicles:
            if answer.id not in owned or sum(a.id == answer.id for a in draft.vehicles) != 1:
                raise ApiError("validation_failed", "Review only your vehicles.", 422)
            vehicle, sub = owned[answer.id]
            values = {}
            if answer.parking_basement is not None:
                basement = answer.parking_basement.strip().upper()
                if basement not in lookup.society_basements(
                    self._db, vehicle.society_id or customer.society_id
                ):
                    raise ApiError("validation_failed", "Select the basement.", 422)
                values["parking_basement"] = basement
            if answer.parking_number is not None:
                if not re.fullmatch(r"\d{1,5}", answer.parking_number.strip()):
                    raise ApiError("validation_failed", "Enter the parking number.", 422)
                values["parking_number"] = answer.parking_number.strip()
            if answer.cutoff_time is not None:
                cutoff = read_cutoff(answer.cutoff_time)
                if sub is None or cutoff is None:
                    raise ApiError("validation_failed", "Select the service cutoff.", 422)
                values["cutoff_time"] = cutoff
            if answer.interior_day is not None:
                if sub is None or not self._asks_interior_day(sub) or answer.interior_day not in WEEKDAYS:
                    raise ApiError("validation_failed", "Select the interior day.", 422)
                values["interior_day"] = answer.interior_day
            changes.append((vehicle, sub, values))
        personal = {}
        for field in ("first_name", "last_name"):
            value = getattr(draft, field)
            if value is not None:
                value = " ".join(value.split())
                if not _NAME.fullmatch(value):
                    raise ApiError("validation_failed", "Check your name.", 422)
                personal[field] = value
        if draft.mobile is not None:
            mobile = draft.mobile.strip()
            if mobile != customer.mobile and not re.fullmatch(r"\d{10}", mobile):
                raise ApiError("validation_failed", "Enter a 10-digit mobile number.", 422)
            personal["mobile"] = mobile
        for field, value in personal.items():
            setattr(customer, field, value)
        for vehicle, sub, values in changes:
            for field, value in values.items():
                setattr(sub if field in ("cutoff_time", "interior_day") else vehicle, field, value)
        customer.onboarding_step = draft.step
        self._db.get(Login, customer.login_id).display_name = (
            f"{customer.first_name} {customer.last_name}")
        self._db.commit()

    def confirm_onboarding(self, login_id: uuid.UUID, answers: OnboardingAnswers) -> None:
        """Saves what the customer may change (ONB-26) and opens Home (ONB-25)."""
        customer = self._customer(login_id)
        if customer.onboarding_confirmed_at is not None:
            raise ApiError("already_confirmed", "Your details are already confirmed.", 409)

        errors: dict[str, str] = {}
        first = " ".join(answers.first_name.split())
        last = " ".join(answers.last_name.split())
        mobile = answers.mobile.strip()
        if not _NAME.fullmatch(first):
            errors["first_name"] = "Enter your first name, using letters only."
        if not _NAME.fullmatch(last):
            errors["last_name"] = "Enter your last name, using letters only."
        # The number on file stands as it is. A new one must be 10 digits.
        if mobile != customer.mobile and not re.fullmatch(r"\d{10}", mobile):
            errors["mobile"] = "Enter a 10-digit mobile number."

        owned = self._vehicles(customer)
        given = {a.id: a for a in answers.vehicles}
        if set(given) != {str(v.id) for v, _ in owned} or len(given) != len(answers.vehicles):
            raise ApiError(
                "validation_failed",
                "Please check the details.",
                422,
                {"vehicles": "Review every one of your vehicles."},
            )

        changes = []
        for index, (vehicle, sub) in enumerate(owned):
            answer = given[str(vehicle.id)]
            at = f"vehicles.{index}"
            basement = answer.parking_basement.strip().upper()
            number = answer.parking_number.strip()
            if vehicle.id not in media.vehicle_photo_urls(self._db, self._store, [vehicle.id]):
                errors[f"{at}.photo"] = "Add a photo of your car."  # ONB-22
            if basement not in lookup.society_basements(
                self._db, vehicle.society_id or customer.society_id
            ):
                errors[f"{at}.parking_basement"] = "Select the basement."
            if not re.fullmatch(r"\d{1,5}", number):
                errors[f"{at}.parking_number"] = "Enter the parking number, in digits."
            cutoff = day = None
            if sub is not None:
                cutoff = read_cutoff(answer.cutoff_time)
                if cutoff is None:
                    errors[f"{at}.cutoff_time"] = "Please select your service cutoff time."
                if self._asks_interior_day(sub):
                    day = (answer.interior_day or "").strip().capitalize()
                    if day not in WEEKDAYS:
                        errors[f"{at}.interior_day"] = "Please select your interior care day."
            changes.append((vehicle, sub, basement, number, cutoff, day))
        if errors:
            raise ApiError("validation_failed", "Please check the details.", 422, errors)

        customer.first_name, customer.last_name, customer.mobile = first, last, mobile
        for vehicle, sub, basement, number, cutoff, day in changes:
            vehicle.parking_basement, vehicle.parking_number = basement, number
            if sub is not None:
                sub.cutoff_time = cutoff
                if day is not None:
                    sub.interior_day = day
        login = self._db.get(Login, customer.login_id)
        login.display_name = f"{first} {last}"
        customer.onboarding_confirmed_at = utcnow()
        self._db.commit()
