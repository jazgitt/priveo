# ruff: noqa: F811
"""Alternate names, the wider customer search, and creating a customer without
an email (owner decisions, 3 Nov 2026)."""
import uuid

from sqlalchemy import select

from app.customers.models import Customer
from app.directory.models import DirectoryAudit
from app.identity.models import Login
from tests.test_api import auth, login
from tests.test_customer_administration import directory, upload, vehicle_body  # noqa: F401

ZONES = "/v1/admin/directory"


def _admin(client):
    return auth(login(client, "admin")["access_token"])


def _create(client, directory, admin, registration="HR01ZZ1234", **person):
    car = {**vehicle_body(directory, upload(client, admin)), "registration": registration}
    body = {"first_name": "Asha", "last_name": "Rao", "mobile": "9876543300",
            "vehicle": car, **person}
    return client.post("/v1/admin/customers", headers=admin, json=body)


def test_create_customer_without_an_email_has_no_sign_in(client, directory, db):
    admin = _admin(client)
    made = _create(client, directory, admin)
    assert made.status_code == 201, made.text
    out = made.json()
    assert out["email"] is None and out["welcome_sent"] is False
    customer = db.get(Customer, uuid.UUID(out["id"]))
    assert customer.login_id is None
    assert db.scalar(select(Login).where(Login.display_name == "Asha Rao")) is None
    blank = _create(client, directory, admin, registration="HR01ZZ5678", email="  ",
                   mobile="9876543301")
    assert blank.status_code == 201 and blank.json()["email"] is None


def test_alternate_names_are_shown_edited_and_not_audited(client, directory, db):
    admin = _admin(client)
    made = _create(client, directory, admin, email="alt@example.com").json()
    assert made["alternate_names"] is None
    edit = {"first_name": "Asha", "last_name": "Rao", "mobile": "9876543300",
            "alternate_names": "  Mrs  Rao,  A. Rao "}
    saved = client.patch(f"/v1/admin/customers/{made['id']}", headers=admin, json=edit)
    assert saved.status_code == 200, saved.text
    assert saved.json()["alternate_names"] == "Mrs Rao, A. Rao"
    # Left out of the request: it stays.
    del edit["alternate_names"]
    kept = client.patch(f"/v1/admin/customers/{made['id']}", headers=admin, json=edit)
    assert kept.json()["alternate_names"] == "Mrs Rao, A. Rao"
    cleared = client.patch(f"/v1/admin/customers/{made['id']}", headers=admin,
                           json={**edit, "alternate_names": ""})
    assert cleared.json()["alternate_names"] is None
    client.patch(f"/v1/admin/customers/{made['id']}", headers=admin,
                 json={**edit, "alternate_names": "Secret Name"})
    logged = " ".join(str(a.detail) for a in db.scalars(select(DirectoryAudit)))
    assert "Secret Name" not in logged and "Mrs Rao" not in logged


def test_search_matches_alternate_names_parking_and_zone(client, directory, db):
    admin, society = _admin(client), directory[0]
    zone = client.post(f"{ZONES}/societies/{society.id}/zones", headers=admin,
                       json={"name": "Tower North"}).json()
    body = vehicle_body(directory, upload(client, admin))
    body["zone_id"] = zone["id"]
    body["parking_number"] = "77"
    made = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Asha", "last_name": "Rao", "email": "find@example.com",
        "mobile": "9876543302", "vehicle": body}).json()
    client.patch(f"/v1/admin/customers/{made['id']}", headers=admin, json={
        "first_name": "Asha", "last_name": "Rao", "mobile": "9876543302",
        "alternate_names": "Pinky Memsaab"})
    for q in ("memsaab", "Tower North", "77"):
        found = client.get("/v1/admin/customers", headers=admin, params={"q": q})
        assert found.status_code == 200, found.text
        assert [c["id"] for c in found.json()] == [made["id"]], q
    assert client.get("/v1/admin/customers", headers=admin,
                      params={"q": "nobody-here"}).json() == []
