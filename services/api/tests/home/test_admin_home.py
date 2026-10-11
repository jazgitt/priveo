"""The admin's home on real data and the read-only day schedule (BE-19)."""
from datetime import date

from sqlalchemy.orm import Session

from app.billing.models import MoneyAlert, Payment
from app.platform.db import utcnow
from app.support.alerts import raise_alert
from app.support.models import Complaint
from tests.scheduling.conftest import SUNDAY, admin, api, run_week, world  # noqa: F401
from tests.test_api import auth, login


def test_an_empty_home_is_all_zero(api, admin):
    home = api.get("/v1/admin/home", headers=admin).json()
    assert home["alert_count"] == 0 and home["needs_scheduling_count"] == 0
    assert home["payments_to_confirm"] == [] and home["payments_to_confirm_count"] == 0
    assert home["open_complaints_count"] == 0


def test_home_counts_alerts_payments_complaints_and_unscheduled_jobs(
        api, admin, world, run_week, engine):
    world.add_crew()
    for _ in range(4):
        world.add_vehicle()
    world.db.commit()
    run_week()
    with Session(engine) as db:
        raise_alert(db, "complaint", "Complaint raised", "Streaks")
        raise_alert(db, "complaint", "Another")
        pay = Payment(customer_id=world.customer.id, vehicle_id=world.vehicles[0].id,
                      kind="Plan", description="Plan, October", amount_rupees=1299,
                      status="Initiated", due_date=date(2026, 10, 20), initiated_at=utcnow())
        db.add(pay)
        db.add(Payment(customer_id=world.customer.id, vehicle_id=world.vehicles[1].id,
                       kind="Plan", description="Due one", amount_rupees=1299,
                       status="Due", due_date=date(2026, 10, 20)))
        db.flush()
        pay_id = str(pay.id)
        db.add(MoneyAlert(kind="payment_initiated", message="Paid", payment_id=pay.id))
        db.add(Complaint(number=1, customer_id=world.customer.id, category="Billing",
                         description="x", status="Raised"))
        db.add(Complaint(number=2, customer_id=world.customer.id, category="Billing",
                         description="y", status="Resolved"))
        db.commit()

    home = api.get("/v1/admin/home", headers=admin).json()
    assert home["support_alert_count"] == 2 and home["payment_alert_count"] == 1
    assert home["alert_count"] == 3
    assert home["needs_scheduling_count"] >= 1
    assert home["needs_scheduling_count"] == len(api.get(
        "/v1/admin/scheduling/needs-scheduling", headers=admin).json()["jobs"])
    assert home["open_complaints_count"] == 1
    assert home["payments_to_confirm_count"] == 1
    card = home["payments_to_confirm"][0]
    assert card["id"] == pay_id and card["amount_rupees"] == 1299
    assert card["customer_label"] == "Asha Rao, Flat A-101"
    assert card["reference"] == "Plan, October"
    assert {"id": str(world.society.id), "name": "DLF Meadows"} in home["societies"]


def test_marking_alerts_read_lowers_the_count(api, admin, engine):
    with Session(engine) as db:
        raise_alert(db, "complaint", "One")
    assert api.get("/v1/admin/home", headers=admin).json()["alert_count"] == 1
    api.post("/v1/admin/alerts/read-all", headers=admin)
    assert api.get("/v1/admin/home", headers=admin).json()["alert_count"] == 0


def test_day_schedule_groups_jobs_by_crew_and_hides_the_customer(api, admin, world, run_week):
    crew = world.add_crew(name="Ravi")
    world.add_crew(name="Sita")
    for _ in range(4):
        world.add_vehicle()
    world.db.commit()
    run_week()
    r = api.get("/v1/admin/schedule/day", headers=admin,
                params={"date": SUNDAY.isoformat(), "society_id": str(world.society.id)})
    assert r.status_code == 200, r.text
    day = r.json()
    assert day["date"] == SUNDAY.isoformat() and day["total"] == 4
    assert day["schedule_status"] == "Draft"
    assert day["done"] == 0 and day["left"] == 4
    names = [c["crew_name"] for c in day["crew"] if c["crew_id"]]
    assert names == sorted(names) and {"Ravi", "Sita"} <= set(names)
    ravi = next(c for c in day["crew"] if c["crew_id"] == str(crew.id))
    assert ravi["jobs"] and ravi["jobs"][0]["time"]
    assert "9876543210" not in r.text and "Asha" not in r.text and "Rao" not in r.text


def test_day_schedule_without_a_society_and_with_an_empty_day(api, admin, world, run_week):
    world.add_crew()
    world.add_vehicle()
    world.db.commit()
    run_week()
    day = api.get("/v1/admin/schedule/day", headers=admin,
                  params={"date": SUNDAY.isoformat()}).json()
    assert day["society_id"] is None and day["total"] == 1
    empty = api.get("/v1/admin/schedule/day", headers=admin,
                    params={"date": "2030-01-01"}).json()
    assert empty["total"] == 0 and empty["schedule_status"] is None and empty["crew"] == []


def test_day_schedule_is_for_admins_only(api, world):
    customer = auth(login(api, "customer")["access_token"])
    r = api.get("/v1/admin/schedule/day", headers=customer, params={"date": "2026-10-18"})
    assert r.status_code == 403
    assert api.get("/v1/admin/schedule/day", params={"date": "2026-10-18"}).status_code == 401
