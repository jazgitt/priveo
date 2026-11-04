import datetime as dt

from pydantic import BaseModel


class PaymentOut(BaseModel):
    id: str
    kind: str  # Plan | Add-on
    description: str
    amount_rupees: int
    # Not Due | Due | Due today | Over due | Initiated | Paid (PAY-09, PAY-14).
    # The backend works it out; the app only displays it.
    status: str
    # Due date minus today in India: negative once over due.
    days_to_due: int = 0
    # "Due in 3 days", "2 days over due", "Waiting for Priveo to confirm", "Payment
    # received"; empty for Not Due.
    status_message: str = ""
    # True after the admin rejected the last attempt and the customer has not marked it
    # paid again (PAY-17): the app adds "Your last payment failed".
    last_payment_failed: bool = False
    due_date: dt.date
    cycle_start: dt.date | None = None
    # The cycle's last day, counted (the same day as due_date for a plan payment).
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
    vehicle: str = ""
    service_details: dict[str, str | None] = {}


class SubscriptionView(BaseModel):
    """My Subscription (SUB-01, SUB-02, SUB-10)."""

    vehicle_id: str
    subscription_id: str
    plan_name: str | None
    # The plan's ID, list price and inclusions, for the Subscription page.
    plan_code: str | None = None
    plan_list_price_rupees: int | None = None
    plan_inclusions: list[str] = []
    vehicle: str
    registration: str
    society: str
    status: str  # Active | Activating | Paused | Inactive
    monthly_price_rupees: int
    payment_method: str
    cutoff_time: str | None
    interior_day: str | None
    # The first day the subscription covers (its first service date).
    start_date: dt.date
    cycle_start: dt.date
    # The end date is hidden unless the payment is Over due (SUB-01): renewal_date,
    # expires_on, days_left, cycle_end and inactive_by are null otherwise.
    renewal_date: dt.date | None = None
    expires_on: dt.date | None = None
    cycle_days: int
    days_left: int | None = None
    # Only when Over due: the cycle's last day, and the day by which the payment must
    # be cleared or the subscription goes Inactive (cycle_end + 7 days).
    cycle_end: dt.date | None = None
    inactive_by: dt.date | None = None
    # The payment the card is about: the oldest unpaid cycle that is past its end
    # date, else the current cycle. Null only before the cycle's payment is made.
    payment_id: str | None = None
    payment_status: str = "Not Due"
    days_to_due: int = 0
    status_message: str = ""
    last_payment_failed: bool = False
    latest_payment: PaymentOut | None
    # The customer can pay now: an Active subscription whose payment is not
    # Initiated or Paid (SUB-09).
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
    tax_details: dict | None = None


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
    # Add-on only (the service date). A plan payment is due on its cycle's last day.
    due_date: dt.date | None = None
    # Plan only: the first day of the cycle, also a past one. Default: the current cycle.
    cycle_start: dt.date | None = None
    # Not Due | Due | Due today | Over due (all mean Open) | Initiated | Paid.
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


class SubscriptionRowOut(BaseModel):
    """One row of the admin Subscriptions list (ADM-SUB-01 to ADM-SUB-05)."""

    subscription_id: str
    vehicle_id: str
    customer_name: str
    flat: str
    society: str
    vehicle: str
    plan_name: str | None
    # Active | Activating | Paused | Inactive. Paused is an Active subscription
    # with a pause running today.
    status: str
    first_service_date: dt.date | None
    # The end of the current billing cycle.
    renewal_date: dt.date | None
    # The status of the latest plan payment, and whether it is waiting (Due, Due today or Over due).
    payment_status: str | None = None
    payment_due: bool = False


class SubscriptionEventOut(BaseModel):
    """One change of a subscription's status (ADM-SUB-05)."""

    from_status: str
    to_status: str
    by: str
    reason: str
    at: dt.datetime


class SubscriptionStatusOut(BaseModel):
    subscription_id: str
    status: str
