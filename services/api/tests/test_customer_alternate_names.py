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


def test_parking_number_is_free_text_and_basement_is_optional_with_a_zone(client, directory, db):
    admin, society = _admin(client), directory[0]
    zone = client.post(f"{ZONES}/societies/{society.id}/zones", headers=admin,
                       json={"name": "Zone 9"}).json()
    car = {**vehicle_body(directory, upload(client, admin)), "registration": "HR01ZZ4321",
           "parking_basement": "", "parking_number": "Under D25"}
    # No zone and no basement: refused. With a zone: allowed.
    refused = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Pia", "last_name": "Rao", "mobile": "9876543310", "vehicle": car})
    assert refused.status_code == 422
    made = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Pia", "last_name": "Rao", "mobile": "9876543310",
        "vehicle": {**car, "zone_id": zone["id"]}})
    assert made.status_code == 201, made.text
    vehicle = made.json()["vehicles"][0]
    assert vehicle["parking_number"] == "Under D25" and vehicle["parking_basement"] == ""
    # Edit: free text again, and a 61-character entry is refused.
    ok = client.patch(f"/v1/admin/vehicles/{vehicle['id']}", headers=admin,
                      json={"parking_number": "Near   Tesla"})
    assert ok.status_code == 200 and ok.json()["parking_number"] == "Near Tesla"
    long = client.patch(f"/v1/admin/vehicles/{vehicle['id']}", headers=admin,
                        json={"parking_number": "y" * 61})
    assert long.status_code == 422
    # The zone cannot be removed while the vehicle has no basement.
    stuck = client.patch(f"/v1/admin/vehicles/{vehicle['id']}", headers=admin,
                         json={"clear_zone": True})
    assert stuck.status_code == 422
    # Editing something else on a vehicle with no basement is not blocked.
    other = client.patch(f"/v1/admin/vehicles/{vehicle['id']}", headers=admin, json={"active": True})
    assert other.status_code == 200
