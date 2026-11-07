"""SCHS-38: the customer calendar no longer promises the Interior on the preferred
weekday. It says "Interior this week" until the Interior is planned, then shows the
planned day. (Enabling story: no SCHR row.)"""
import uuid
from datetime import date

from sqlalchemy import select

from app.customer_reads.repository import Job, Visit
from app.customers.models import Subscription, Vehicle
from app.scheduling import entitlements
from app.scheduling.models import InteriorEntitlement
from tests.customer_reads.test_calendar_projection import by_date, clock, month  # noqa: F401


def _flagged(body):
    return sorted(v["date"] for v in body["visits"] if v.get("interior_this_week"))


def test_before_planning_the_calendar_says_interior_this_week(api, asha, clock, db):  # noqa: F811
    body = month(api, asha, "2026-12")
    days = by_date(body)
    # 04-Dec-26 (Friday) was the interior care day: no longer promised.
    assert days["2026-12-04"]["services"] == ["Cleaning-External"]
    assert all("Cleaning-Internal" not in v["services"] for v in body["visits"] if v["source"] == "projected")
    # Once for each service week, on its first open day. 01-Dec-26 has a planned visit.
    assert _flagged(body) == ["2026-12-02", "2026-12-07", "2026-12-14", "2026-12-21", "2026-12-28"]


def test_after_planning_the_calendar_shows_the_planned_day(api, asha, clock, db, repo):  # noqa: F811
    vehicle = asha["vehicles"][0]
    repo.visit_rows.append(Visit("v-int", vehicle, date(2026, 12, 9), "Scheduled"))
    repo.job_rows.append(Job("j-int", "v-int", "Cleaning-Internal", "Scheduled"))
    body = month(api, asha, "2026-12")
    days = by_date(body)
    assert "Cleaning-Internal" in days["2026-12-09"]["services"]
    assert days["2026-12-09"]["source"] == "visit"
    # The week of 07-Dec-26 has its Interior planned, so no "this week" note there.
    assert "2026-12-07" not in _flagged(body)
    assert "2026-12-14" in _flagged(body)


def test_a_week_the_ledger_has_completed_or_waived_is_not_flagged(api, asha, clock, db):  # noqa: F811
    vehicle = db.get(Vehicle, uuid.UUID(asha["vehicles"][0]))
    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == vehicle.id))
    entitlements.ensure(db, sub, date(2026, 12, 31))
    week = entitlements.week_start(db, date(2026, 12, 14))
    for row in db.scalars(select(InteriorEntitlement).where(
            InteriorEntitlement.vehicle_id == vehicle.id, InteriorEntitlement.service_week_start == week)):
        row.status = entitlements.COMPLETED
    db.commit()
    assert "2026-12-14" not in _flagged(month(api, asha, "2026-12"))
    assert "2026-12-21" in _flagged(month(api, asha, "2026-12"))
