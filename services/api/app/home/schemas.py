from datetime import date

from pydantic import BaseModel


class NextService(BaseModel):
    date: date
    service: str
    status: str


class VehicleCard(BaseModel):
    id: str
    # Shown as on the plate. Empty when the number is not on file yet.
    registration: str
    model: str
    society: str
    # For example "B2-14". Empty when it is not on file yet.
    parking: str
    # Empty for a vehicle with no subscription (standalone Deep Spa, ADD-14).
    subscription_status: str | None
    monthly_price_rupees: int | None
    # "HH:MM", the time by which the daily clean is done (ONB-16).
    cutoff_time: str | None
    interior_day: str | None
    # Empty until a visit is scheduled.
    next_service: NextService | None


class QuickAction(BaseModel):
    key: str
    label: str


class CustomerHome(BaseModel):
    greeting_name: str
    # False until the customer confirms the review at first sign-in (ONB-25).
    onboarding_confirmed: bool
    # One card for each vehicle. The customer switches between them (HOME-07).
    vehicles: list[VehicleCard]
    quick_actions: list[QuickAction]


class JobCard(BaseModel):
    id: str
    time: str
    vehicle: str
    parking: str
    service: str
    status: str


class CrewHome(BaseModel):
    date: date
    society: str
    total: int
    done: int
    left: int
    jobs: list[JobCard]


class PaymentToConfirm(BaseModel):
    id: str
    customer_label: str
    amount_rupees: int
    reference: str


class AdminHome(BaseModel):
    alert_count: int
    payments_to_confirm: list[PaymentToConfirm]
    needs_scheduling_count: int
