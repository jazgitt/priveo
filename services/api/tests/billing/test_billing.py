"""Payments: Not Due .. Over due, Initiated, Paid; the 7-day Inactive rule;
invoices; the admin's confirmation (PAY-, SUB-, ADM-PAY-, ADM-SUB-)."""
import uuid

import pytest
from sqlalchemy import select

from app.billing.models import MoneyAlert, Payment, PaymentEvent
from app.billing.service import generate_due_payments, mark_overdue_and_inactive
from tests.changes.money_fixtures import at
from tests.directory_helpers import set_setting


def vehicle(m):
    return f"/v1/customer/vehicles/{m.vehicle_id}"


def admin_payment(m, **kw):
    body = {"vehicle_id": m.vehicle_id, "amount_rupees": 1299, **kw}
    r = m.client.post("/v1/admin/payments", json=body, headers=m.admin)
    assert r.status_code == 201, r.text
    return r.json()


def test_my_subscription_shows_the_cycle(money):
    m = money
    s = m.client.get(f"{vehicle(m)}/subscription", headers=m.customer).json()
    assert (s["status"], s["cycle_start"], s["cycle_days"]) == ("Active", "2026-10-01", 30)
    # The end date is hidden unless the payment is Over due (SUB-01).
    assert (s["renewal_date"], s["expires_on"], s["days_left"]) == (None, None, None)
    assert (s["monthly_price_rupees"], s["payment_method"]) == (1299, "UPI")
    assert (s["registration"], s["society"], s["can_pay_next"]) == (
        "HR 26 DK 8337", "DLF Meadows", True)
    assert (s["payment_status"], s["days_to_due"]) == ("Not Due", 19)
    assert s["latest_payment"] is None


def test_a_confirmed_early_payment_does_not_move_the_cycle(money):
    """Paying the current cycle early only changes its status (PAY-15)."""
    m = money
    p = admin_payment(m, cycle_start="2026-10-01")
    m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    m.client.post(f"/v1/admin/payments/{p['id']}/confirm", headers=m.admin)
    s = m.client.get(f"{vehicle(m)}/subscription", headers=m.customer).json()
    assert (s["cycle_start"], s["payment_status"], s["expires_on"]) == ("2026-10-01", "Paid", None)
    home = m.client.get("/v1/customer/home", headers=m.customer).json()
    assert [v["expires_on"] for v in home["vehicles"]] == [None]  # hidden unless Over due


def test_admin_lists_subscriptions_with_filters_and_a_status_history(money):
    m = money
    rows = m.client.get("/v1/admin/subscriptions", headers=m.admin).json()
    row = next(r for r in rows if r["vehicle_id"] == m.vehicle_id)
    assert (row["customer_name"], row["flat"], row["society"], row["status"]) == (
        "Meera Rao", "A-101", "DLF Meadows", "Active")
    assert row["first_service_date"] == "2026-10-01" and row["renewal_date"] == "2026-10-31"
    assert "Hyundai Creta" in row["vehicle"]

    def ids(status):
        r = m.client.get("/v1/admin/subscriptions", params={"status": status}, headers=m.admin)
        assert r.status_code == 200, r.text
        return {x["subscription_id"] for x in r.json()}

    sid = str(m.subscription_id)
    assert sid in ids("Active") and sid not in ids("Inactive") and sid not in ids("Paused")
    assert len(m.client.get("/v1/admin/subscriptions", params={"limit": 1},
                            headers=m.admin).json()) == 1

    # A pause running today shows the subscription as Paused.
    m.client.post(f"/v1/customer/vehicles/{m.vehicle_id}/pauses",
                  json={"from_date": "2026-10-12", "to_date": "2026-10-14"}, headers=m.customer)
    m.clock.now = at(13, 10)
    assert sid in ids("Paused") and sid not in ids("Active")

    # Status changes are listed newest first, with who made them.
    r = m.client.put(f"/v1/admin/subscriptions/{sid}/status", headers=m.admin,
                     json={"status": "Inactive", "reason": "Moved away"})
    assert r.status_code == 200, r.text
    events = m.client.get(f"/v1/admin/subscriptions/{sid}/events", headers=m.admin).json()
    assert (events[0]["from_status"], events[0]["to_status"], events[0]["reason"]) == (
        "Active", "Inactive", "Moved away")
    assert events[0]["by"] != ""
    assert sid in ids("Inactive")
    missing = m.client.get(f"/v1/admin/subscriptions/{uuid.uuid4()}/events", headers=m.admin)
    assert missing.status_code == 404
    # The Site selector limits the list to one society (ADM-SITE-01).
    other = m.client.get("/v1/admin/subscriptions", params={"society_id": str(uuid.uuid4())},
                         headers=m.admin)
    assert other.status_code == 200 and other.json() == []
    # Only an admin may read the list.
    assert m.client.get("/v1/admin/subscriptions", headers=m.customer).status_code == 403


