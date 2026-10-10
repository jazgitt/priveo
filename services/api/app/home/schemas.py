from datetime import date

from pydantic import BaseModel


class VehicleCard(BaseModel):
    registration: str
    model: str
    society: str
    parking: str


class NextService(BaseModel):
    date: date
    service: str
    status: str


class QuickAction(BaseModel):
    key: str
    label: str


class CustomerHome(BaseModel):
    greeting_name: str
    vehicle: VehicleCard
    next_service: NextService
    subscription_status: str
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
