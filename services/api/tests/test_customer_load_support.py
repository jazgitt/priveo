# ruff: noqa: F811
"""What the customer load needs from the rest of the API: zones, a customer with
no email, and the Custom interior day."""
import uuid

from sqlalchemy import select

from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import DirectoryAudit
from tests.test_api import auth, login
from tests.test_customer_administration import directory, upload, vehicle_body  # noqa: F401

ZONES = "/v1/admin/directory"


def _admin(client):
    return auth(login(client, "admin")["access_token"])


def test_admin_manages_zones_of_a_society(client, directory, db):
    admin, society = _admin(client), directory[0]
    made = client.post(f"{ZONES}/societies/{society.id}/zones", headers=admin,
                       json={"name": "  Zone  1 "})
    assert made.status_code == 201, made.text
    zone = made.json()
    assert zone["name"] == "Zone 1" and zone["active"] and zone["vehicles"] == 0
    again = client.post(f"{ZONES}/societies/{society.id}/zones", headers=admin,
                        json={"name": "zone 1"})
    assert again.status_code == 409
    renamed = client.patch(f"{ZONES}/zones/{zone['id']}", headers=admin, json={"name": "Zone A"})
    assert renamed.json()["name"] == "Zone A"
    off = client.post(f"{ZONES}/zones/{zone['id']}/deactivate", headers=admin).json()
    assert off["active"] is False
    listed = client.get(f"{ZONES}/societies/{society.id}/zones?include_inactive=false",
                        headers=admin)
    assert listed.json() == []
    client.post(f"{ZONES}/zones/{zone['id']}/reactivate", headers=admin)
    assert len(client.get(f"{ZONES}/societies/{society.id}/zones", headers=admin).json()) == 1
    actions = {a.action for a in db.scalars(select(DirectoryAudit).where(
        DirectoryAudit.entity == "zone"))}
    assert actions == {"create", "update"}
    assert client.get(f"{ZONES}/societies/{uuid.uuid4()}/zones", headers=admin).status_code == 404


def test_zone_is_set_in_add_vehicle_and_can_be_changed(client, directory, db):
    admin, society = _admin(client), directory[0]
    zone = client.post(f"{ZONES}/societies/{society.id}/zones", headers=admin,
                       json={"name": "Zone 2"}).json()
    body = vehicle_body(directory, upload(client, admin))
    body["zone_id"] = zone["id"]
    made = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Zed", "last_name": "Rao", "email": "zed@example.com",
        "mobile": "9876543200", "vehicle": body})
    assert made.status_code == 201, made.text
    car = made.json()["vehicles"][0]
    assert car["zone_id"] == zone["id"] and car["zone"] == "Zone 2"
    assert client.get(f"{ZONES}/societies/{society.id}/zones",
                      headers=admin).json()[0]["vehicles"] == 1

    cleared = client.patch(f"/v1/admin/vehicles/{car['id']}", headers=admin,
                           json={"clear_zone": True})
    assert cleared.status_code == 200 and cleared.json()["zone"] is None
    other = client.post(f"{ZONES}/societies/{society.id}/zones", headers=admin,
                        json={"name": "Zone 3"}).json()
    client.post(f"{ZONES}/zones/{other['id']}/deactivate", headers=admin)
    refused = client.patch(f"/v1/admin/vehicles/{car['id']}", headers=admin,
                           json={"zone_id": other["id"]})
    assert refused.status_code == 422


def test_zone_of_another_society_is_refused(client, directory, db):
    from app.directory.models import Society
    admin = _admin(client)
    elsewhere = Society(name="Elsewhere")
    db.add(elsewhere)
    db.commit()
    zone = client.post(f"{ZONES}/societies/{elsewhere.id}/zones", headers=admin,
                       json={"name": "Z"}).json()
    body = vehicle_body(directory, upload(client, admin))
    body["zone_id"] = zone["id"]
    refused = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Zed", "last_name": "Rao", "email": "zed2@example.com",
        "mobile": "9876543201", "vehicle": body})
    assert refused.status_code == 422


def _loaded_without_email(db, directory):
    society = directory[0]
    customer = Customer(login_id=None, email=None, first_name="No", last_name="Email",
                        mobile="9000000111", society_id=society.id, source="migration",
                        alternate_names="Someone")
    db.add(customer)
    db.flush()
    db.add(Vehicle(customer_id=customer.id, society_id=society.id, model="Nexon",
                   registration="T0926HR9225CH", parking_number="Under D25"))
    db.commit()
    return customer


