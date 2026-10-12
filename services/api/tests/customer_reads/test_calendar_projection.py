"""The projected calendar: dates the scheduler has not planned yet come from
the subscription, planned visits win, and the day states are marked
(CAL-01, CAL-02, CAL-05 to CAL-10, SUB-08)."""

import uuid
from datetime import date, datetime, time

import pytest

import app.changes.models  # noqa: F401
from app import changes
from app.changes.gateway import InMemoryScheduleChangeGateway, get_schedule_gateway
from app.changes.models import ScheduleChange
from app.changes.rules import get_now
from app.customer_reads.repository import Job, Visit
from app.customer_reads.service import CustomerReads
from app.customers.models import Customer, Subscription
from app.platform.clock import IST


@pytest.fixture
def clock(api):
    holder = {"now": datetime(2026, 10, 11, 10, 0, tzinfo=IST)}
    api.app.dependency_overrides[get_now] = lambda: lambda: holder["now"]
    changes.register(api.app)
    gateway = InMemoryScheduleChangeGateway()
    api.app.dependency_overrides[get_schedule_gateway] = lambda: gateway
    return holder


def month(api, asha, text, vehicle=0):
    r = api.get(
        f"/v1/customer/calendar?month={text}&vehicle_id={asha['vehicles'][vehicle]}",
        headers=asha["headers"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def by_date(body):
    return {v["date"]: v for v in body["visits"]}


def test_a_future_month_is_projected_from_the_subscription(api, asha, clock):
    days = by_date(month(api, asha, "2026-12"))
    assert len(days) == 31
    first = days["2026-12-02"]
    assert first["source"] == "projected" and first["status"] == "Projected"
    assert first["visit_id"] is None and first["services"] == ["Cleaning-External"]
    assert first["cutoff_time"] == "07:00" and first["can_change"] is True
    # 04-Dec-26 is a Friday: the interior care day.
    assert days["2026-12-04"]["services"] == ["Cleaning-External", "Cleaning-Internal"]


def test_planned_visits_win_over_projected_days(api, asha, clock):
    body = month(api, asha, "2026-11")
    days = by_date(body)
    assert len(body["visits"]) == 30
    assert days["2026-11-02"]["source"] == "visit" and days["2026-11-02"]["visit_id"] == "v-1"
    assert days["2026-11-03"]["status"] == "Skipped"
    assert days["2026-11-04"]["source"] == "projected"
    assert days["2026-11-20"]["source"] == "visit"


def test_spa_visit_does_not_replace_the_projected_plan_clean(api, asha, clock, repo):
    repo.visit_rows.append(Visit("spa", asha["vehicles"][0], date(2026, 11, 22), "Scheduled"))
    repo.job_rows.append(Job("spa-job", "spa", "Deep Spa", "Scheduled"))
    body = month(api, asha, "2026-11")
    assert len(body["visits"]) == 31
    spa_day = [v for v in body["visits"] if v["date"] == "2026-11-22"]
    assert len(spa_day) == 2
    assert any(v["source"] == "projected" for v in spa_day)
    assert any(v["services"] == ["Deep Spa"] for v in spa_day)


def test_no_projection_for_the_past_or_without_an_active_subscription(api, asha, clock, db):
    assert month(api, asha, "2026-09")["visits"] == []
    for sub in db.query(Subscription).all():
        sub.status = "Inactive"
    db.commit()
    rows = month(api, asha, "2026-12")["visits"]
    assert [v for v in rows if v["source"] == "projected"] == []


def test_skip_pause_and_cutoff_change_on_projected_days(api, asha, clock):
    vid = asha["vehicles"][0]
    h = asha["headers"]
    r = api.post(f"/v1/customer/vehicles/{vid}/skips", json={"date": "2026-12-05"}, headers=h)
    assert r.status_code == 201, r.text
    day = by_date(month(api, asha, "2026-12"))["2026-12-05"]
    assert day["status"] == "Skipped" and day["skip_id"] == r.json()["id"]
    assert day["can_change"] is True
    r = api.delete(f"/v1/customer/vehicles/{vid}/skips/{r.json()['id']}", headers=h)
    assert r.status_code == 204
    assert by_date(month(api, asha, "2026-12"))["2026-12-05"]["status"] == "Projected"
    r = api.post(
        f"/v1/customer/vehicles/{vid}/pauses",
        json={"from_date": "2026-12-10", "to_date": "2026-12-11"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = month(api, asha, "2026-12")
    assert by_date(body)["2026-12-10"]["status"] == "Paused"
    assert by_date(body)["2026-12-10"]["can_change"] is False
    r = api.post(
        f"/v1/customer/vehicles/{vid}/cutoff-changes",
        json={"date": "2026-12-12", "cutoff_time": "08:30"},
        headers=h,
    )
    assert r.status_code == 201
    assert by_date(month(api, asha, "2026-12"))["2026-12-12"]["cutoff_time"] == "08:30"


def test_renewal_dates_move_with_a_pause(api, asha, clock):
    vid = asha["vehicles"][0]
    # First service 14-Sep-26: renewals on 14-Oct-26, 13-Nov-26, 13-Dec-26.
    assert [r["date"] for r in month(api, asha, "2026-12")["renewals"]] == ["2026-12-13"]
    api.post(
        f"/v1/customer/vehicles/{vid}/pauses",
        json={"from_date": "2026-12-20", "to_date": "2026-12-21"},
        headers=asha["headers"],
    )
    # Two paused days: the renewals before the pause move two days on.
    assert [r["date"] for r in month(api, asha, "2026-12")["renewals"]] == ["2026-12-15"]


def test_a_requested_cutoff_change_keeps_the_current_value(api, asha, clock, db):
    customer = db.query(Customer).filter_by(email="asha@example.com").one()
    db.add(
        ScheduleChange(
            customer_id=customer.id,
            vehicle_id=uuid.UUID(asha["vehicles"][0]),
            kind="cutoff",
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 20),
            cutoff_time=time(9, 0),
            status="Requested",
            actor="customer",
        )
    )
    db.commit()
    day = by_date(month(api, asha, "2026-11"))["2026-11-20"]
    assert day["change_requested"] is True and day["state"] == "Change requested"
    assert day["requested_cutoff_time"] == "09:00"
    assert day["cutoff_time"] == "07:00"


def test_missed_visits_show_covered_and_rescheduled_dates(api, asha, clock, repo):
    vid = asha["vehicles"][0]
    repo.visit_rows.extend(
        [
            Visit("m-1", vid, date(2026, 10, 5), "Missed"),
            Visit("m-2", vid, date(2026, 10, 6), "Scheduled"),
            Visit("m-3", vid, date(2026, 10, 2), "Missed"),
            Visit("m-4", vid, date(2026, 10, 7), "Scheduled"),
        ]
    )
    repo.job_rows.extend(
        [
            Job("mj-1", "m-1", "Cleaning-External", "Missed"),
            Job("mj-2", "m-2", "Cleaning-External", "Pending"),
            # A missed interior clean on a Friday, done again on a Wednesday.
            Job("mj-3", "m-3", "Cleaning-Internal", "Missed"),
            Job("mj-4", "m-4", "Cleaning-Internal", "Pending"),
        ]
    )
    days = by_date(month(api, asha, "2026-10"))
    assert days["2026-10-05"]["state"] == "Covered"
    assert days["2026-10-05"]["covered_on"] == "2026-10-06"
    assert days["2026-10-02"]["state"] == "Rescheduled"
    assert days["2026-10-02"]["rescheduled_on"] == "2026-10-07"


def test_spa_does_not_cover_a_missed_exterior_job(api, asha, clock, repo):
    vid = asha["vehicles"][0]
    repo.visit_rows.extend(
        [
            Visit("missed-ext", vid, date(2026, 10, 5), "Missed"),
            Visit("spa-only", vid, date(2026, 10, 6), "Completed"),
        ]
    )
    repo.job_rows.extend(
        [
            Job("ext", "missed-ext", "Cleaning-External", "Missed"),
            Job("spa", "spa-only", "Deep Spa", "Done"),
        ]
    )
    day = next(v for v in month(api, asha, "2026-10")["visits"] if v["visit_id"] == "missed-ext")
    assert day["covered_on"] is None


def test_assignment_shows_only_for_a_frozen_schedule(api, asha, clock, repo):
    vid = asha["vehicles"][0]
    repo.visit_rows.extend(
        [
            Visit("f-1", vid, date(2026, 10, 12), "Scheduled", frozen=True),
            Visit("f-2", vid, date(2026, 10, 13), "Scheduled", frozen=False),
        ]
    )
    repo.job_rows.extend(
        [
            Job(
                "fj-1",
                "f-1",
                "Cleaning-External",
                "Pending",
                crew_name="Ravi Kumar",
                start_minute=420,
                duration_minutes=20,
            ),
            Job(
                "fj-2",
                "f-2",
                "Cleaning-External",
                "Pending",
                crew_name="Ravi Kumar",
                start_minute=420,
                duration_minutes=20,
            ),
        ]
    )
    days = by_date(month(api, asha, "2026-10"))
    assert days["2026-10-12"]["crew_name"] == "Ravi Kumar"
    assert days["2026-10-12"]["start_time"] == "07:00"
    assert days["2026-10-12"]["end_time"] == "07:20"
    assert days["2026-10-13"]["crew_name"] is None
    assert "mobile" not in str(days["2026-10-12"])


def test_next_service_is_projected_without_a_planned_visit(db, asha, repo):
    login = db.query(Customer).filter_by(email="asha@example.com").one().login_id
    now = datetime(2026, 12, 20, 10, 0, tzinfo=IST)
    reads = CustomerReads(db, repo, lambda: now)
    items = reads.next_services(login, date(2026, 12, 20))
    assert [(i.date, i.source, i.visit_id) for i in items] == [
        (date(2026, 12, 21), "projected", None)
    ] * 2
    assert items[0].services == ["Cleaning-External"]
    assert items[0].cutoff_time == "07:00"


def test_preferences_change_the_default_cutoff_and_interior_day(api, asha, clock, db):
    vid = asha["vehicles"][0]
    r = api.patch(
        f"/v1/customer/vehicles/{vid}/preferences",
        json={"cutoff_time": "08:30", "interior_day": "Wednesday"},
        headers=asha["headers"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cutoff_time"] == "08:30" and body["interior_day"] == "Wednesday"
    # 11-Oct-26 10:00: tomorrow is still before its 9 PM cutoff.
    assert body["applies_from"] == "2026-10-12"
    days = by_date(month(api, asha, "2026-12"))
    assert days["2026-12-02"]["services"] == ["Cleaning-External", "Cleaning-Internal"]
    assert days["2026-12-04"]["services"] == ["Cleaning-External"]
    assert days["2026-12-04"]["cutoff_time"] == "08:30"
    bad = api.patch(
        f"/v1/customer/vehicles/{vid}/preferences",
        json={"cutoff_time": "08:15"},
        headers=asha["headers"],
    )
    assert bad.status_code == 422
    assert (
        api.patch(
            f"/v1/customer/vehicles/{vid}/preferences", json={}, headers=asha["headers"]
        ).status_code
        == 422
    )


def test_preferences_after_9pm_apply_from_the_day_after(api, asha, clock):
    clock["now"] = datetime(2026, 10, 11, 21, 30, tzinfo=IST)
    r = api.patch(
        f"/v1/customer/vehicles/{asha['vehicles'][0]}/preferences",
        json={"cutoff_time": "09:00"},
        headers=asha["headers"],
    )
    assert r.json()["applies_from"] == "2026-10-13"
