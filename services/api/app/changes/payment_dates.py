"""Move unpaid renewal records in the same transaction as a pause edit."""
from datetime import timedelta

from sqlalchemy import select

from app.billing.models import Payment
from app.changes.rules import show_date
from app.platform.errors import ApiError


def shift_unpaid_renewals(db, sub, effective_date, days):
    if not days or sub is None:
        return
    rows = list(db.scalars(select(Payment).where(
        Payment.subscription_id == sub.id, Payment.kind == "Plan",
        Payment.status != "Received", Payment.voided_at.is_(None),
        (Payment.cycle_start >= effective_date) |
        (Payment.cycle_start.is_(None) & (Payment.due_date >= effective_date)),
    ).order_by(Payment.cycle_start)))
    moving = {p.id for p in rows}
    occupied = {p.cycle_start for p in db.scalars(select(Payment).where(
        Payment.subscription_id == sub.id)) if p.id not in moving}
    if any(p.cycle_start is not None and p.cycle_start + timedelta(days=days) in occupied
           for p in rows):
        raise ApiError("payment_cycle_conflict", "A payment already exists at the new cycle date.", 409)
    # The unique (subscription, cycle_start) key must not collide with the
    # next record while shifting several cycles in one transaction.
    if days > 0:
        rows.reverse()
    for payment in rows:
        if payment.cycle_start:
            payment.cycle_start += timedelta(days=days)
        if payment.cycle_end:
            payment.cycle_end += timedelta(days=days)
        payment.due_date += timedelta(days=days)
        if payment.overdue_since:
            payment.overdue_since += timedelta(days=days)
        if payment.description.startswith("Plan ") and payment.cycle_start and payment.cycle_end:
            payment.description = (f"Plan {show_date(payment.cycle_start)} to "
                                   f"{show_date(payment.cycle_end - timedelta(days=1))}")
        db.flush()
    if sub.pending_from and sub.pending_from >= effective_date:
        sub.pending_from += timedelta(days=days)
