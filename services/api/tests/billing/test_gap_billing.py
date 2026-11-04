"""P03: billing lifecycle and pause updates without waiting for a cron."""
import uuid
from datetime import date

from sqlalchemy import select

from app.billing.models import Payment
from app.billing.service import generate_due_payments, mark_overdue_and_inactive
from app.changes.models import ScheduleChange
from app.customers.models import Customer
from tests.billing.test_billing import admin_payment, vehicle
from tests.changes.money_fixtures import at


def reactivate(m, first="2026-11-02"):
    url = f"/v1/admin/subscriptions/{m.subscription_id}/status"
    for body in ({"status": "Inactive"}, {"status": "Activating"},
                 {"status": "Active", "first_service_date": first}):
        r = m.client.put(url, json=body, headers=m.admin)
        assert r.status_code == 200, r.text
    return url


def test_reactivation_creates_one_new_due_cycle_and_keeps_old_receipt(money):
    m = money
    old = admin_payment(m, status="Paid", cycle_start="2026-10-01")
    url = reactivate(m)
    m.db.expire_all()
    rows = m.db.scalars(select(Payment).where(Payment.subscription_id == m.subscription_id)).all()
    assert len(rows) == 2
    new = next(p for p in rows if str(p.id) != old["id"])
    assert (new.status, new.due_date, new.cycle_start, new.cycle_end) == (
        "Open", date(2026, 12, 1), date(2026, 11, 2), date(2026, 12, 2))
    assert new.amount_rupees == 1299
    assert m.db.get(Payment, next(p.id for p in rows if str(p.id) == old["id"])).status == "Paid"
    assert m.client.put(url, headers=m.admin, json={
        "status": "Active", "first_service_date": "2026-11-02"}).status_code == 409
    # A future first-service payment must not be silently moved to renewal.
    generate_due_payments(at(30), m.db)
    m.db.expire_all()
    assert m.db.get(Payment, new.id).due_date == date(2026, 12, 1)
    assert len(m.db.scalars(select(Payment).where(
        Payment.subscription_id == m.subscription_id)).all()) == 2


def test_reactivation_requires_new_date_without_changing_state(money):
    m = money
    url = f"/v1/admin/subscriptions/{m.subscription_id}/status"
    for status in ("Inactive", "Activating"):
        assert m.client.put(url, headers=m.admin, json={"status": status}).status_code == 200
    assert m.client.put(url, headers=m.admin, json={"status": "Active"}).status_code == 422
    assert m.subscription().status == "Activating"
    assert not m.db.scalars(select(Payment)).all()


def test_previous_activation_pause_and_debt_do_not_inactivate_new_cycle(money):
    m = money
    admin_payment(m, status="Over due", cycle_start="2026-10-01")
    m.db.add(ScheduleChange(customer_id=m.customer_id, vehicle_id=uuid.UUID(m.vehicle_id),
                            kind="pause", start_date=date(2026, 10, 5), end_date=date(2026, 10, 8),
                            status="Active", actor="customer",
                            actor_login_id=m.db.get(Customer, m.customer_id).login_id))
    m.db.commit()
    reactivate(m)
    mark_overdue_and_inactive(at(3, month=11), m.db)
    assert m.subscription().status == "Active"
    # Keep clock within the new activation when reading the window.
    m.clock.now = at(3, month=11)
    view = m.client.get(f"{vehicle(m)}/subscription", headers=m.customer).json()
    assert view["cycle_start"] == "2026-11-02" and view["payment_status"] == "Not Due"
    assert view["renewal_date"] is None  # the old debt belongs to the previous activation


def test_reactivation_cycle_collision_keeps_old_payment_and_activating_state(money):
    m = money
    admin_payment(m, status="Paid", cycle_start="2026-11-02")
    url = f"/v1/admin/subscriptions/{m.subscription_id}/status"
    for status in ("Inactive", "Activating"):
        assert m.client.put(url, headers=m.admin, json={"status": status}).status_code == 200
    result = m.client.put(url, headers=m.admin, json={
        "status": "Active", "first_service_date": "2026-11-02"})
    assert result.status_code == 409 and result.json()["code"] == "cycle_exists"
    assert m.subscription().status == "Activating"
    assert m.subscription().first_service_date == date(2026, 10, 1)
    assert len(m.db.scalars(select(Payment)).all()) == 1


def test_payment_submission_has_vehicle_preferences_and_amount_uri(money):
    from urllib.parse import parse_qs, urlparse

    m = money
    row = admin_payment(m)
    result = m.client.post(f"/v1/customer/payments/{row['id']}/paid", headers=m.customer)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["payment"]["status"] == "Initiated"
    assert "Creta" in body["vehicle"] and "HR 26 DK 8337" in body["vehicle"]
    assert body["service_details"]["cutoff_time"] == "07:00"
    assert body["service_details"]["interior_day"] == "Friday"
    assert parse_qs(urlparse(body["instructions"]["upi_uri"]).query)["am"] == ["1299"]


def test_payment_paging_does_not_repeat_identical_sort_values(money):
    m = money
    for index in range(105):
        m.db.add(Payment(customer_id=m.customer_id, vehicle_id=uuid.UUID(m.vehicle_id),
                         kind="Add-on", description=f"Record {index}", amount_rupees=100,
                         status="Open", due_date=date(2026, 10, 31)))
    m.db.commit()
    ids = []
    for offset in (0, 50, 100):
        r = m.client.get(f"/v1/admin/payments?limit=50&offset={offset}", headers=m.admin)
        assert r.status_code == 200, r.text
        ids.extend(p["id"] for p in r.json())
    assert len(ids) == len(set(ids)) == 105
    assert m.client.get("/v1/admin/payments?limit=50&society=Unknown", headers=m.admin).json() == []
