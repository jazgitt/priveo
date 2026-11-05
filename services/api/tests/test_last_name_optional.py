# ruff: noqa: F811
"""The last name is optional everywhere (ADM-CUS-01, ADM-CUS-24, ONB-02, ACC-06;
owner decision of 5 Nov 2026). A name that is typed must still be letters."""
import uuid

from app.customers.models import Customer
from app.identity.models import Login
from tests.test_api import auth, login
from tests.test_customer_administration import directory, upload, vehicle_body  # noqa: F401


def _create(client, directory, admin, registration, **person):
    car = {**vehicle_body(directory, upload(client, admin)), "registration": registration}
    body = {"first_name": "Asha", "mobile": "9876543400", "vehicle": car, **person}
    return client.post("/v1/admin/customers", headers=admin, json=body)


def test_adm_cus_01_create_without_a_last_name(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    missing = _create(client, directory, admin, "HR01LN0001")
    assert missing.status_code == 201, missing.text
    assert missing.json()["last_name"] == ""
    customer = db.get(Customer, uuid.UUID(missing.json()["id"]))
    # No trailing space in the sign-in display name.
    assert db.get(Login, customer.login_id).display_name == "Asha"
    blank = _create(client, directory, admin, "HR01LN0002", mobile="9876543401", last_name="  ")
    assert blank.status_code == 201 and blank.json()["last_name"] == ""
    listed = client.get("/v1/admin/customers?q=Asha", headers=admin).json()
    assert {row["name"] for row in listed} == {"Asha"}


def test_adm_cus_01_a_typed_last_name_must_still_be_letters(client, directory):
    admin = auth(login(client, "admin")["access_token"])
    bad = _create(client, directory, admin, "HR01LN0003", last_name="R4o")
    assert bad.status_code == 422 and set(bad.json()["fields"]) == {"last_name"}
    short = _create(client, directory, admin, "HR01LN0004", mobile="98765")
    assert short.status_code == 422 and set(short.json()["fields"]) == {"mobile"}


def test_adm_cus_24_edit_clears_the_last_name(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    made = _create(client, directory, admin, "HR01LN0005", last_name="Rao").json()
    edit = {"first_name": "Asha", "last_name": "", "mobile": "9876543400"}
    saved = client.patch(f"/v1/admin/customers/{made['id']}", headers=admin, json=edit)
    assert saved.status_code == 200, saved.text
    assert saved.json()["last_name"] == ""
    customer = db.get(Customer, uuid.UUID(made["id"]))
    assert db.get(Login, customer.login_id).display_name == "Asha"
    bad = client.patch(f"/v1/admin/customers/{made['id']}", headers=admin,
                       json={**edit, "last_name": "R4o"})
    assert bad.status_code == 422
