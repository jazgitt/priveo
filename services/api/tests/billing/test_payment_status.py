"""The payment status rule (PAY-14 to PAY-19) and its SQL twin."""
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.billing.models import Payment
from app.billing.status import STORED_STATUSES, payment_status, payment_status_sql

TODAY = date(2026, 11, 5)
REJECTED = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.mark.parametrize("d, status, message", [
    (30, "Not Due", ""),
    (8, "Not Due", ""),
    (7, "Due", "Due in 7 days"),
    (2, "Due", "Due in 2 days"),
    (1, "Due", "Due in 1 day"),
    (0, "Due today", "Due today"),
    (-1, "Over due", "1 day over due"),
    (-2, "Over due", "2 days over due"),
    (-7, "Over due", "7 days over due"),
])
def test_the_status_follows_the_days_to_the_due_date(d, status, message):
    got = payment_status(TODAY + timedelta(days=d), "Open", None, TODAY)
    assert (got.status, got.message, got.days_to_due) == (status, message, d)
    assert got.last_payment_failed is False


def test_initiated_and_paid_ignore_the_date():
    for d in (-9, 0, 3, 20):
        due = TODAY + timedelta(days=d)
        assert payment_status(due, "Paid", None, TODAY).status == "Paid"
        assert payment_status(due, "Initiated", None, TODAY).status == "Initiated"
    assert payment_status(TODAY, "Paid", None, TODAY).message == "Payment received"


def test_a_rejected_payment_shows_the_date_status_and_the_failed_flag():
    got = payment_status(TODAY - timedelta(days=2), "Open", REJECTED, TODAY)
    assert (got.status, got.last_payment_failed) == ("Over due", True)
    # Once the customer taps I've paid again, the flag goes.
    assert payment_status(TODAY, "Initiated", REJECTED, TODAY).last_payment_failed is False
    assert payment_status(TODAY, "Paid", REJECTED, TODAY).last_payment_failed is False


def test_the_sql_case_agrees_with_the_python_rule(money):
    db = money.db
    rows = {}
    for d in range(-10, 11):
        for stored in STORED_STATUSES:
            pid = uuid.uuid4()
            rows[pid] = (d, stored)
            db.add(Payment(id=pid, customer_id=money.customer_id, kind="Add-on",
                           description="x", amount_rupees=1, status=stored,
                           due_date=TODAY + timedelta(days=d)))
    db.commit()
    shown = dict(db.execute(select(Payment.id, payment_status_sql(TODAY))).all())
    assert len(shown) == len(rows) == 21 * 3
    for pid, (d, stored) in rows.items():
        want = payment_status(TODAY + timedelta(days=d), stored, None, TODAY).status
        assert shown[pid] == want, (d, stored)
    # It also works as a filter and a group-by.
    over = db.scalars(select(Payment.id).where(payment_status_sql(TODAY) == "Over due")).all()
    assert len(over) == 10
    shown_as = payment_status_sql(TODAY).label("shown")
    grouped = dict(db.execute(select(shown_as, func.count()).group_by(shown_as)).all())
    assert grouped == {"Paid": 21, "Initiated": 21, "Not Due": 3, "Due": 7,
                       "Due today": 1, "Over due": 10}
