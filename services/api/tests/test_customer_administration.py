import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.billing.config import MoneySettings
from app.billing.models import Payment
from app.billing.service import BillingService
from app.customers.models import AddonRequest, Customer, Subscription, Vehicle
from app.directory.models import Plan, Society, VehicleCatalogueEntry
from app.media.store import LocalObjectStore, get_object_store
from app.platform.clock import today_ist
from tests.test_api import auth, login


def test_admin_creates_standalone_customer_without_plan_or_payment(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    car = vehicle_body(directory, upload(client, admin))
    car.update(plan_id=None, cutoff_time=None, interior_day=None)
    response = client.post('/v1/admin/customers', headers=admin, json={
        'first_name': 'Spa', 'last_name': 'Customer', 'email': 'spa@example.com',
        'mobile': '9876543211', 'vehicle': car})
    assert response.status_code == 201, response.text
    vehicle = response.json()['vehicles'][0]
    assert vehicle['subscription'] is None and vehicle['payments'] == []
    assert db.scalar(select(Subscription).where(Subscription.vehicle_id == uuid.UUID(vehicle['id']))) is None
    assert db.scalar(select(Payment).where(Payment.vehicle_id == uuid.UUID(vehicle['id']))) is None


@pytest.fixture
def directory(db, client, tmp_path):
    society = Society(name="Second society")
    plan = Plan(
        name="Premium test",
        monthly_price_rupees=999,
        includes_interior=True,
        inclusions=["Daily exterior", "Weekly interior"],
        list_price_rupees=1499,
    )
    car = VehicleCatalogueEntry(make="Tata", model="Nexon", variant="Pure", category="Compact SUV")
    db.add_all([society, plan, car])
    db.commit()
    client.app.dependency_overrides[get_object_store] = lambda: LocalObjectStore(
        root=tmp_path / "media", secret="test-secret"
    )
    return society, plan, car


def upload(client, headers, purpose="vehicle", admin=True):
    prefix = "/v1/admin/customer-uploads" if admin else "/v1/customer/uploads"
    r = client.post(
        prefix,
        headers=headers,
        json={"purpose": purpose, "content_type": "image/jpeg", "size_bytes": 5},
    )
    assert r.status_code == 201, r.text
    ticket = r.json()
    assert client.put(ticket["upload_url"], content=b"photo").status_code == 204
    assert client.post(f"{prefix}/{ticket['id']}/confirm", headers=headers).status_code == 200
    return ticket["id"]


def vehicle_body(directory, photo):
    society, plan, car = directory
    return {
        "society_id": str(society.id),
        "plan_id": str(plan.id),
        "catalogue_id": str(car.id),
        "registration": "HR01ZZ1234",
        "parking_basement": "B2",
        "parking_number": "17",
        "cutoff_time": "09:00",
        "interior_day": "Monday",
        "photo_upload_id": photo,
    }


def create(client, directory, admin):
    body = {
        "first_name": "Asha",
        "last_name": "Rao",
        "email": "asha@example.com",
        "mobile": "9876543210",
        "flat": "A-12",
        "vehicle": vehicle_body(directory, upload(client, admin)),
    }
    r = client.post("/v1/admin/customers", headers=admin, json=body)
    assert r.status_code == 201, r.text
    return r.json(), body


def test_onboard_without_import_and_duplicate_email_opens_existing(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    c, body = create(client, directory, admin)
    assert c["welcome_sent"] and not c["password_set"] and not c["onboarding_confirmed"]
    v = c["vehicles"][0]
    assert v["subscription"]["status"] == "Activating" and v["payments"][0]["status"] == "Due"
    assert v["photo_url"] and v["society"] == "Second society"
    repeat = client.post("/v1/admin/customers", headers=admin, json=body).json()
    assert repeat["existing"] and repeat["id"] == c["id"]
    assert len(list(db.scalars(select(Customer).where(Customer.email == body["email"])))) == 1
    listed = client.get("/v1/admin/customers?q=asha%20rao", headers=admin)
    assert listed.status_code == 200
    row = next(r for r in listed.json() if r["id"] == c["id"])
    assert row["flat"] == "A-12" and not row["password_set"] and not row["email_verified"]
    assert row["vehicles"] == [{"id": v["id"], "registration": v["registration"],
                                "status": "Activating"}]


def test_customer_adds_vehicle_in_another_society_and_cannot_confirm_payment(client, directory, db):
    customer = auth(login(client, "customer")["access_token"])
    body = vehicle_body(directory, upload(client, customer, admin=False))
    rejected = client.post(
        "/v1/customer/vehicles", headers=customer, json={**body, "first_payment_status": "Received"}
    )
    assert rejected.status_code == 422
    r = client.post("/v1/customer/vehicles", headers=customer, json=body)
    assert r.status_code == 201, r.text
    v = r.json()
    read = client.get(f"/v1/customer/vehicles/{v['id']}", headers=customer).json()
    assert read["society"] == "Second society" and read["photo_url"]
    home = client.get("/v1/customer/home", headers=customer).json()
    assert len({card["society"] for card in home["vehicles"]}) == 2
    assert db.get(Vehicle, uuid.UUID(v["id"])).society_id == directory[0].id
    assert (
        client.patch(
            f"/v1/customer/vehicles/{v['id']}",
            headers=customer,
            json={"parking_basement": "B3", "parking_number": "9"},
        ).status_code
        == 200
    )


def test_customer_cannot_use_an_admins_upload(client, directory):
    admin = auth(login(client, "admin")["access_token"])
    customer = auth(login(client, "customer")["access_token"])
    body = vehicle_body(directory, upload(client, admin))
    assert client.post("/v1/customer/vehicles", headers=customer, json=body).status_code == 422
    assert client.post("/v1/admin/customers", headers=customer, json={}).status_code == 403


def test_email_correction_invalidates_sessions_and_pending_codes(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    old = login(client, "customer")
    c = db.scalar(select(Customer).where(Customer.email == "customer@priveo.test"))
    r = client.patch(
        f"/v1/admin/customers/{c.id}/email", headers=admin, json={"email": "corrected@example.com"}
    )
    assert r.status_code == 200 and r.json()["welcome_sent"]
    assert client.get("/v1/customer/home", headers=auth(old["access_token"])).status_code == 401
    assert (
        client.post("/v1/auth/start", json={"login_id": "corrected@example.com"}).status_code == 200
    )
    assert (
        client.post(
            "/v1/auth/login", json={"login_id": "corrected@example.com", "password": "pw-customer1"}
        ).status_code
        == 401
    )


def test_plan_change_waits_for_renewal_and_society_is_immutable(client, directory, db):
    from app.notifications.models import Notification
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)
    sub = db.scalar(
        select(Subscription).where(
            Subscription.id == uuid.UUID(c["vehicles"][0]["subscription"]["id"])
        )
    )
    next_plan = Plan(name="Exterior test", monthly_price_rupees=699, includes_interior=False)
    db.add(next_plan)
    db.commit()
    r = client.patch(
        f"/v1/admin/subscriptions/{sub.id}", headers=admin, json={"plan_id": str(next_plan.id)}
    )
    assert r.status_code == 200, r.text
    assert client.patch(f"/v1/admin/subscriptions/{sub.id}", headers=admin,
                        json={"cutoff_time": "08:30"}).status_code == 200
    customer_login_id = db.get(Customer, uuid.UUID(c["id"])).login_id
    assert db.scalar(select(Notification).where(Notification.login_id == customer_login_id)) is None
    db.refresh(sub)
    assert sub.monthly_price_rupees == 999 and sub.pending_plan_id == next_plan.id
    assert sub.pending_from >= today_ist() + timedelta(days=1)
    vid = c["vehicles"][0]["id"]
    assert (
        client.patch(
            f"/v1/admin/vehicles/{vid}", headers=admin, json={"society_id": str(directory[0].id)}
        ).status_code
        == 422
    )


def test_activation_anchors_first_payment_and_pending_plan_applies_at_renewal(
    client, directory, db
):
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)
    sub = db.get(Subscription, uuid.UUID(c["vehicles"][0]["subscription"]["id"]))
    start = today_ist() + timedelta(days=3)
    activated = client.put(
        f"/v1/admin/subscriptions/{sub.id}/status",
        headers=admin,
        json={"status": "Active", "first_service_date": start.isoformat()},
    )
    assert activated.status_code == 200, activated.text
    first = db.scalar(select(Payment).where(Payment.subscription_id == sub.id))
    assert first.cycle_start == start and first.due_date == start
    assert first.cycle_end == start + timedelta(days=30)
    first.status = "Received"
    next_plan = Plan(name="Exterior renewal", monthly_price_rupees=699, includes_interior=False)
    db.add(next_plan)
    db.commit()
    changed = client.patch(
        f"/v1/admin/subscriptions/{sub.id}",
        headers=admin,
        json={"plan_id": str(next_plan.id)},
    )
    assert changed.status_code == 200, changed.text
    db.refresh(sub)
    renewal = sub.pending_from
    before = datetime.combine(renewal - timedelta(days=7), datetime.min.time(), tzinfo=UTC)
    BillingService(db, lambda: before, MoneySettings()).generate_due_payments(before)
    db.refresh(sub)
    assert sub.monthly_price_rupees == 999
    due = db.scalar(
        select(Payment).where(Payment.subscription_id == sub.id, Payment.cycle_start == renewal)
    )
    assert due.amount_rupees == 699
    effective = datetime.combine(renewal, datetime.min.time(), tzinfo=UTC)
    BillingService(db, lambda: effective, MoneySettings()).generate_due_payments(effective)
    db.refresh(sub)
    assert sub.plan_id == next_plan.id and sub.monthly_price_rupees == 699
    assert sub.pending_plan_id is None and sub.interior_day is None


def test_customer_list_filters_by_status_and_summary_counts_them(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)  # a new customer: subscription Activating
    spa = vehicle_body(directory, upload(client, admin))
    spa.update(registration="HR01SP0001", plan_id=None, cutoff_time=None, interior_day=None)
    spa_customer = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Spa", "last_name": "Only", "email": "spaonly@example.com",
        "mobile": "9876543212", "vehicle": spa}).json()
    db.add(AddonRequest(customer_id=uuid.UUID(spa_customer["id"]), service="Deep Spa"))
    db.commit()

    def ids(query):
        r = client.get(f"/v1/admin/customers?{query}", headers=admin)
        assert r.status_code == 200, r.text
        return {row["id"] for row in r.json()}

    assert c["id"] in ids("status=Activating")
    assert c["id"] not in ids("status=No%20subscription")
    assert spa_customer["id"] in ids("status=No%20subscription")
    assert spa_customer["id"] not in ids("status=Activating")
    assert client.get("/v1/admin/customers?status=Nope", headers=admin).status_code == 422

    summary = client.get("/v1/admin/customers/summary", headers=admin).json()
    assert summary["total"] == sum(summary["by_status"].values())
    no_sub = summary["by_status"]["No subscription"]
    assert summary["with_subscription"] == summary["total"] - no_sub
    assert summary["by_status"]["Activating"] >= 1 and summary["addons_only"] == 1
    narrowed = client.get("/v1/admin/customers/summary?q=spaonly", headers=admin).json()
    assert narrowed == {"total": 1, "with_subscription": 0, "addons_only": 1,
                        "by_status": {"Active": 0, "Activating": 0, "Inactive": 0,
                                      "No subscription": 1}}
    assert client.get("/v1/admin/customers/summary", headers=auth(
        login(client, "customer")["access_token"])).status_code == 403


