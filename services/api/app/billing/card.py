"""What the plan card shows about the current payment (SUB-01, SUB-10, PAY-14).

The cycle's end date is shown only when the payment is Over due; then the card
also says the day by which it must be cleared (end date + the Inactive limit)."""
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.models import Payment
from app.billing.status import PaymentStatusView, display_status, payment_status
from app.changes.cycle import cycle_window, shift_days
from app.customers.models import Subscription
from app.directory import lookup


@dataclass
class CardState:
    cycle_start: date
    last_day: date  # the cycle's last day (counted)
    current: Payment | None  # the payment of the cycle that holds today
    focus: Payment | None  # the payment the card is about
    view: PaymentStatusView
    inactive_after: int

    @property
    def overdue(self) -> bool:
        return self.view.status == "Over due"

    @property
    def inactive_by(self) -> date | None:
        return self.last_day + timedelta(days=self.inactive_after) if self.overdue else None


def card_state(db: Session, sub: Subscription, today: date) -> CardState:
    cycle_days = lookup.setting(db, "billing.cycle_days")
    start, renewal = cycle_window(sub.first_service_date, shift_days(db, sub.vehicle_id),
                                  today, cycle_days)

    def plan_rows(*where):
        return select(Payment).where(
            Payment.subscription_id == sub.id, Payment.kind == "Plan",
            Payment.voided_at.is_(None), *where)

    current = db.scalar(plan_rows(Payment.cycle_start == start))
    # An older cycle that is still unpaid and past its end date comes first.
    older = db.scalar(plan_rows(Payment.status == "Open",
                                Payment.cycle_start >= sub.first_service_date)
                      .order_by(Payment.due_date))
    focus = older if older is not None and older.due_date < today else current
    if focus is not None:
        view, last_day = display_status(focus, today), focus.due_date
    else:  # The payment of this cycle is not made yet; the date rule still applies.
        last_day = renewal - timedelta(days=1)
        view = payment_status(last_day, "Open", None, today)
    return CardState(start, last_day, current, focus, view,
                     lookup.setting(db, "billing.inactive_after_days"))