def test_a_payment_runs_from_not_due_to_paid(money):
    m = money
    p = admin_payment(m)
    assert (p["status"], p["kind"], p["customer_name"], p["flat"]) == (
        "Not Due", "Plan", "Meera Rao", "A-101")
    detail = m.client.get(f"/v1/customer/payments/{p['id']}", headers=m.customer).json()
    assert detail["instructions"]["amount_rupees"] == 1299
    assert detail["instructions"]["upi_id"].endswith("@upi")  # A placeholder.
    assert "upi://pay?pa=" in detail["instructions"]["upi_uri"]

    r = m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    assert r.json()["payment"]["status"] == "Initiated"
    # The admin is alerted, and sees it in the list to confirm (ADM-PAY-11).
    alerts = m.client.get("/v1/admin/payment-alerts", headers=m.admin).json()
    assert alerts[0]["kind"] == "payment_initiated" and alerts[0]["payment_id"] == p["id"]
    to_confirm = m.client.get("/v1/admin/payments?status=Initiated", headers=m.admin).json()
    assert [x["id"] for x in to_confirm] == [p["id"]]

    r = m.client.post(f"/v1/admin/payments/{p['id']}/confirm", headers=m.admin)
    assert r.json()["status"] == "Paid" and r.json()["received_on"] == "2026-10-11"
    hist = m.client.get(f"{vehicle(m)}/payments", headers=m.customer).json()
    assert [(h["status"], h["amount_rupees"]) for h in hist] == [("Paid", 1299)]
    r = m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    assert r.status_code == 409 and r.json()["code"] == "already_received"
    events = m.db.scalars(select(PaymentEvent).order_by(PaymentEvent.at)).all()
    assert [(e.from_status, e.to_status) for e in events] == [
        (None, "Not Due"), ("Not Due", "Initiated"), ("Initiated", "Paid")]


def test_i_have_paid_twice_is_one_change(money):
    m = money
    p = admin_payment(m)
    for _ in range(2):
        assert m.client.post(f"/v1/customer/payments/{p['id']}/paid",
                             headers=m.customer).status_code == 200
    assert len(m.db.scalars(select(MoneyAlert)).all()) == 1


def test_the_admin_can_reject_and_move_back(money):
    m = money
    p = admin_payment(m, cycle_start="2026-09-01")  # ended 30-Sep-26
    m.client.post(f"/v1/customer/payments/{p['id']}/paid", headers=m.customer)
    r = m.client.post(f"/v1/admin/payments/{p['id']}/reject", headers=m.admin)
    assert r.json()["status"] == "Over due"  # The date has passed.
    assert r.json()["last_payment_failed"] is True
    r = m.client.put(f"/v1/admin/payments/{p['id']}/status", json={"status": "Paid"},
                     headers=m.admin)
    assert r.json()["status"] == "Paid"
    r = m.client.put(f"/v1/admin/payments/{p['id']}/status", json={"status": "Due"},
                     headers=m.admin)
    assert r.json()["status"] == "Over due" and r.json()["received_on"] is None
    r = m.client.put(f"/v1/admin/payments/{p['id']}/status", json={"status": "Received"},
                     headers=m.admin)
    assert r.status_code == 422


