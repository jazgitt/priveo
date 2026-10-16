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
    make: str = ""
    society: str
    # For example "B2-14". Empty when it is not on file yet.
    parking: str
    # Empty for a vehicle with no subscription (standalone Deep Spa, ADD-14).
    subscription_status: str | None
    monthly_price_rupees: int | None
    # The subscription's plan name. None for a vehicle with no subscription.
    plan_name: str | None = None
    # "HH:MM", the time by which the daily clean is done (ONB-16).
    cutoff_time: str | None
    interior_day: str | None
    variant: str = ""
    # A signed read URL of the customer's own vehicle photo (HOME-02, VEH-01).
    photo_url: str | None = None
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
    vehicle: str = ""
    society: str = ""


class AdminHomeSociety(BaseModel):
    id: str
    name: str


class AdminHome(BaseModel):
    # Unread alerts of both lists: support alerts and payment alerts.
    alert_count: int
    # The oldest Initiated payments first, at most 20.
    payments_to_confirm: list[PaymentToConfirm]
    needs_scheduling_count: int
    # Added for the admin quick actions (ADM-ACC-07). All have defaults so an
    # older app keeps working.
    support_alert_count: int = 0
    payment_alert_count: int = 0
    payments_to_confirm_count: int = 0
    open_complaints_count: int = 0
    societies: list[AdminHomeSociety] = []


class AdminDayJob(BaseModel):
    id: str
    time: str | None
    end_time: str | None
    vehicle: str
    registration: str
    service: str
    status: str
    late: bool


class AdminDayCrew(BaseModel):
    # None for the jobs that have no crew member yet.
    crew_id: str | None
    crew_name: str
    role: str | None
    jobs: list[AdminDayJob]


class AdminDaySchedule(BaseModel):
    """One date, read only (ADM-ACC-07 c). No customer name or mobile number."""

    date: date
    society_id: str | None
    # Draft, Frozen, Mixed (more than one society with different states) or
    # None when no schedule has been run for the date.
    schedule_status: str | None
    total: int
    done: int
    left: int
    crew: list[AdminDayCrew]
