import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.billing.config import MoneySettings
from app.billing.models import Payment
from app.billing.service import BillingService
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Plan, Society, VehicleCatalogueEntry
from app.media.store import LocalObjectStore, get_object_store
from app.platform.clock import today_ist
from tests.test_api import auth, login


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
    assert client.get("/v1/admin/customers?q=asha%20rao", headers=admin).status_code == 200


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