def test_a_customer_with_no_email_shows_in_the_portal(client, directory, db):
    admin, customer = _admin(client), _loaded_without_email(db, directory)
    one = client.get(f"/v1/admin/customers/{customer.id}", headers=admin)
    assert one.status_code == 200, one.text
    assert one.json()["email"] is None and one.json()["password_set"] is False
    listed = client.get("/v1/admin/customers?q=email", headers=admin)
    assert listed.status_code == 200
    assert any(r["id"] == str(customer.id) and r["email"] is None for r in listed.json())
    assert client.get("/v1/admin/customers", headers=admin).status_code == 200
    assert client.get(f"/v1/admin/customers/{customer.id}/sessions", headers=admin).json() == []
    assert client.post(f"/v1/admin/customers/{customer.id}/reset-password",
                       headers=admin).status_code == 200
    assert client.patch(f"/v1/admin/customers/{customer.id}", headers=admin, json={
        "first_name": "No", "last_name": "Email", "mobile": "9000000111", "flat": "A-1",
        "address_line1": "", "address_line2": ""}).status_code == 200
    prefs = client.get(f"/v1/admin/customers/{customer.id}/notification-preferences",
                       headers=admin)
    assert prefs.status_code == 409 and prefs.json()["code"] == "no_sign_in"


def test_adding_an_email_later_gives_the_customer_a_sign_in(client, directory, db):
    admin, customer = _admin(client), _loaded_without_email(db, directory)
    done = client.patch(f"/v1/admin/customers/{customer.id}/email", headers=admin,
                        json={"email": "later@example.com"})
    assert done.status_code == 200, done.text
    db.expire_all()
    fresh = db.get(Customer, customer.id)
    assert fresh.email == "later@example.com" and fresh.login_id is not None


def test_custom_interior_day_is_stored_with_its_notes(client, directory, db):
    admin = _admin(client)
    body = vehicle_body(directory, upload(client, admin))
    body.update(interior_day="Custom", interior_day_notes="Car A on odd weeks")
    made = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Cus", "last_name": "Tom", "email": "cus@example.com",
        "mobile": "9876543202", "vehicle": body})
    assert made.status_code == 201, made.text
    sub = made.json()["vehicles"][0]["subscription"]
    assert sub["interior_day"] == "Custom" and sub["interior_day_notes"] == "Car A on odd weeks"

    changed = client.patch(f"/v1/admin/subscriptions/{sub['id']}", headers=admin,
                           json={"interior_day": "Friday"})
    assert changed.status_code == 200, changed.text
    row = db.scalar(select(Subscription).where(Subscription.id == uuid.UUID(sub["id"])))
    db.refresh(row)
    assert row.interior_day == "Friday" and row.interior_day_notes is None
    back = client.patch(f"/v1/admin/subscriptions/{sub['id']}", headers=admin,
                        json={"interior_day": "Custom", "interior_day_notes": "Swap each week"})
    assert back.status_code == 200
    db.refresh(row)
    assert row.interior_day == "Custom" and row.interior_day_notes == "Swap each week"
    bad = client.patch(f"/v1/admin/subscriptions/{sub['id']}", headers=admin,
                       json={"interior_day": "Someday"})
    assert bad.status_code == 422


def test_admin_sets_up_the_subscription_of_a_vehicle_that_has_none(client, directory, db):
    admin, plan = _admin(client), directory[1]
    customer = _loaded_without_email(db, directory)
    car = db.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id))
    url = f"/v1/admin/vehicles/{car.id}/subscription"
    body = {"plan_id": str(plan.id), "cutoff_time": "09:00", "interior_day": "Sunday",
            "first_service_date": "2026-11-01", "first_payment_status": "Due"}

    assert client.post(url, headers=admin, json={**body, "cutoff_time": "09:10"}).status_code == 422
    assert client.post(url, headers=admin, json={**body, "interior_day": None}).status_code == 422
    made = client.post(url, headers=admin, json=body)
    assert made.status_code == 201, made.text
    sub = made.json()["subscription"]
    assert sub["status"] == "Activating" and sub["price_rupees"] == plan.monthly_price_rupees
    assert sub["interior_day"] == "Sunday" and sub["first_service_date"] == "2026-11-01"
    assert made.json()["payments"][0]["status"] == "Due"
    assert made.json()["payments"][0]["due_date"] == "2026-11-01"

    again = client.post(url, headers=admin, json=body)
    assert again.status_code == 409 and again.json()["code"] == "subscription_exists"
    assert client.post(f"/v1/admin/vehicles/{uuid.uuid4()}/subscription", headers=admin,
                       json=body).status_code == 404
    assert db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id)) is not None


def test_set_up_subscription_accepts_a_custom_interior_day(client, directory, db):
    admin, plan = _admin(client), directory[1]
    customer = _loaded_without_email(db, directory)
    car = db.scalar(select(Vehicle).where(Vehicle.customer_id == customer.id))
    made = client.post(f"/v1/admin/vehicles/{car.id}/subscription", headers=admin, json={
        "plan_id": str(plan.id), "cutoff_time": "08:30", "interior_day": "Custom",
        "interior_day_notes": "This car on odd weeks"})
    assert made.status_code == 201, made.text
    sub = made.json()["subscription"]
    assert (sub["interior_day"], sub["interior_day_notes"]) == ("Custom", "This car on odd weeks")
