"""What a signed-in customer sees of their own record: the home screen and
the review of their details at first sign-in (ONB-25, ONB-26)."""
import re
import uuid
from datetime import time

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import WEEKDAYS, Customer, Subscription, Vehicle
from app.directory.models import Plan, Society
from app.home.schemas import CustomerHome, QuickAction, VehicleCard
from app.identity.models import Login
from app.platform.db import utcnow
from app.platform.errors import ApiError

BASEMENTS = ("B1", "B2", "B3", "B4")  # ONB-13
_NAME = re.compile(r"[A-Za-z][A-Za-z .'-]{0,79}")  # ONB-02
_REGISTRATION = re.compile(r"([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{4})")

QUICK_ACTIONS = [
    QuickAction(key="skip_pause", label="Skip or Pause"),
    QuickAction(key="history", label="Service History"),
    QuickAction(key="feedback", label="Give Feedback"),
    QuickAction(key="report_issue", label="Report an Issue"),
]


class OnboardingVehicle(BaseModel):
    id: str
    registration: str
    model: str
    parking_basement: str
    parking_number: str
    has_subscription: bool
    plan_name: str | None
    monthly_price_rupees: int | None
    cutoff_time: str | None
    # Whether the plan includes interior cleaning, so the day is asked (ONB-18).
    asks_interior_day: bool
    interior_day: str | None


class Onboarding(BaseModel):
    confirmed: bool
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
    def __init__(self, db: Session):
        self._db = db

    def _customer(self, login_id: uuid.UUID) -> Customer:
        customer = self._db.scalar(select(Customer).where(Customer.login_id == login_id))
        if customer is None:
            raise ApiError("no_customer_record",
                           "Your details are not set up yet. Contact Priveo.", 404)
        return customer

    def _vehicles(self, customer: Customer) -> list[tuple[Vehicle, Subscription | None]]:
        rows = self._db.execute(
            select(Vehicle, Subscription)
            .outerjoin(Subscription, Subscription.vehicle_id == Vehicle.id)
            .where(Vehicle.customer_id == customer.id, Vehicle.active.is_(True))
            .order_by(Vehicle.created_at, Vehicle.source_ref, Vehicle.id)).all()
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
        society = self._db.get(Society, customer.society_id).name
        cards = []
        for vehicle, sub in self._vehicles(customer):
            parking = "-".join(p for p in (vehicle.parking_basement, vehicle.parking_number) if p)
            cards.append(VehicleCard(
                id=str(vehicle.id),
                registration=show_registration(vehicle.registration),
                model=vehicle.model,
                society=society,
                parking=parking,
                subscription_status=sub.status if sub else None,
                monthly_price_rupees=sub.monthly_price_rupees if sub else None,
                cutoff_time=show_time(sub.cutoff_time) if sub else None,
                interior_day=sub.interior_day if sub else None,
                # Filled in once visits are scheduled.
                next_service=None,
            ))
        return CustomerHome(
            greeting_name=customer.first_name,
            onboarding_confirmed=customer.onboarding_confirmed_at is not None,
            vehicles=cards,
            quick_actions=QUICK_ACTIONS,
        )

    def onboarding(self, login_id: uuid.UUID) -> Onboarding:
        customer = self._customer(login_id)
        vehicles = []
        for vehicle, sub in self._vehicles(customer):
            plan = self._plan(sub)
            vehicles.append(OnboardingVehicle(
                id=str(vehicle.id),
                registration=show_registration(vehicle.registration),
                model=vehicle.model,
                parking_basement=vehicle.parking_basement,
                parking_number=vehicle.parking_number,
                has_subscription=sub is not None,
                plan_name=plan.name if plan else None,
                monthly_price_rupees=sub.monthly_price_rupees if sub else None,
                cutoff_time=show_time(sub.cutoff_time) if sub else None,
                asks_interior_day=self._asks_interior_day(sub),
                interior_day=sub.interior_day if sub else None,
            ))
        return Onboarding(
            confirmed=customer.onboarding_confirmed_at is not None,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            mobile=customer.mobile,
            society=self._db.get(Society, customer.society_id).name,
            flat=customer.flat,
            vehicles=vehicles,
        )

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
            raise ApiError("validation_failed", "Please check the details.", 422,
                           {"vehicles": "Review every one of your vehicles."})

        changes = []
        for index, (vehicle, sub) in enumerate(owned):
            answer = given[str(vehicle.id)]
            at = f"vehicles.{index}"
            basement = answer.parking_basement.strip().upper()
            number = answer.parking_number.strip()
            if basement not in BASEMENTS:
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
