"""Payments this billing cycle, customers Over due, and collections week over week
(Appendix A questions 21 to 23). Costs, payroll and expenses are not recorded anywhere."""
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import Payment
from app.billing.status import DISPLAY_STATUSES, display_status_sql
from app.customers.models import Customer, Vehicle
from app.directory.models import Society
from app.mani.contracts import ToolSpec
from app.mani.tools._base import (
    WEEK_START,
    ReadTool,
    capped,
    full_name,
    get_choice,
    get_int,
    ist_range,
    pct,
    schema,
    today_ist,
    week_start,
)


def _status_table(rows) -> dict[str, dict[str, int]]:
    table = {s: {"payments": 0, "rupees": 0} for s in DISPLAY_STATUSES}
    for status, n, rupees in rows:
        table[status] = {"payments": n, "rupees": int(rupees)}
    table["total"] = {"payments": sum(v["payments"] for v in table.values()),
                      "rupees": sum(v["rupees"] for v in table.values())}
    return table


class PaymentsSummary(ReadTool):
    title = "Payments and collections"
    spec = ToolSpec(
        name="payments_summary",
        description=(
            "Money owed and collected, in rupees with GST: plan payments of the billing cycle "
            "that holds today and add-on payments due in the last 30 days, by status (Not Due, Due, Due today, "
            "Over due, Initiated, Paid); the customers whose payment has been Over due for more "
            "than a number of days (default 7), with names and societies only; and what was "
            "collected in each of the last three weeks, India time. Void payments are left out. "
            "Costs and expenses are not recorded, so profit cannot be worked out."),
        parameters=schema({
            "over_due_days": {"type": "integer", "description": "List payments Over due for more "
                                                                "than this many days, 0 to 365. Default 7."},
            "week_starts_on": WEEK_START}))

    def compute(self, db: Session, args: dict[str, Any], now) -> tuple[Any, str]:
        today = today_ist(now)
        limit_days = get_int(args, "over_due_days", 7, 0, 365)
        starts = get_choice(args, "week_starts_on", ("monday", "sunday"), "monday")
        live = Payment.voided_at.is_(None)

        def by_status(*where):
            shown = display_status_sql(today).label("s")  # one object, so PostgreSQL can group by it
            return _status_table(db.execute(
                select(shown, func.count(), func.coalesce(func.sum(Payment.amount_rupees), 0))
                .where(live, *where).group_by(shown)))

        plan_cycle = by_status(Payment.kind == "Plan", Payment.cycle_start <= today,
                               Payment.cycle_end >= today)
        add_ons = by_status(Payment.kind == "Add-on", Payment.due_date >= today - timedelta(days=29),
                            Payment.due_date <= today)
        owed = by_status(Payment.status == "Open")

        # Over due for more than N days. A plan payment is Over due from the day after its
        # due date; an add-on from the day its service was done unpaid (`overdue_since`).
        candidates = db.execute(
            select(Payment.kind, Payment.amount_rupees, Payment.due_date, Payment.overdue_since,
                   Customer.first_name, Customer.last_name, Society.name)
            .join(Customer, Customer.id == Payment.customer_id)
            .outerjoin(Vehicle, Vehicle.id == Payment.vehicle_id)
            .join(Society, Society.id == func.coalesce(Vehicle.society_id, Customer.society_id))
            .where(live, Payment.status == "Open")).all()
        late = []
        for r in candidates:
            since = r.overdue_since if r.kind == "Add-on" else r.due_date + timedelta(days=1)
            if since is not None and since <= today and since < today - timedelta(days=limit_days):
                late.append((since, r))
        late.sort(key=lambda x: (x[0], x[1].first_name))
        late_rows = [{"customer": full_name(r.first_name, r.last_name), "society": r.name,
                      "kind": r.kind, "rupees": r.amount_rupees, "over_due_since": since.isoformat(),
                      "days_over_due": (today - since).days} for since, r in late]

        this_week = week_start(today, starts)
        weeks = []
        for back in (0, 1, 2):
            first = this_week - timedelta(days=7 * back)
            last = today if back == 0 else first + timedelta(days=6)
            start, end = ist_range(first, last)
            count, rupees = db.execute(
                select(func.count(), func.coalesce(func.sum(Payment.amount_rupees), 0))
                .where(live, Payment.status == "Paid", Payment.received_at >= start,
                       Payment.received_at < end)).one()
            weeks.append({"from_date": first.isoformat(), "to_date": last.isoformat(),
                          "partial_week": back == 0, "payments": count, "rupees": int(rupees)})
        last_week, before = weeks[1], weeks[2]
        difference = last_week["rupees"] - before["rupees"]
        data = {
            "today": today.isoformat(),
            "this_cycle_plan_payments": plan_cycle,
            "add_on_payments_due_last_30_days": add_ons,
            "outstanding_all_cycles": {
                "not_due": owed["Not Due"], "due": owed["Due"], "due_today": owed["Due today"],
                "over_due": owed["Over due"]},
            "over_due_more_than_days": limit_days,
            "customers_over_due": {
                "payments": len(late_rows), "customers": len({(r["customer"], r["society"]) for r in late_rows}),
                "rupees": sum(r["rupees"] for r in late_rows), "list": capped(late_rows)},
            "collections_by_week": {"week_starts_on": starts, "weeks": weeks},
            "last_week_against_week_before": {
                "last_week_rupees": last_week["rupees"], "week_before_rupees": before["rupees"],
                "difference_rupees": difference,
                "change_percent": pct(difference, before["rupees"]) if before["rupees"] else None},
        }
        not_late = sum(plan_cycle[s]["rupees"] for s in ("Not Due", "Due", "Due today"))
        summary = (
            f"This cycle's plan payments: Rs {not_late} Due or not yet due, "
            f"Rs {plan_cycle['Over due']['rupees']} Over due, Rs {plan_cycle['Paid']['rupees']} "
            f"Paid. {len(late_rows)} payments are Over due for more than {limit_days} days. "
            f"Collected Rs {last_week['rupees']} last week against Rs {before['rupees']} the week "
            "before. Collections count payments marked Paid, by the day received. No costs "
            "are recorded.")
        return data, summary