def test_the_admin_can_record_an_offline_payment(money):
    p = admin_payment(money, status="Paid")
    assert p["status"] == "Paid"


def test_over_due_then_inactive_after_seven_days(money):
    m = money
    p = admin_payment(m, cycle_start="2026-10-01")  # last day 30-Oct-26
    sub_id = m.subscription_id

    # On the last day it is still Due today.
    mark_overdue_and_inactive(at(30, 23, 59), m.db)
    assert m.db.get(Payment, uuid.UUID(p["id"])).overdue_since is None

    # The day after, it is Over due and the subscription is still Active.
    report = mark_overdue_and_inactive(at(31, 1, 0), m.db)
    assert report.marked_overdue == 1 and report.inactivated == []
    assert m.subscription().status == "Active"
    row = m.db.scalar(select(Payment))
    assert (row.status, row.overdue_since.isoformat()) == ("Open", "2026-10-31")  # shown Over due

    # Seven days over due: still Active. Eight: Inactive.
    mark_overdue_and_inactive(at(6, 12, month=11), m.db)
    assert m.subscription().status == "Active"
    report = mark_overdue_and_inactive(at(7, 0, 5, month=11), m.db)
    assert report.inactivated == [sub_id]
    assert m.subscription().status == "Inactive"

    # Running it again changes nothing more.
    again = mark_overdue_and_inactive(at(9, 8, month=11), m.db)
    assert again.marked_overdue == 0 and again.inactivated == []
    assert [a.kind for a in m.db.scalars(select(MoneyAlert))] == ["auto_inactive"]
    s = m.client.get(f"{vehicle(m)}/subscription", headers=m.customer).json()
    assert s["status"] == "Inactive"


def _addon(m, day="2026-10-20"):
    from app.addons.models import AddonBooking

    r = m.client.post(f"{vehicle(m)}/addons", json={"date": day, "finish_by": "12:00"},
                      headers=m.customer)
    assert r.status_code == 201, r.text
    return m.db.scalar(select(AddonBooking)), m.db.scalar(select(Payment))


def test_an_add_on_payment_is_due_on_the_service_date_and_stays_due_until_done(money):
    m = money
    booking, row = _addon(m)
    assert (row.kind, row.status, row.due_date.isoformat()) == ("Add-on", "Open", "2026-10-20")
    # Service not done: still Due, even after the service date has passed.
    mark_overdue_and_inactive(at(25, 8), m.db)
    m.db.expire_all()
    assert m.db.scalar(select(Payment)).status == "Open"


def test_a_completed_add_on_with_unreceived_payment_is_over_due_never_inactive(money):
    m = money
    booking, row = _addon(m)
    booking.status = "Completed"
    m.db.commit()
    report = mark_overdue_and_inactive(at(20, 18), m.db)
    m.db.expire_all()
    row = m.db.scalar(select(Payment))
    assert report.marked_overdue == 1 and row.overdue_since is not None
    mark_overdue_and_inactive(at(30, 8), m.db)
    assert m.subscription().status == "Active"


def test_a_completed_add_on_already_received_is_left_alone(money):
    m = money
    booking, row = _addon(m)
    row.status = "Paid"
    booking.status = "Completed"
    m.db.commit()
    assert mark_overdue_and_inactive(at(25, 8), m.db).marked_overdue == 0
    m.db.expire_all()
    assert m.db.scalar(select(Payment)).status == "Paid"


def test_changing_the_add_on_date_moves_the_payment_due_date(money):
    m = money
    booking, row = _addon(m)
    r = m.client.patch(f"/v1/customer/addons/{booking.id}", json={"date": "2026-10-22"},
                       headers=m.customer)
    assert r.status_code == 200, r.text
    m.db.expire_all()
    assert m.db.scalar(select(Payment)).due_date.isoformat() == "2026-10-22"


def test_a_received_payment_is_never_made_over_due(money):
    m = money
    admin_payment(m, cycle_start="2026-10-01", status="Paid")
    report = mark_overdue_and_inactive(at(30, 8), m.db)
    assert report.marked_overdue == 0 and m.subscription().status == "Active"


