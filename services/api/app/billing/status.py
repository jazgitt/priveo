"""The payment status a customer and the admin see (PAY-14 to PAY-19, ADM-PAY-01).

The database stores only Open, Initiated or Paid. Not Due, Due, Due today and
Over due are worked out from the due date (the last day of the cycle) and
today's date in India. `payment_status` is the one rule; `payment_status_sql`
is its twin for filters, tiles and group-by, and a test keeps them equal."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import case, literal_column

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


# TODO(B2): interim shim. Until the billing-flow rework, the API still speaks the
# old four names: Open with `overdue_since` set shows as "Over due", otherwise
# "Due"; Paid shows as "Received". B2 replaces this with payment_status().
LEGACY_STATUSES = ("Due", "Over due", "Initiated", "Received")


def legacy_shown(p) -> str:
    if p.status == "Paid":
        return "Received"
    if p.status == "Initiated":
        return "Initiated"
    return "Over due" if p.overdue_since is not None else "Due"


def legacy_shown_sql():
    from app.billing.models import Payment

    # Literal columns, not bound strings, so that PostgreSQL accepts the same
    # expression in the select list and in GROUP BY.
    return case((Payment.status == literal_column("'Paid'"), literal_column("'Received'")),
                (Payment.status == literal_column("'Initiated'"), literal_column("'Initiated'")),
                (Payment.overdue_since.is_not(None), literal_column("'Over due'")),
                else_=literal_column("'Due'"))
