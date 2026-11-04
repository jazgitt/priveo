"""The payment flow of the new model: one payment per cycle, due on the cycle's last
day, Initiated -> Paid or rejected, and the views (PAY-08 to PAY-19, SUB-09, SUB-10,
ADM-PAY-01 to ADM-PAY-15)."""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.billing.models import MoneyAlert, Payment, PaymentEvent
from app.billing.service import generate_due_payments, mark_overdue_and_inactive
from app.identity.models import Login
from app.notifications.models import Notification
from tests.billing.test_billing import admin_payment, vehicle
from tests.changes.money_fixtures import MOBILE, at

CYCLE1_END = date(2026, 10, 30)  # first service 1-Oct-26, 30 days counted


def sub_view(m):
    r = m.client.get(f"{vehicle(m)}/subscription", headers=m.customer)
    assert r.status_code == 200, r.text
    return r.json()


def current(m):
    """The payment screen for the current cycle (made if missing)."""
    r = m.client.post(f"{vehicle(m)}/payments/next", headers=m.customer)
    assert r.status_code == 200, r.text
    return r.json()["payment"]


def inbox(m):
    login = m.db.scalar(select(Login.id).where(Login.login_id == MOBILE))
    m.db.expire_all()
    return list(m.db.scalars(select(Notification).where(Notification.login_id == login)
                             .order_by(Notification.created_at)))


@pytest.mark.parametrize("d, status, message", [
    (8, "Not Due", ""), (7, "Due", "Due in 7 days"), (1, "Due", "Due in 1 day"),
    (0, "Due today", "Due today"), (-1, "Over due", "1 day over due"),
    (-7, "Over due", "7 days over due"),
])
def test_the_payment_status_follows_the_days_to_the_cycle_end(money, d, status, message):
    m = money
    current(m)  # the cycle's payment exists from the start
    m.clock.now = at(30) - timedelta(days=d)  # 30-Oct-26 is the cycle's last day
    p = current(m)
    assert (p["status"], p["status_message"], p["days_to_due"]) == (status, message, d)
    assert p["due_date"] == "2026-10-30" and p["cycle_end"] == "2026-10-30"
    assert p["cycle_start"] == "2026-10-01" and p["last_payment_failed"] is False


def test_the_cycle_has_one_payment_and_pay_any_time_is_allowed(money):
    m = money
    first = current(m)  # 11-Oct-26: 19 days before the end, no "too early"
    assert first["status"] == "Not Due"
    assert current(m)["id"] == first["id"]
    assert len(m.db.scalars(select(Payment)).all()) == 1
    r = m.client.post(f"/v1/customer/payments/{first['id']}/paid", headers=m.customer)
    assert r.json()["payment"]["status"] == "Initiated"
    # A second tap changes nothing: one Initiated payment for the cycle.
    again = m.client.post(f"/v1/customer/payments/{first['id']}/paid", headers=m.customer)
    assert again.status_code == 200 and again.json()["payment"]["status"] == "Initiated"
    assert len(m.db.scalars(select(MoneyAlert)).all()) == 1
    # The screen for the cycle returns the same payment, not a new one.
    assert current(m)["id"] == first["id"]
    assert len(m.db.scalars(select(Payment)).all()) == 1


def test_early_payment_does_not_move_the_cycle_dates(money):
    m = money
    before = sub_view(m)
    p = current(m)
    m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    m.client.post(f"/v1/admin/payments/{p['id']}/confirm", headers=m.admin)
    after = sub_view(m)
    assert after["cycle_start"] == before["cycle_start"] == "2026-10-01"
    assert after["payment_status"] == "Paid"
    # The next cycle starts the day after the end, with its own Not Due payment.
    m.clock.now = at(31)
    generate_due_payments(m.clock.now, m.db)
    nxt = sub_view(m)
    assert nxt["cycle_start"] == "2026-10-31" and nxt["payment_status"] == "Not Due"
    assert nxt["payment_id"] != after["payment_id"]


def test_a_late_payment_keeps_the_next_cycles_dates(money):
    m = money
    current(m)
    m.clock.now = at(1, month=11)  # one day over due
    p = current(m)
    assert p["status"] == "Over due"
    m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    m.client.post(f"/v1/admin/payments/{p['id']}/confirm", headers=m.admin)
    generate_due_payments(m.clock.now, m.db)
    view = sub_view(m)
    assert view["cycle_start"] == "2026-10-31"
    rows = m.db.scalars(select(Payment).where(Payment.subscription_id == m.subscription_id)
                        .order_by(Payment.cycle_start)).all()
    assert [(r.cycle_start.isoformat(), r.due_date.isoformat(), r.status) for r in rows] == [
        ("2026-10-01", "2026-10-30", "Paid"), ("2026-10-31", "2026-11-29", "Open")]