def test_an_admin_set_over_due_on_an_add_on_is_shown_and_never_inactivates(money):
    m = money
    p = admin_payment(m, kind="Add-on", due_date="2026-10-05", description="Spa")
    assert p["status"] == "Due"
    r = m.client.put(f"/v1/admin/payments/{p['id']}/status", json={"status": "Over due"},
                     headers=m.admin)
    assert r.json()["status"] == "Over due"
    mark_overdue_and_inactive(at(25, 8), m.db)
    assert m.subscription().status == "Active"


def test_the_customer_can_pay_the_current_cycle_any_time(money):
    m = money
    r = m.client.post(f"{vehicle(m)}/payments/next", headers=m.customer)
    assert r.status_code == 200, r.text  # 19 days before the end: no "too early"
    p = r.json()["payment"]
    assert (p["status"], p["due_date"], p["amount_rupees"]) == ("Not Due", "2026-10-30", 1299)
    again = m.client.post(f"{vehicle(m)}/payments/next", headers=m.customer).json()
    assert again["payment"]["id"] == p["id"]


def test_a_pause_does_not_move_the_cycle_or_its_payment(money):
    m = money
    generate_due_payments(at(11), m.db)
    row = m.db.scalar(select(Payment).where(Payment.subscription_id == m.subscription_id))
    assert row.due_date.isoformat() == "2026-10-30"
    r = m.client.post(f"{vehicle(m)}/pauses",
                      json={"from_date": "2026-10-27", "to_date": "2026-10-29"},
                      headers=m.customer)
    assert r.status_code == 201, r.text
    generate_due_payments(at(26, 6), m.db)
    m.db.expire_all()
    assert m.db.scalar(select(Payment).where(
        Payment.subscription_id == m.subscription_id)).due_date.isoformat() == "2026-10-30"


@pytest.fixture
def stalled(monkeypatch):
    """Sign-ins made while this fixture is active get tokens that read 16 minutes old as soon as
    they are issued, as if the machine had stalled for 16 minutes right after signing in."""
    import datetime as dt

    from app.identity import tokens

    real = tokens.utcnow
    monkeypatch.setattr(tokens, "utcnow", lambda: real() - dt.timedelta(minutes=16))


def test_a_sign_in_survives_a_stalled_machine(stalled, money):
    """The nightly dry run of 04-Nov-26 slept 15 minutes inside a test: the 15 minute token expired
    and the pause request got a 401. Tests now sign in with a long-lived token."""
    m = money
    r = m.client.get(f"{vehicle(m)}/payments", headers=m.customer)
    assert r.status_code == 200, r.text


def test_invoice_number_and_the_customers_copy(money):
    m = money
    p = admin_payment(m)
    r = m.client.post(f"/v1/admin/payments/{p['id']}/invoice", headers=m.admin)
    assert r.status_code == 409 and r.json()["code"] == "not_received"
    m.client.post(f"/v1/admin/payments/{p['id']}/confirm", headers=m.admin)
    inv = m.client.post(f"/v1/admin/payments/{p['id']}/invoice", headers=m.admin).json()
    # PRV + month + year + last 4 of the mobile + 4 digits.
    assert inv["number"].startswith("PRV10264321") and len(inv["number"]) == 15
    again = m.client.post(f"/v1/admin/payments/{p['id']}/invoice", headers=m.admin).json()
    assert again["number"] == inv["number"]
    mine = m.client.get(f"/v1/customer/payments/{p['id']}/invoice", headers=m.customer).json()
    assert (mine["number"], mine["gst_included"], mine["customer_name"]) == (
        inv["number"], True, "Meera Rao")
    hist = m.client.get(f"{vehicle(m)}/payments", headers=m.customer).json()
    assert hist[0]["invoice_number"] == inv["number"]


