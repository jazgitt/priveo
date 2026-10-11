import datetime as dt

from pydantic import BaseModel


class PaymentOut(BaseModel):
    id: str
    kind: str  # Plan | Add-on
    description: str
    amount_rupees: int
    # Due | Over due | Initiated | Received (PAY-09). The app only displays it.
    status: str
    due_date: dt.date
    cycle_start: dt.date | None = None
    cycle_end: dt.date | None = None
    vehicle_id: str | None = None
    received_on: dt.date | None = None
    invoice_number: str | None = None


class PayInstructions(BaseModel):
    """What the payment screen shows (PAY-05)."""

    amount_rupees: int
    upi_id: str
    payee_name: str
    qr_url: str | None
    upi_uri: str
    note: str


class PaymentDetail(BaseModel):
    payment: PaymentOut
    instructions: PayInstructions


class SubscriptionView(BaseModel):
    """My Subscription (SUB-01, SUB-02, SUB-10)."""

    vehicle_id: str
    subscription_id: str
    plan_name: str | None
    vehicle: str
    registration: str
    society: str
    status: str  # Active | Activating | Paused | Inactive
    monthly_price_rupees: int
    payment_method: str
    cutoff_time: str | None
    interior_day: str | None
    cycle_start: dt.date
    renewal_date: dt.date
    cycle_days: int
    days_left: int
    latest_payment: PaymentOut | None
    # From one week before the renewal date (SUB-09).
    can_pay_next: bool


class InvoiceOut(BaseModel):
    number: str
    issued_on: dt.date
    amount_rupees: int
    description: str
    customer_name: str
    vehicle: str
    gst_included: bool
    seller_name: str
    seller_address: str
    seller_gstin: str


class AdminPaymentOut(PaymentOut):
    customer_name: str
    flat: str
    society: str
    vehicle: str
    initiated_at: dt.datetime | None = None


class StatusIn(BaseModel):
    status: str


class AdminPaymentIn(BaseModel):
    """Record a payment for a customer, for example one made in person
    (ADM-PAY-04) or the first payment of a new subscription (ADM-CUS-06)."""

    vehicle_id: str
    kind: str = "Plan"
    description: str = ""
    amount_rupees: int
    due_date: dt.date
    cycle_start: dt.date | None = None
    status: str = "Due"


class PaymentAlertOut(BaseModel):
    id: str
    kind: str
    message: str
    payment_id: str | None
    created_at: dt.datetime
    read: bool


class SubscriptionStatusIn(BaseModel):
    status: str  # Inactive | Activating | Active
    reason: str = ""
    first_service_date: dt.date | None = None


class SubscriptionStatusOut(BaseModel):
    subscription_id: str
    status: str