def test_approve_tells_the_customer_with_the_cycle_and_vehicle(money):
    m = money
    p = current(m)
    m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    r = m.client.post(f"/v1/admin/payments/{p['id']}/confirm", headers=m.admin)
    assert r.json()["status"] == "Paid" and r.json()["status_message"] == "Payment received"
    [note] = inbox(m)
    assert (note.event, note.title) == ("payment_received", "Payment received")
    assert "Hyundai Creta" in note.body and "01-Oct-26 to 30-Oct-26" in note.body
    row = m.db.scalar(select(Payment))
    assert row.received_at is not None and row.confirmed_by is not None
    events = m.db.scalars(select(PaymentEvent).order_by(PaymentEvent.at)).all()
    assert [e.to_status for e in events] == ["Not Due", "Initiated", "Paid"]


def test_reject_goes_back_to_the_date_status_with_the_failed_flag(money):
    m = money
    m.clock.now = at(27)  # 3 days to the end
    p = current(m)
    m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    r = m.client.post(f"/v1/admin/payments/{p['id']}/reject", headers=m.admin).json()
    assert (r["status"], r["last_payment_failed"], r["days_to_due"]) == ("Due", True, 3)
    mine = sub_view(m)
    assert (mine["payment_status"], mine["last_payment_failed"]) == ("Due", True)
    [note] = inbox(m)
    assert (note.event, note.title) == ("payment_failed", "Your last payment failed")
    row = m.db.scalar(select(Payment))
    assert row.status == "Open" and row.rejected_at is not None and row.received_at is None
    # The customer can mark it paid again; the flag clears.
    again = m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer).json()
    assert again["payment"]["status"] == "Initiated"
    assert again["payment"]["last_payment_failed"] is False
    # A second rejection is told again.
    m.clock.now = at(27, 11)
    m.client.post(f"/v1/admin/payments/{p['id']}/reject", headers=m.admin)
    assert [n.event for n in inbox(m)] == ["payment_failed", "payment_failed"]


def test_admin_override_and_moving_back_sends_no_message(money):
    m = money
    p = current(m)
    url = f"/v1/admin/payments/{p['id']}/status"
    for status in ("Initiated", "Paid"):
        assert m.client.put(url, json={"status": status}, headers=m.admin).json()["status"] == status
    assert [n.event for n in inbox(m)] == ["payment_received"]
    # A date-based status means Open: the date rule shows which.
    back = m.client.put(url, json={"status": "Over due"}, headers=m.admin).json()
    assert back["status"] == "Not Due" and back["received_on"] is None
    assert back["last_payment_failed"] is False
    assert m.db.scalar(select(Payment)).status == "Open"
    assert [n.event for n in inbox(m)] == ["payment_received"]
    assert m.client.put(url, json={"status": "Received"}, headers=m.admin).status_code == 422


def test_the_admin_can_record_an_offline_payment_for_a_past_cycle(money):
    m = money
    m.clock.now = at(20, month=12)
    old = admin_payment(m, cycle_start="2026-10-01", status="Paid", amount_rupees=1299)
    assert (old["status"], old["cycle_start"], old["cycle_end"]) == (
        "Paid", "2026-10-01", "2026-10-30")
    assert old["due_date"] == "2026-10-30" and old["received_on"] == "2026-12-20"
    assert inbox(m) == []  # History is not announced to the customer.
    dup = m.client.post("/v1/admin/payments", headers=m.admin, json={
        "vehicle_id": m.vehicle_id, "amount_rupees": 1299, "cycle_start": "2026-10-01"})
    assert dup.status_code == 409 and dup.json()["code"] == "payment_exists"
    # An open payment of the cycle is updated, not doubled.
    open_p = current(m)  # the cycle of 20-Dec-26 starts 29-Nov-26
    assert open_p["cycle_start"] == "2026-11-30" or open_p["status"] == "Over due"
    done = admin_payment(m, cycle_start=open_p["cycle_start"], status="Paid")
    assert done["id"] == open_p["id"] and done["status"] == "Paid"


def test_plan_card_hides_the_end_date_unless_over_due(money):
    m = money
    current(m)
    for day, status in ((11, "Not Due"), (25, "Due"), (30, "Due today")):
        m.clock.now = at(day)
        v = sub_view(m)
        assert v["payment_status"] == status
        for hidden in ("cycle_end", "inactive_by", "expires_on", "renewal_date", "days_left"):
            assert v[hidden] is None, (day, hidden)
        assert v["cycle_start"] == "2026-10-01"
    m.clock.now = at(2, month=11)
    v = sub_view(m)
    assert v["payment_status"] == "Over due" and v["days_to_due"] == -3
    assert v["status_message"] == "3 days over due"
    assert (v["cycle_end"], v["inactive_by"]) == ("2026-10-30", "2026-11-06")
    assert v["expires_on"] == "2026-10-30" and v["can_pay_next"] is True


