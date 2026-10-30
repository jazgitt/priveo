"""Subscriptions by plan and society, subscriptions that went Inactive, and customer pauses
and skips (Appendix A questions 1 to 4)."""
from collections import Counter
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import SubscriptionEvent
from app.changes.models import ScheduleChange
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Plan, Society
from app.mani.contracts import ToolSpec
from app.mani.tools._base import (
    FROM_DATE,
    TO_DATE,
    ReadTool,
    add_months,
    capped,
    first_of_month,
    full_name,
    get_int,
    get_month,
    get_period,
    iso,
    ist_range,
    month_last_day,
    schema,
    today_ist,
)

NO_PLAN = "No plan set"
NO_REASON = "No reason recorded"


def _society_id():
    return func.coalesce(Vehicle.society_id, Customer.society_id)


class SubscriptionsSummary(ReadTool):
    title = "Subscriptions summary"
    spec = ToolSpec(
        name="subscriptions_summary",
        description=(
            "Subscriptions today: counts by status, active subscriptions by plan, active "
            "subscribers by housing society (the most and the fewest), and the subscriptions "
            "that went Inactive in a period with the reasons recorded. The period defaults to "
            "the last 30 days."),
        parameters=schema({
            "from_date": FROM_DATE, "to_date": TO_DATE,
            "top": {"type": "integer", "description": "How many societies to list as most and "
                                                       "fewest, 1 to 10. Default 5."},
        }))

    def compute(self, db: Session, args: dict[str, Any], now) -> tuple[Any, str]:
        today = today_ist(now)
        first, last = get_period(args, today - timedelta(days=29), today)
        top = get_int(args, "top", 5, 1, 10)
        base = (select(Subscription.status, Plan.name, Society.name, func.count())
                .select_from(Subscription)
                .join(Vehicle, Vehicle.id == Subscription.vehicle_id)
                .join(Customer, Customer.id == Vehicle.customer_id)
                .join(Society, Society.id == _society_id())
                .outerjoin(Plan, Plan.id == Subscription.plan_id)
                .where(Vehicle.active.is_(True))
                .group_by(Subscription.status, Plan.name, Society.name))
        by_status: Counter = Counter()
        by_plan: Counter = Counter()
        by_society: Counter = Counter()
        for status, plan, society, n in db.execute(base):
            by_status[status] += n
            if status == "Active":
                by_plan[plan or NO_PLAN] += n
                by_society[society] += n
        for (name,) in db.execute(select(Society.name).where(Society.active.is_(True))):
            by_society.setdefault(name, 0)  # a society with no active subscriber counts as 0
        ranked = sorted(by_society.items(), key=lambda kv: (-kv[1], kv[0]))
        fewest = sorted(by_society.items(), key=lambda kv: (kv[1], kv[0]))

        start, end = ist_range(first, last)
        events = db.execute(
            select(SubscriptionEvent.subscription_id, SubscriptionEvent.at,
                   SubscriptionEvent.reason, Customer.first_name, Customer.last_name, Society.name)
            .join(Subscription, Subscription.id == SubscriptionEvent.subscription_id)
            .join(Vehicle, Vehicle.id == Subscription.vehicle_id)
            .join(Customer, Customer.id == Vehicle.customer_id)
            .join(Society, Society.id == _society_id())
            .where(SubscriptionEvent.to_status == "Inactive",
                   SubscriptionEvent.at >= start, SubscriptionEvent.at < end)
            .order_by(SubscriptionEvent.at.desc())).all()
        reasons = Counter((e.reason or "").strip() or NO_REASON for e in events)
        distinct = len({e.subscription_id for e in events})
        data = {
            "active_subscriptions": by_status.get("Active", 0),
            "by_status": dict(sorted(by_status.items())),
            "active_by_plan": [{"plan": p, "subscriptions": n}
                               for p, n in sorted(by_plan.items(), key=lambda kv: (-kv[1], kv[0]))],
            "active_by_society": {
                "societies_counted": len(by_society),
                "most": [{"society": s, "subscriptions": n} for s, n in ranked[:top]],
                "fewest": [{"society": s, "subscriptions": n} for s, n in fewest[:top]],
            },
            "went_inactive": {
                "from_date": first.isoformat(), "to_date": last.isoformat(),
                "subscriptions": distinct, "events": len(events),
                "reasons": [{"reason": r, "count": n} for r, n in reasons.most_common()],
                "recent": capped([{"customer": full_name(e.first_name, e.last_name),
                                   "society": e.name, "on": iso(e.at), "reason": e.reason or NO_REASON}
                                  for e in events]),
            },
        }
        summary = (
            f"{data['active_subscriptions']} active subscriptions; {distinct} went Inactive between "
            f"{first.isoformat()} and {last.isoformat()}. Reasons are the free text on the status "
            "change; an automatic change records the payment rule, and an older one may have none.")
        return data, summary


def _month_counts(db: Session, month: date) -> dict[str, Any]:
    last = month_last_day(month)
    rows = db.execute(
        select(ScheduleChange.customer_id, ScheduleChange.kind, ScheduleChange.start_date,
               ScheduleChange.end_date)
        .where(ScheduleChange.kind.in_(("skip", "pause")), ScheduleChange.status == "Active",
               ScheduleChange.start_date >= month, ScheduleChange.start_date <= last)).all()
    skips = [r for r in rows if r.kind == "skip"]
    pauses = [r for r in rows if r.kind == "pause"]
    return {
        "month": month.strftime("%Y-%m"),
        "skips": len(skips), "pauses": len(pauses),
        "customers_who_skipped": len({r.customer_id for r in skips}),
        "customers_who_paused": len({r.customer_id for r in pauses}),
        "customers_either": len({r.customer_id for r in rows}),
        "paused_days": sum((r.end_date - r.start_date).days + 1 for r in pauses),
    }


class ScheduleChangesSummary(ReadTool):
    title = "Pauses and skips"
    spec = ToolSpec(
        name="pauses_and_skips_summary",
        description=(
            "How many customers paused or skipped in a month, compared with the month before. "
            "Defaults to last month against the month before it. A change counts in the month it "
            "starts; cancelled changes and skips folded into a pause are not counted."),
        parameters=schema({"month": {"type": "string", "description": "The month to report, "
                                     "YYYY-MM. Default: last month."}}))

    def compute(self, db: Session, args: dict[str, Any], now) -> tuple[Any, str]:
        default = add_months(first_of_month(today_ist(now)), -1)
        month = get_month(args, "month", default)
        current = _month_counts(db, month)
        previous = _month_counts(db, add_months(month, -1))
        change = {k: current[k] - previous[k] for k in
                  ("skips", "pauses", "customers_either", "paused_days")}
        data = {"month": current, "month_before": previous, "change": change}
        summary = (f"{current['customers_either']} customers paused or skipped in {current['month']} "
                   f"against {previous['customers_either']} in {previous['month']}. "
                   "Counted by the day the pause or skip starts, not the day it was requested.")
        return data, summary