def test_admin_deactivates_and_reactivates_a_vehicle(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)
    v = c["vehicles"][0]
    blocked = client.patch(f"/v1/admin/vehicles/{v['id']}", headers=admin, json={"active": False})
    assert blocked.status_code == 422  # the subscription is still Activating
    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == uuid.UUID(v["id"])))
    sub.status = "Inactive"
    db.commit()
    off = client.patch(f"/v1/admin/vehicles/{v['id']}", headers=admin, json={"active": False})
    assert off.status_code == 200 and off.json()["active"] is False
    detail = client.get(f"/v1/admin/customers/{c['id']}", headers=admin).json()
    assert [x["active"] for x in detail["vehicles"]] == [False]
    row = next(r for r in client.get("/v1/admin/customers?q=asha", headers=admin).json()
               if r["id"] == c["id"])
    assert row["vehicles"] == []  # the list shows live vehicles only
    on = client.patch(f"/v1/admin/vehicles/{v['id']}", headers=admin, json={"active": True})
    assert on.status_code == 200 and on.json()["active"] is True


def test_admin_adds_a_vehicle_without_a_photo_but_the_customer_cannot(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)
    car = vehicle_body(directory, None)
    car.pop("photo_upload_id")
    car["registration"] = "HR02NP0002"
    r = client.post(f"/v1/admin/customers/{c['id']}/vehicles", headers=admin, json=car)
    assert r.status_code == 201, r.text
    assert r.json()["photo_url"] is None
    customer = auth(login(client, "customer")["access_token"])
    car["registration"] = "HR02NP0003"
    assert client.post("/v1/customer/vehicles", headers=customer, json=car).status_code == 422


