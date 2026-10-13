"""Deep Spa requests (ADD-01 to ADD-10, ADD-15)."""
from sqlalchemy import select

from app.billing.models import Payment
from tests.changes.money_fixtures import at


def vehicle(m):
    return f"/v1/customer/vehicles/{m.vehicle_id}"


def request(m, **kw):
    body = {"service": "Deep Spa", "date": "2026-10-20", "finish_by": "12:30", **kw}
    return m.client.post(f"{vehicle(m)}/addons", json=body, headers=m.customer)


def test_the_screen_lists_the_offer_and_earlier_requests(money):
    r = money.client.get("/v1/customer/addons", headers=money.customer).json()
    assert [(o["service"], o["duration_minutes"]) for o in r["offers"]] == [("Deep Spa", 120)]
    assert r["requests"] == []


def test_a_subscriber_requests_deep_spa_and_gets_a_payment(money):
    m = money
    r = request(m)
    assert r.status_code == 201, r.text
    a = r.json()
    assert (a["status"], a["date"], a["finish_by"], a["payment_status"], a["can_change"]) == (
        "Requested", "2026-10-20", "12:30", "Due", True)
    pay = m.db.scalar(select(Payment))
    assert (pay.kind, pay.amount_rupees, str(pay.id)) == (
        "Add-on", a["price_rupees"], a["payment_id"])
    # It uses the same UPI screen and the same "I've paid" step (ADD-05).
    r = m.client.post(f"/v1/customer/payments/{a['payment_id']}/paid", headers=m.customer)
    assert r.json()["payment"]["status"] == "Initiated"
    mine = m.client.get("/v1/customer/addons", headers=m.customer).json()["requests"]
    assert mine[0]["payment_status"] == "Initiated"


def test_the_date_must_be_before_its_9pm_cutoff(money):
    m = money
    m.clock.now = at(11, 21, 0)
    r = request(m, date="2026-10-12")
    assert r.status_code == 409 and r.json()["code"] == "after_cutoff"
    m.clock.now = at(11, 20, 59)
    assert request(m, date="2026-10-12").status_code == 201


def test_finish_by_is_in_half_hour_steps_and_the_service_is_offered(money):
    assert request(money, finish_by="12:15").status_code == 422
    assert request(money, service="Wax").status_code == 422


def test_only_a_vehicle_with_an_active_subscription_can_buy_an_add_on(money):
    m = money
    for vehicle_id in (m.add_vehicle(subscribed=True, status="Activating"),
                       m.add_vehicle(subscribed=False)):
        r = m.client.post(f"/v1/customer/vehicles/{vehicle_id}/addons",
                          json={"date": "2026-10-20", "finish_by": "12:00"},
                          headers=m.customer)
        assert r.status_code == 409 and r.json()["code"] == "subscription_not_active"


def test_a_retry_with_the_same_key_is_one_request(money):
    m = money
    h = {**m.customer, "Idempotency-Key": "addon-1"}
    body = {"date": "2026-10-20", "finish_by": "12:00"}
    a = m.client.post(f"{vehicle(m)}/addons", json=body, headers=h).json()
    b = m.client.post(f"{vehicle(m)}/addons", json=body, headers=h).json()
    assert a["id"] == b["id"]
    assert len(m.db.scalars(select(Payment)).all()) == 1


def test_change_and_cancel_follow_the_9pm_rule_and_a_cancelled_add_on_is_not_charged(money):
    m = money
    a = request(m).json()
    r = m.client.patch(f"/v1/customer/addons/{a['id']}",
                       json={"date": "2026-10-22", "finish_by": "14:00"}, headers=m.customer)
    assert (r.json()["date"], r.json()["finish_by"]) == ("2026-10-22", "14:00")

    m.clock.now = at(21, 21, 0)
    r = m.client.patch(f"/v1/customer/addons/{a['id']}", json={"finish_by": "10:00"},
                       headers=m.customer)
    assert r.status_code == 409 and r.json()["code"] == "after_cutoff"
    assert m.client.delete(f"/v1/customer/addons/{a['id']}",
                           headers=m.customer).status_code == 409

    m.clock.now = at(15, 10)
    r = m.client.delete(f"/v1/customer/addons/{a['id']}", headers=m.customer)
    assert r.json()["status"] == "Cancelled" and r.json()["payment_status"] is None
    assert m.db.scalar(select(Payment)).voided_at is not None
    assert m.client.get(f"{vehicle(m)}/payments", headers=m.customer).json() == []


def test_standalone_deep_spa_uses_the_same_spa_payment(money):
    m = money
    none = m.add_vehicle(subscribed=False)
    r = m.client.post("/v1/customer/addons/standalone",
                      json={"vehicle_id": none, "date": "2026-10-20", "finish_by": "13:00",
                            "notes": "Call after 6 PM"}, headers=m.customer)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["standalone"] and a["status"] == "Requested"
    pay = m.db.scalar(select(Payment))
    assert str(pay.id) == a["payment_id"] and pay.kind == "Add-on"
    assert pay.amount_rupees == a["price_rupees"] and a["payment_status"] == "Due"
    listed = m.client.get("/v1/admin/addons?standalone=true", headers=m.admin).json()
    assert (listed[0]["contact_mobile"], listed[0]["notes"], listed[0]["customer_name"]) == (
        "9000004321", "Call after 6 PM", "Meera Rao")
    # A vehicle with an active subscription uses the add-on route instead.
    r = m.client.post("/v1/customer/addons/standalone",
                      json={"vehicle_id": m.vehicle_id, "date": "2026-10-20",
                            "finish_by": "13:00"}, headers=m.customer)
    assert r.json()["code"] == "has_subscription"


def test_the_admin_lists_and_updates_requests_without_the_9pm_rule(money):
    m = money
    a = request(m, date="2026-10-12").json()
    m.clock.now = at(11, 22)
    r = m.client.patch(f"/v1/admin/addons/{a['id']}",
                       json={"date": "2026-10-13", "status": "Requested"}, headers=m.admin)
    assert (r.json()["date"], r.json()["status"], r.json()["vehicle"]) == (
        "2026-10-13", "Requested", "Hyundai Creta HR 26 DK 8337")
    assert [x["id"] for x in m.client.get("/v1/admin/addons?status=Requested",
                                         headers=m.admin).json()] == [a["id"]]
    r = m.client.patch(f"/v1/admin/addons/{a['id']}", json={"status": "Nope"},
                       headers=m.admin)
    assert r.status_code == 422
    assert m.client.get("/v1/admin/addons", headers=m.customer).status_code == 403


def test_a_changed_add_on_price_is_the_one_offered(money):
    from app.directory.models import AddonCatalogueItem
    from app.directory.seed import seed_defaults
    seed_defaults(money.db)
    row = money.db.scalar(
        select(AddonCatalogueItem).where(AddonCatalogueItem.service == "Deep Spa"))
    row.price_rupees = 1777
    money.db.commit()
    offers = money.client.get("/v1/customer/addons", headers=money.customer).json()["offers"]
    assert offers[0]["price_rupees"] == 1777
    assert request(money).json()["price_rupees"] == 1777
