"""The payment status a customer and the admin see (PAY-14 to PAY-19, ADM-PAY-01).

The database stores only Open, Initiated or Paid. Not Due, Due, Due today and
Over due are worked out from the due date (the last day of the cycle) and
today's date in India. `payment_status` is the one rule; `payment_status_sql`
is its twin for filters, tiles and group-by, and a test keeps them equal."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import and_, case

STORED_STATUSES = ("Open", "Initiated", "Paid")
DISPLAY_STATUSES = ("Not Due", "Due", "Due today", "Over due", "Initiated", "Paid")
# Due is shown from this many days before the due date.
DUE_SOON_DAYS = 7


@dataclass(frozen=True)
class PaymentStatusView:
    status: str
    days_to_due: int
    message: str
    last_payment_failed: bool


def _days(n: int) -> str:
    return f"{n} day" if n == 1 else f"{n} days"


def payment_status(due_date: date, stored_status: str, rejected_at: datetime | None,
                   today: date) -> PaymentStatusView:
    """`today` is the India date. `days_to_due` is negative once over due."""
    d = (due_date - today).days
    if stored_status == "Paid":
        return PaymentStatusView("Paid", d, "Payment received", False)
    if stored_status == "Initiated":
        return PaymentStatusView("Initiated", d, "Waiting for Priveo to confirm", False)
    failed = rejected_at is not None
    if d > DUE_SOON_DAYS:
        return PaymentStatusView("Not Due", d, "", failed)
    if d >= 1:
        return PaymentStatusView("Due", d, f"Due in {_days(d)}", failed)
    if d == 0:
        return PaymentStatusView("Due today", d, "Due today", failed)
    return PaymentStatusView("Over due", d, f"{_days(-d)} over due", failed)


def payment_status_sql(today: date, due_date=None, status=None):
    """SQL `case` giving the same display status as `payment_status`, for
    filters, tiles and group-by. To group by it, label it once and group by the
    label (`e = payment_status_sql(t).label("s"); select(e, ...).group_by(e)`),
    because PostgreSQL does not match two copies that carry separate bound
    dates. The day arithmetic is done on the Python side
    (date thresholds), so it is the same on SQLite and PostgreSQL."""
    if due_date is None or status is None:
        from app.billing.models import Payment
        due_date, status = Payment.due_date, Payment.status
    return case(
        (status == "Paid", "Paid"),
        (status == "Initiated", "Initiated"),
        (due_date > today + timedelta(days=DUE_SOON_DAYS), "Not Due"),
        (due_date > today, "Due"),
        (due_date == today, "Due today"),
        else_="Over due",
    )


# The statuses the admin may choose that mean "no payment counts for the cycle":
# the date rule decides which one is shown (ADM-PAY-02).
DATE_BASED_STATUSES = ("Not Due", "Due", "Due today", "Over due")


def stored_for(display: str) -> str:
    """What is saved for a status the admin or an import chose."""
    return {"Paid": "Paid", "Initiated": "Initiated"}.get(display, "Open")


def display_status(p, today: date) -> PaymentStatusView:
    """The status of any payment row. A plan payment (and a plan-change charge)
    follows the date rule. An add-on is Due until its service is done unpaid, then
    Over due (ADM-PAY-13); it is not tied to a cycle."""
    if p.kind != "Add-on" or p.status != "Open":
        return payment_status(p.due_date, p.status, p.rejected_at, today)
    failed = p.rejected_at is not None
    d = (p.due_date - today).days
    if p.overdue_since is not None:
        return PaymentStatusView("Over due", d, "Service done, payment not received", failed)
    return PaymentStatusView("Due", d, f"Due on {p.due_date.strftime('%d-%b-%y')}", failed)


def display_status_sql(today: date):
    """SQL twin of `display_status` over the Payment columns. Label it once and
    reuse the label (see `payment_status_sql`)."""
    from app.billing.models import Payment

    addon_open = and_(Payment.kind == "Add-on", Payment.status == "Open")
    return case(
        (and_(addon_open, Payment.overdue_since.is_(None)), "Due"),
        (addon_open, "Over due"),
        else_=payment_status_sql(today),
    )
