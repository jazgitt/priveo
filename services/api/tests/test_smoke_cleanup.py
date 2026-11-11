# ruff: noqa: F811
"""The deployment smoke test makes its own customer and crew and removes them (9-Nov-26 decision).
The removal route exists only in the test environment and only for the smoke-test number range."""
import types

from sqlalchemy import func, select

from app.customers.models import Customer, Vehicle
from app.identity.models import Login
from app.testing import smoke_cleanup
from scripts import smoke_test
from tests.conftest import PASSWORDS
from tests.test_api import auth, login
from tests.test_customer_administration import directory  # noqa: F401


def _environment(monkeypatch, name):
    monkeypatch.setattr(smoke_cleanup, "get_settings", lambda: types.SimpleNamespace(environment=name))


def _customer(client, directory, admin, mobile, registration):
    society, plan, car = directory
    vehicle = {"society_id": str(society.id), "plan_id": str(plan.id), "catalogue_id": str(car.id),
               "registration": registration, "parking_basement": "B2", "parking_number": "99",
               "cutoff_time": "09:00", "interior_day": "Monday"}
    made = client.post("/v1/admin/customers", headers=admin, json={
        "first_name": "Smoke", "last_name": "Customer", "mobile": mobile, "flat": "SMOKE",
        "vehicle": vehicle})
    assert made.status_code == 201, made.text
    return made.json()


def test_cleanup_is_not_found_outside_the_test_environment(client, monkeypatch, directory):
    admin = auth(login(client, "admin")["access_token"])
    _customer(client, directory, admin, "9000099111", "HR99SM0111")
    _environment(monkeypatch, "prod")
    gone = client.delete("/v1/admin/test-users/9000099111", headers=admin)
    assert gone.status_code == 404


def test_cleanup_refuses_a_login_outside_the_smoke_range(client, monkeypatch, directory):
    admin = auth(login(client, "admin")["access_token"])
    _environment(monkeypatch, "test")
    assert client.delete("/v1/admin/test-users/testadminid", headers=admin).status_code == 422
    assert client.delete("/v1/admin/test-users/9876543210", headers=admin).status_code == 422


def test_cleanup_removes_the_customer_and_its_rows_and_nothing_else(client, monkeypatch, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    _customer(client, directory, admin, "9000099222", "HR99SM0222")
    kept = _customer(client, directory, admin, "9876543220", "HR01ZZ2220")
    _environment(monkeypatch, "test")
    assert client.delete("/v1/admin/test-users/9000099222", headers=admin).status_code == 204
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Login)
                     .where(Login.login_id == "9000099222")) == 0
    assert db.scalar(select(func.count()).select_from(Customer)
                     .where(Customer.mobile == "9000099222")) == 0
    assert db.scalar(select(func.count()).select_from(Vehicle)
                     .where(Vehicle.registration == "HR99SM0222")) == 0
    # The other customer is untouched.
    assert db.scalar(select(func.count()).select_from(Login)
                     .where(Login.login_id == "9876543220")) == 1
    assert db.scalar(select(func.count()).select_from(Vehicle)
                     .where(Vehicle.registration == "HR01ZZ2220")) == 1
    assert kept["mobile"] == "9876543220"


def test_smoke_makes_its_own_customer_and_crew_and_removes_them(client, monkeypatch, directory,
                                                                db, capsys):
    _environment(monkeypatch, "test")
    monkeypatch.setattr(smoke_test.sys, "argv", ["smoke_test.py", "https://test.invalid"])
    monkeypatch.setenv("SMOKE_CREATE_USERS", "true")
    monkeypatch.setenv("SMOKE_ADMIN_PASSWORD", PASSWORDS["admin"])
    deleted = []

    def call(base, path, body=None, token=None, method=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        if method == "DELETE":
            deleted.append(path)
            response = client.delete(path, headers=headers)
        elif body is not None:
            response = client.post(path, json=body, headers=headers)
        else:
            response = client.get(path, headers=headers)
        return response.status_code, (response.json() if response.content else {})

    monkeypatch.setattr(smoke_test, "call", call)
    smoke_test.main()
    out = capsys.readouterr().out
    assert "ok   entry data customer" in out
    assert "ok   entry data crew" in out
    assert "ok   entry data admin" in out
    assert len(deleted) == 2
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Login)
                     .where(Login.login_id.like("9000099%"))) == 0