def test_admin_edits_address_lines_and_society(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)
    assert c["address_line1"] == "" and c["society_id"] == str(directory[0].id)
    other = Society(name="Third society")
    db.add(other)
    db.commit()
    body = {"first_name": "Asha", "last_name": "Rao", "mobile": "9876543210", "flat": "A-12",
            "address_line1": " Tower 4 ", "address_line2": "Sector 9", "society_id": str(other.id)}
    r = client.patch(f"/v1/admin/customers/{c['id']}", headers=admin, json=body)
    assert r.status_code == 200, r.text
    assert r.json()["address_line1"] == "Tower 4" and r.json()["society_id"] == str(other.id)
    body["society_id"] = str(uuid.uuid4())
    patch = client.patch(f"/v1/admin/customers/{c['id']}", headers=admin, json=body)
    assert patch.status_code == 422
    body.pop("society_id")
    kept = client.patch(f"/v1/admin/customers/{c['id']}", headers=admin, json=body).json()
    assert kept["society_id"] == str(other.id)  # left out means unchanged


def test_summary_counts_follow_the_society(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)
    path = "/v1/admin/customers/summary?society_id="
    here = client.get(path + str(directory[0].id), headers=admin).json()
    elsewhere = client.get(path + str(uuid.uuid4()), headers=admin).json()
    assert here["by_status"]["Activating"] == 1 and elsewhere["total"] == 0


def test_customer_list_filters_by_scope(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)
    spa = vehicle_body(directory, upload(client, admin))
    spa.update(registration="HR01SP0009", plan_id=None, cutoff_time=None, interior_day=None)
    spa_customer = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Spa", "last_name": "Scope", "email": "spascope@example.com",
        "mobile": "9876543213", "vehicle": spa}).json()
    db.add(AddonRequest(customer_id=uuid.UUID(spa_customer["id"]), service="Deep Spa"))
    db.commit()

    def ids(query):
        r = client.get(f"/v1/admin/customers?{query}", headers=admin)
        assert r.status_code == 200, r.text
        return {row["id"] for row in r.json()}

    assert c["id"] in ids("scope=with_subscription")
    assert spa_customer["id"] not in ids("scope=with_subscription")
    assert ids("scope=addons_only") == {spa_customer["id"]}
    assert client.get("/v1/admin/customers?scope=bad", headers=admin).status_code == 422