def test_auto_inactive_still_fires_with_its_alert(money):
    m = money
    p = admin_payment(m, cycle_start="2026-10-01")
    assert p["status"] == "Not Due"
    mark_overdue_and_inactive(at(6, month=11), m.db)  # 7 days over due
    assert m.subscription().status == "Active"
    report = mark_overdue_and_inactive(at(7, month=11), m.db)  # more than 7
    assert report.inactivated == [m.subscription_id]
    assert [a.kind for a in m.db.scalars(select(MoneyAlert))] == ["auto_inactive"]
    # Initiated stops the clock: the same set-up, but marked paid, stays Active.


def test_an_initiated_payment_is_not_made_inactive(money):
    m = money
    p = current(m)
    m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    assert mark_overdue_and_inactive(at(20, month=11), m.db).inactivated == []


def test_the_job_makes_the_current_cycle_payment_once(money):
    m = money

    def mine():
        m.db.expire_all()
        return sorted(r.cycle_start.isoformat() for r in m.db.scalars(
            select(Payment).where(Payment.subscription_id == m.subscription_id)))

    generate_due_payments(at(11), m.db)
    generate_due_payments(at(12), m.db)
    assert mine() == ["2026-10-01"]
    generate_due_payments(at(30), m.db)
    assert mine() == ["2026-10-01"]  # the last day of the cycle: no new row yet
    generate_due_payments(at(31), m.db)
    generate_due_payments(at(31, 12), m.db)
    assert mine() == ["2026-10-01", "2026-10-31"]


def test_list_filters_and_tiles_use_the_display_statuses(money):
    m = money
    admin_payment(m, cycle_start="2026-10-01", amount_rupees=1000)  # ends 30-Oct: Not Due
    admin_payment(m, cycle_start="2026-09-01", amount_rupees=700)  # ended 30-Sep: Over due
    admin_payment(m, cycle_start="2026-08-02", status="Paid", amount_rupees=500)
    admin_payment(m, cycle_start="2026-07-03", status="Initiated", amount_rupees=300)
    m.clock.now = at(25)

    def ids(status):
        r = m.client.get("/v1/admin/payments", params={"status": status}, headers=m.admin)
        assert r.status_code == 200, r.text
        return [x["status"] for x in r.json()]

    assert ids("Over due") == ["Over due"]  # the cycle that ended 30-Sep-26
    assert ids("Due") == ["Due"] and ids("Paid") == ["Paid"] and ids("Initiated") == ["Initiated"]
    assert ids("Not Due") == [] and ids("Due today") == []
    s = m.client.get("/v1/admin/payments/summary", headers=m.admin).json()
    assert list(s["by_status"]) == ["Not Due", "Due", "Due today", "Over due", "Initiated", "Paid"]
    assert s["by_status"]["Paid"] == {"count": 1, "rupees": 500}
    assert s["by_status"]["Over due"] == {"count": 1, "rupees": 700} and s["total"] == 4
    assert s["total_rupees"] == 1000 + 700 + 500 + 300
    bad = m.client.get("/v1/admin/payments", params={"status": "Received"}, headers=m.admin)
    assert bad.status_code == 422


def test_an_add_on_keeps_its_own_status_logic(money):
    m = money
    r = m.client.post(f"{vehicle(m)}/addons", json={"date": "2026-10-20", "finish_by": "12:00"},
                      headers=m.customer)
    assert r.status_code == 201, r.text
    row = m.db.scalar(select(Payment))
    assert row.kind == "Add-on" and row.status == "Open"
    m.clock.now = at(25)  # after the service date, service not done: still Due
    assert m.client.get(f"{vehicle(m)}/payments", headers=m.customer).json()[0]["status"] == "Due"
    from app.addons.models import AddonBooking

    m.db.scalar(select(AddonBooking)).status = "Completed"
    m.db.commit()
    mark_overdue_and_inactive(at(25), m.db)
    assert m.client.get(f"{vehicle(m)}/payments", headers=m.customer).json()[0]["status"] == "Over due"
    assert m.subscription().status == "Active"


def test_unknown_payment_is_not_found(money):
    r = money.client.put(f"/v1/admin/payments/{uuid.uuid4()}/status", json={"status": "Paid"},
                         headers=money.admin)
    assert r.status_code == 404
