"""Add-ons: pending Deep Spa bookings, add-on revenue by month, and add-on payments that
became Over due when the service completed (Appendix A questions 18, 24, 50)."""
from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.billing.models import Payment, PaymentEvent
from app.customers.models import Customer
from app.directory.models import Society
from app.mani.contracts import ToolSpec
from app.mani.tools._base import (
    ReadTool,
    add_months,
    capped,
    first_of_month,
    full_name,
    get_int,
    get_month,
    get_text,
    ist_range,
    month_last_day,
    schema,
    today_ist,
)

# The note the billing module writes when an unpaid add-on becomes Over due on completion.
COMPLETED_NOTE = "Service completed, payment not received"
PENDING = ("Requested", "Scheduled")


class AddonsSummary(ReadTool):
    title = "Add-ons summary"
    spec = ToolSpec(
        name="addons_summary",
        description=(
            "Add-on bookings and money. Pending bookings (Requested or Scheduled) with their "
            "proposed dates; add-on revenue received per month; and the add-on payments that "
            "became Over due the moment their service completed. The service defaults to "
            "Deep Spa for pending bookings and for the Over due count; revenue covers every add-on."),
        parameters=schema({
            "service": {"type": "string", "description": "A service name such as Deep Spa, or "
                                                         "'all'. Default Deep Spa."},
            "month": {"type": "string", "description": "The latest month for revenue and the "
                                                       "Over due count, YYYY-MM. Default this month."},
            "months": {"type": "integer", "description": "How many months of revenue, 1 to 12. Default 3."},
        }))

    def compute(self, db: Session, args: dict[str, Any], now) -> tuple[Any, str]:
        today = today_ist(now)
        service = get_text(args, "service") or "Deep Spa"
        month = get_month(args, "month", first_of_month(today))
        months = get_int(args, "months", 3, 1, 12)
        only = None if service.lower() == "all" else service

        pending_query = (select(AddonBooking.proposed_date, AddonBooking.finish_by,
                                AddonBooking.status, AddonBooking.service, AddonBooking.standalone,
                                Customer.first_name, Customer.last_name, Society.name)
                         .join(Customer, Customer.id == AddonBooking.customer_id)
                         .join(Society, Society.id == Customer.society_id)
                         .where(AddonBooking.status.in_(PENDING))
                         .order_by(AddonBooking.proposed_date, AddonBooking.created_at))
        if only:
            pending_query = pending_query.where(AddonBooking.service == only)
        pending = db.execute(pending_query).all()
        by_date = Counter(p.proposed_date for p in pending)

        revenue = []
        for back in range(months - 1, -1, -1):
            first = add_months(month, -back)
            start, end = ist_range(first, month_last_day(first))
            count, rupees = db.execute(
                select(func.count(), func.coalesce(func.sum(Payment.amount_rupees), 0))
                .where(Payment.kind == "Add-on", Payment.status == "Received",
                       Payment.voided_at.is_(None), Payment.received_at >= start,
                       Payment.received_at < end)).one()
            revenue.append({"month": first.strftime("%Y-%m"), "payments": count, "rupees": int(rupees)})

        start, end = ist_range(month, month_last_day(month))
        events = (select(PaymentEvent.payment_id, PaymentEvent.at, Payment.status)
                  .join(Payment, Payment.id == PaymentEvent.payment_id)
                  .join(AddonBooking, AddonBooking.payment_id == Payment.id)
                  .where(PaymentEvent.to_status == "Over due", PaymentEvent.note == COMPLETED_NOTE,
                         Payment.kind == "Add-on"))
        if only:
            events = events.where(AddonBooking.service == only)
        rows = db.execute(events).all()
        payments = {r.payment_id: r for r in rows}
        in_month = {r.payment_id for r in rows if start <= r.at < end}
        data = {
            "service": only or "all",
            "pending_bookings": {
                "total": len(pending),
                "by_status": dict(Counter(p.status for p in pending)),
                "by_date": capped([{"date": d.isoformat(), "bookings": n}
                                   for d, n in sorted(by_date.items())], 31),
                "bookings": capped([{
                    "date": p.proposed_date.isoformat(), "finish_by": p.finish_by.strftime("%H:%M"),
                    "status": p.status, "service": p.service, "society": p.name,
                    "customer": full_name(p.first_name, p.last_name),
                    "standalone": p.standalone} for p in pending]),
            },
            "revenue_received_by_month": revenue,
            "became_over_due_on_completion": {
                "all_time": len(payments),
                "in_month": {"month": month.strftime("%Y-%m"), "payments": len(in_month)},
                "still_over_due_now": sum(1 for r in payments.values() if r.status == "Over due"),
                "received_since": sum(1 for r in payments.values() if r.status == "Received"),
            },
        }
        this_month = revenue[-1]
        summary = (
            f"{len(pending)} pending {only or 'add-on'} bookings; add-on revenue received in "
            f"{this_month['month']} is Rs {this_month['rupees']} from {this_month['payments']} payments; "
            f"{len(payments)} add-on payments became Over due on completion. Revenue counts payments "
            "marked Received, by the day received (India time), GST included. Bookings made before "
            "the booking table existed are not included.")
        return data, summary
