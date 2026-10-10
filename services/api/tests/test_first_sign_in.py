"""A customer's first sign-in and forgotten password: an emailed code, then a
password (AUTH-03 to AUTH-08, AUTH-12, AUTH-15, AUTH-16)."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.customers.models import Customer
from app.directory.models import Society
from app.identity.models import AuthEvent, EmailCode, Login
from app.platform.config import get_settings
from app.platform.db import utcnow
from tests.conftest import LOGIN_IDS, PASSWORDS
from tests.test_api import auth, login

EMAIL = "asha@example.com"
CODE = "246810"
NEW_PASSWORD = "carwash2026"


@pytest.fixture
def customer(client, db):
    """A customer the admin created, who has never signed in."""
    row = Login(role="customer", login_id=EMAIL, display_name="Asha Rao")
    society = Society(name="Green Meadows", sector="Sector 1")
    db.add_all([row, society])
    db.flush()
    db.add(Customer(login_id=row.id, first_name="Asha", last_name="Rao", email=EMAIL,
                    mobile="9000000101", society_id=society.id))
    db.commit()
    return row


def start(client, login_id=EMAIL):
    return client.post("/v1/auth/start", json={"login_id": login_id})


def verify(client, code=CODE, email=EMAIL):
    return client.post("/v1/auth/code/verify", json={"email": email, "code": code})


def set_password(client, token, password=NEW_PASSWORD):
    return client.post("/v1/auth/password",
                       json={"password_token": token, "password": password})


def age_codes(db, **by):
    for row in db.scalars(select(EmailCode)):
        row.created_at -= timedelta(**by)
    db.commit()


def test_first_sign_in_from_code_to_home(client, db, customer):
    r = start(client, "  Asha@Example.com ")
    assert r.status_code == 200 and r.json() == {"next": "code", "resend_in_seconds": 30}

    token = verify(client).json()["password_token"]
    r = set_password(client, token)
    assert r.status_code == 200 and r.json()["role"] == "customer"
    assert client.get("/v1/customer/home",
                      headers=auth(r.json()["access_token"])).status_code == 200

    # The terms are recorded at the first sign-in (AUTH-04), and from now on
    # the customer is asked for the password.
    assert db.scalar(select(Customer)).terms_accepted_at is not None
    assert start(client).json() == {"next": "password", "resend_in_seconds": 0}
    r = client.post("/v1/auth/login", json={"login_id": EMAIL, "password": NEW_PASSWORD})
    assert r.status_code == 200
    kinds = set(db.scalars(select(AuthEvent.kind)))
    assert {"code_sent", "code_verified", "password_set"} <= kinds


def test_only_hashes_are_stored(client, db, customer):
    start(client)
    token = verify(client).json()["password_token"]
    row = db.scalar(select(EmailCode))
    assert CODE not in row.code_hash and len(row.code_hash) == 64
    assert row.password_token_hash != token
    set_password(client, token)
    db.refresh(customer)
    assert customer.password_hash.startswith("$argon2")


def test_crew_and_admin_are_asked_for_the_password(client):
    for login_id in (LOGIN_IDS["crew"], LOGIN_IDS["admin"], "nobody", "9111111111"):
        assert start(client, login_id).json() == {"next": "password", "resend_in_seconds": 0}


def test_an_email_the_admin_has_not_created_gets_no_code(client, db):
    for call in (start(client, "stranger@example.com"),
                 client.post("/v1/auth/code", json={"email": "stranger@example.com"}),
                 verify(client, email="stranger@example.com")):
        assert call.status_code == 404 and call.json()["code"] == "email_not_registered"
    assert db.scalar(select(EmailCode)) is None


def test_an_inactive_customer_gets_no_code(client, db, customer):
    customer.active = False
    db.commit()
    assert start(client).json()["code"] == "email_not_registered"


def test_a_wrong_code_and_then_the_right_one(client, customer):
    start(client)
    r = verify(client, "000000")
    assert r.status_code == 400 and r.json()["code"] == "invalid_code"
    assert verify(client).status_code == 200


def test_five_wrong_codes_cancel_the_code(client, db, customer):
    start(client)
    for _ in range(4):
        assert verify(client, "000000").json()["code"] == "invalid_code"
    assert verify(client, "000000").json()["code"] == "code_ended"
    # The right code no longer works. A new one does.
    assert verify(client).json()["code"] == "code_ended"
    age_codes(db, seconds=31)
    assert client.post("/v1/auth/code", json={"email": EMAIL}).status_code == 200
    assert verify(client).status_code == 200


def test_a_code_expires_after_10_minutes(client, db, customer):
    start(client)
    row = db.scalar(select(EmailCode))
    assert timedelta(minutes=9) < row.expires_at - utcnow() <= timedelta(minutes=10)
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    r = verify(client)
    assert r.status_code == 400 and r.json()["code"] == "code_ended"


def test_asking_again_within_30_seconds_sends_nothing_new(client, db, customer):
    start(client)
    again = client.post("/v1/auth/code", json={"email": EMAIL}).json()
    assert 0 < again["resend_in_seconds"] <= 30
    assert len(db.scalars(select(EmailCode)).all()) == 1

    age_codes(db, seconds=31)
    assert client.post("/v1/auth/code", json={"email": EMAIL}).json() == {
        "resend_in_seconds": 30}
    rows = db.scalars(select(EmailCode).order_by(EmailCode.created_at)).all()
    assert [r.ended_reason for r in rows] == ["replaced", None]


def test_at_most_five_codes_in_an_hour(client, db, customer):
    for _ in range(5):
        assert client.post("/v1/auth/code", json={"email": EMAIL}).status_code == 200
        age_codes(db, minutes=1)
    r = client.post("/v1/auth/code", json={"email": EMAIL})
    assert r.status_code == 429 and r.json()["code"] == "too_many_codes"
    age_codes(db, hours=1)
    assert client.post("/v1/auth/code", json={"email": EMAIL}).status_code == 200


@pytest.mark.parametrize("password", ["short1", "nodigitshere", "12345678"])
def test_a_weak_password_is_refused_and_can_be_tried_again(client, customer, password):
    start(client)
    token = verify(client).json()["password_token"]
    r = set_password(client, token, password)
    assert r.status_code == 422 and r.json()["code"] == "weak_password"
    assert r.json()["fields"]["password"]
    assert set_password(client, token).status_code == 200


def test_the_password_token_works_once_and_for_10_minutes(client, db, customer):
    start(client)
    token = verify(client).json()["password_token"]
    assert set_password(client, token).status_code == 200
    assert set_password(client, token, "another2026").json()["code"] == "code_ended"
    assert set_password(client, "made-up").json()["code"] == "code_ended"

    age_codes(db, seconds=31)
    client.post("/v1/auth/code", json={"email": EMAIL})
    token = verify(client).json()["password_token"]
    row = db.scalar(select(EmailCode).where(EmailCode.ended_at.is_(None)))
    row.password_token_expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert set_password(client, token).json()["code"] == "code_ended"


def test_forgot_password_replaces_the_password_and_signs_out_other_phones(client, db):
    old = login(client, "customer")
    email = LOGIN_IDS["customer"]
    assert client.post("/v1/auth/code", json={"email": email}).status_code == 200
    token = verify(client, email=email).json()["password_token"]
    new = set_password(client, token).json()

    assert client.get("/v1/customer/home",
                      headers=auth(old["access_token"])).status_code == 401
    assert client.get("/v1/customer/home",
                      headers=auth(new["access_token"])).status_code == 200
    r = client.post("/v1/auth/login",
                    json={"login_id": email, "password": PASSWORDS["customer"]})
    assert r.status_code == 401
    assert db.scalar(select(AuthEvent).where(AuthEvent.kind == "password_reset")) is not None


def test_a_reset_lifts_the_15_minute_block(client):
    email = LOGIN_IDS["customer"]
    for _ in range(5):
        client.post("/v1/auth/login", json={"login_id": email, "password": "wrong"})
    client.post("/v1/auth/code", json={"email": email})
    token = verify(client, email=email).json()["password_token"]
    assert set_password(client, token).status_code == 200
    r = client.post("/v1/auth/login", json={"login_id": email, "password": NEW_PASSWORD})
    assert r.status_code == 200


def test_crew_cannot_get_a_code(client):
    r = client.post("/v1/auth/code", json={"email": LOGIN_IDS["crew"]})
    assert r.status_code == 404


@pytest.mark.parametrize("env", [{"MOCK_EMAIL_CODE": ""}, {"MOCK_EMAIL_CODE": "12345"},
                                 {"ENVIRONMENT": "prod"}])
def test_without_a_fixed_code_no_code_is_made(client, db, customer, monkeypatch, env):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    r = start(client)
    assert r.status_code == 503 and r.json()["code"] == "not_configured"
    assert db.scalar(select(EmailCode)) is None