def test_subscription_status_by_the_admin(money):
    m = money
    url = f"/v1/admin/subscriptions/{m.subscription_id}/status"
    r = m.client.put(url, json={"status": "Inactive", "reason": "Left the society"},
                     headers=m.admin)
    assert r.json()["status"] == "Inactive"
    assert m.client.put(url, json={"status": "Active"},
                        headers=m.admin).json()["code"] == "invalid_transition"
    r = m.client.put(url, json={"status": "Activating"}, headers=m.admin)
    assert r.json()["status"] == "Activating"
    r = m.client.put(url, json={"status": "Active", "first_service_date": "2026-11-02"},
                     headers=m.admin)
    assert r.json()["status"] == "Active"
    assert m.subscription().first_service_date.isoformat() == "2026-11-02"


def test_roles_are_enforced_and_unknown_ids_are_not_found(money):
    m = money
    p = admin_payment(m)
    assert m.client.get("/v1/admin/payments", headers=m.customer).status_code == 403
    assert m.client.get(f"/v1/customer/payments/{p['id']}", headers=m.admin).status_code == 403
    assert m.client.get("/v1/customer/payments/not-a-uuid",
                        headers=m.customer).status_code == 404


# ---- the admin's settings are honoured (ADM-SET) -------------------------------------

def test_a_changed_inactive_after_days_is_the_one_used(money):
    m = money
    set_setting(m.db.get_bind(), "billing.inactive_after_days", 2)
    admin_payment(m, cycle_start="2026-10-01")  # last day 30-Oct-26
    mark_overdue_and_inactive(at(31, 1, 0), m.db)  # Over due from 31-Oct-26.
    mark_overdue_and_inactive(at(1, 12, month=11), m.db)
    assert m.subscription().status == "Active"
    report = mark_overdue_and_inactive(at(2, 8, month=11), m.db)
    assert report.inactivated == [m.subscription_id]


def test_a_changed_upi_id_is_shown(money):
    m = money
    set_setting(m.db.get_bind(), "payment.upi_id", "pay@bank")
    r = m.client.post(f"{vehicle(m)}/payments/next", headers=m.customer)
    assert r.status_code == 200, r.text
    pid = r.json()["payment"]["id"]
    detail = m.client.get(f"/v1/customer/payments/{pid}", headers=m.customer).json()
    assert detail["instructions"]["upi_id"] == "pay@bank"


def test_subscription_rows_say_whether_a_plan_payment_is_waiting(money):
    m = money
    row = next(r for r in m.client.get("/v1/admin/subscriptions", headers=m.admin).json()
               if r["vehicle_id"] == m.vehicle_id)
    assert row["payment_due"] is False
    admin_payment(m, kind="Plan", cycle_start="2026-09-01")
    row = next(r for r in m.client.get("/v1/admin/subscriptions", headers=m.admin).json()
               if r["vehicle_id"] == m.vehicle_id)
    assert row["payment_status"] == "Over due" and row["payment_due"] is True


def test_payments_summary_counts_and_adds_up_each_status(money):
    m = money
    admin_payment(m, amount_rupees=1000, cycle_start="2026-10-01")
    admin_payment(m, amount_rupees=500, status="Paid", kind="Add-on", description="Spa",
                  due_date="2026-10-20")
    s = m.client.get("/v1/admin/payments/summary", headers=m.admin).json()
    assert s["by_status"]["Not Due"]["count"] >= 1 and s["by_status"]["Paid"] == {
        "count": 1, "rupees": 500}
    assert s["total"] == sum(v["count"] for v in s["by_status"].values())
    assert s["total_rupees"] == sum(v["rupees"] for v in s["by_status"].values())
    none = m.client.get("/v1/admin/payments/summary", params={"society": "Nowhere"},
                        headers=m.admin).json()
    assert none["total"] == 0
    assert m.client.get("/v1/admin/payments/summary", headers=m.customer).status_code == 403


def test_invoice_numbers_do_not_use_the_random_module():
    import inspect

    from app.billing import service

    assert not hasattr(service, "random")
    assert "secrets.randbelow" in inspect.getsource(service.BillingService.issue_invoice)
