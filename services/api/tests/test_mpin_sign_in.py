"""A customer signs in with the mobile number and an MPIN. The first MPIN is the
last 6 digits of the number and must be changed at once; a customer who forgot
the MPIN gets an emailed code (AUTH-03, AUTH-11 to AUTH-16, AUTH-19, AUTH-20)."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.customers.logins import ensure_login
from app.customers.models import Customer
from app.directory.models import Society
from app.identity.models import AuthEvent, EmailCode, Login
from app.identity.service import hash_password
from app.platform.config import get_settings
from app.platform.db import utcnow
from tests.conftest import LOGIN_IDS, PASSWORDS
from tests.test_api import auth, login

EMAIL = "asha@example.com"
MOBILE = "9000000101"
FIRST_MPIN = "000101"  # the last 6 digits of the mobile number
CODE = "246810"
NEW_MPIN = "482915"


@pytest.fixture
def customer(client, db):
    """A customer the admin created, who has never signed in."""
    society = Society(name="Green Meadows", sector="Sector 1")
    db.add(society)
    db.flush()
    row = Customer(first_name="Asha", last_name="Rao", email=EMAIL, mobile=MOBILE,
                   society_id=society.id)
    db.add(row)
    db.flush()
    ensure_login(db, row)
    db.commit()
    return row


def sign_in(client, mpin=FIRST_MPIN, mobile=MOBILE, role="customer"):
    body = {"login_id": mobile, "password": mpin}
    if role:
        body["role"] = role
    return client.post("/v1/auth/login", json=body)


def change(client, token, current=FIRST_MPIN, new=NEW_MPIN):
    return client.post("/v1/customer/mpin", headers=auth(token),
                       json={"current_mpin": current, "new_mpin": new})


def ask_code(client, mobile=MOBILE):
    return client.post("/v1/auth/code", json={"mobile": mobile})


def verify(client, code=CODE, mobile=MOBILE):
    return client.post("/v1/auth/code/verify", json={"mobile": mobile, "code": code})


def set_mpin(client, token, mpin=NEW_MPIN):
    return client.post("/v1/auth/mpin", json={"mpin_token": token, "mpin": mpin})


def age_codes(db, **by):
    for row in db.scalars(select(EmailCode)):
        row.created_at -= timedelta(**by)
    db.commit()


# --- The first MPIN ---


def test_the_first_mpin_is_the_last_six_digits_and_must_be_changed(client, db, customer):
    r = sign_in(client)
    assert r.status_code == 200 and r.json()["role"] == "customer"
    assert r.json()["must_change_mpin"] is True
    token = r.json()["access_token"]

    # Nothing else works until the MPIN is changed.
    for path in ("/v1/customer/home", "/v1/customer/onboarding", "/v1/customer/profile"):
        blocked = client.get(path, headers=auth(token))
        assert blocked.status_code == 403 and blocked.json()["code"] == "mpin_change_required"

    assert change(client, token).status_code == 204
    assert client.get("/v1/customer/home", headers=auth(token)).status_code == 200

    # From now on the new MPIN works, the first one does not, and nothing is asked again.
    assert sign_in(client, FIRST_MPIN).status_code == 401
    again = sign_in(client, NEW_MPIN)
    assert again.status_code == 200 and again.json()["must_change_mpin"] is False
    # The terms are recorded at the first sign-in (AUTH-04).
    db.expire_all()
    assert db.scalar(select(Customer)).terms_accepted_at is not None


@pytest.mark.parametrize("mpin", ["12345", "1234567", "abcdef", "12 456", ""])
def test_a_new_mpin_is_exactly_six_digits(client, customer, mpin):
    token = sign_in(client).json()["access_token"]
    r = change(client, token, new=mpin)
    assert r.status_code == 422 and r.json()["code"] == "weak_mpin"
    assert r.json()["fields"]["new_mpin"]


def test_the_new_mpin_cannot_be_the_first_one_or_the_current_one(client, customer):
    token = sign_in(client).json()["access_token"]
    first = change(client, token, new=FIRST_MPIN)
    assert first.status_code == 422 and first.json()["code"] == "weak_mpin"
    assert change(client, token).status_code == 204
    same = change(client, token, current=NEW_MPIN, new=NEW_MPIN)
    assert same.status_code == 422 and same.json()["code"] == "weak_mpin"


def test_the_current_mpin_must_be_right_to_change_it(client, customer):
    token = sign_in(client).json()["access_token"]
    r = change(client, token, current="111111")
    assert r.status_code == 422 and r.json()["code"] == "invalid_credentials"
    assert r.json()["fields"]["current_mpin"]


def test_changing_the_mpin_signs_out_the_other_phones(client, customer):
    first = sign_in(client).json()["access_token"]
    assert change(client, first).status_code == 204
    one = sign_in(client, NEW_MPIN).json()["access_token"]
    two = sign_in(client, NEW_MPIN).json()["access_token"]
    assert change(client, one, current=NEW_MPIN, new="135790").status_code == 204
    assert client.get("/v1/customer/home", headers=auth(two)).status_code == 401
    assert client.get("/v1/customer/home", headers=auth(one)).status_code == 200


def test_only_the_hash_of_the_mpin_is_stored(client, db, customer):
    row = db.scalar(select(Login).where(Login.login_id == MOBILE, Login.role == "customer"))
    assert row.password_hash.startswith("$argon2") and FIRST_MPIN not in row.password_hash
    assert row.must_change_mpin is True


# --- Which sign-in is meant ---


def test_the_same_mobile_can_be_a_customer_and_a_crew_member(client, db, customer):
    db.add(Login(role="crew", login_id=MOBILE, display_name="Asha Crew",
                 password_hash=hash_password("Crew1234$")))
    db.commit()
    as_customer = sign_in(client)
    as_crew = sign_in(client, "Crew1234$", role="crew")
    assert as_customer.json()["role"] == "customer" and as_crew.json()["role"] == "crew"
    # Each has its own secret: the other's does not open it.
    assert sign_in(client, "Crew1234$", role="customer").status_code == 401
    assert sign_in(client, FIRST_MPIN, role="crew").status_code == 401


def test_a_sign_in_without_a_role_is_refused_with_a_clear_message(client, customer):
    for login_id, password in ((MOBILE, FIRST_MPIN), (LOGIN_IDS["crew"], PASSWORDS["crew"]),
                               (LOGIN_IDS["admin"], PASSWORDS["admin"])):
        r = client.post("/v1/auth/login", json={"login_id": login_id, "password": password})
        assert r.status_code == 422 and r.json()["code"] == "role_required"
        assert "Update the Priveo app" in r.json()["message"]
    blank = client.post("/v1/auth/login", json={
        "login_id": MOBILE, "password": FIRST_MPIN, "role": " "})
    assert blank.json()["code"] == "role_required"
    unknown = sign_in(client, role="boss")
    assert unknown.status_code == 401 and unknown.json()["code"] == "invalid_credentials"
    for who, role in (("crew", "crew"), ("admin", "admin")):
        ok = client.post("/v1/auth/login", json={
            "login_id": LOGIN_IDS[who], "password": PASSWORDS[who], "role": role})
        assert ok.status_code == 200 and ok.json()["role"] == role


def test_a_wrong_mpin_looks_the_same_as_an_unknown_number(client, customer):
    wrong = sign_in(client, "999999")
    unknown = sign_in(client, FIRST_MPIN, mobile="9111111111")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["code"] == unknown.json()["code"] == "invalid_credentials"
    assert "MPIN" in wrong.json()["message"] and "password" not in wrong.json()["message"]


def test_five_wrong_mpins_block_a_customer_for_15_minutes(client, db, customer):
    for _ in range(4):
        assert sign_in(client, "999999").json()["code"] == "invalid_credentials"
    fifth = sign_in(client, "999999")
    assert fifth.status_code == 429 and "15 minutes" in fifth.json()["message"]
    assert sign_in(client).json()["code"] == "too_many_attempts"
    row = db.scalar(select(Login).where(Login.login_id == MOBILE, Login.role == "customer"))
    row.blocked_until = utcnow() - timedelta(seconds=1)
    db.commit()
    assert sign_in(client).status_code == 200


# --- Forgot MPIN ---


def test_forgot_mpin_replaces_it_and_signs_out_other_phones(client, db, customer):
    old = sign_in(client).json()["access_token"]
    assert change(client, old).status_code == 204
    assert ask_code(client).status_code == 200
    token = verify(client).json()["mpin_token"]
    new = set_mpin(client, token, "135790").json()
    assert new["role"] == "customer" and new["must_change_mpin"] is False

    assert client.get("/v1/customer/home", headers=auth(old)).status_code == 401
    assert client.get("/v1/customer/home", headers=auth(new["access_token"])).status_code == 200
    assert sign_in(client, NEW_MPIN).status_code == 401
    assert sign_in(client, "135790").status_code == 200
    assert db.scalar(select(AuthEvent).where(AuthEvent.kind == "mpin_reset")) is not None


def test_a_reset_lifts_the_15_minute_block(client, customer):
    for _ in range(5):
        sign_in(client, "999999")
    ask_code(client)
    assert set_mpin(client, verify(client).json()["mpin_token"]).status_code == 200
    assert sign_in(client, NEW_MPIN).status_code == 200


@pytest.mark.parametrize("mpin", ["12345", "1234567", "abcdef", FIRST_MPIN])
def test_a_weak_mpin_is_refused_and_can_be_tried_again(client, customer, mpin):
    ask_code(client)
    token = verify(client).json()["mpin_token"]
    r = set_mpin(client, token, mpin)
    assert r.status_code == 422 and r.json()["code"] == "weak_mpin"
    assert r.json()["fields"]["mpin"]
    assert set_mpin(client, token).status_code == 200


def test_the_mpin_token_works_once_and_for_10_minutes(client, db, customer):
    ask_code(client)
    token = verify(client).json()["mpin_token"]
    assert set_mpin(client, token).status_code == 200
    assert set_mpin(client, token, "135790").json()["code"] == "code_ended"
    assert set_mpin(client, "made-up").json()["code"] == "code_ended"

    age_codes(db, seconds=31)
    ask_code(client)
    token = verify(client).json()["mpin_token"]
    row = db.scalar(select(EmailCode).where(EmailCode.ended_at.is_(None)))
    row.password_token_expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert set_mpin(client, token).json()["code"] == "code_ended"


def test_a_number_the_admin_has_not_created_gets_no_code(client, db):
    """R-11: the answer is the same as for a known number, and nothing is sent or stored."""
    assert ask_code(client, "9111111111").status_code == 200
    assert verify(client, mobile="9111111111").status_code == 400
    assert db.scalar(select(EmailCode)) is None


def test_unknown_and_known_numbers_get_the_same_answers(client, db, customer):
    known, unknown = ask_code(client), ask_code(client, "9111111111")
    assert known.status_code == unknown.status_code == 200
    assert known.json().keys() == unknown.json().keys()
    assert db.scalar(select(EmailCode)) is not None  # the code went to the known number
    wrong_known = verify(client, code="000000")
    wrong_unknown = verify(client, code="000000", mobile="9111111111")
    assert wrong_known.status_code == wrong_unknown.status_code == 400
    assert wrong_known.json() == wrong_unknown.json()


def test_an_inactive_customer_gets_no_code(client, db, customer):
    db.scalar(select(Login).where(Login.login_id == MOBILE, Login.role == "customer")
              ).active = False
    db.commit()
    assert ask_code(client).status_code == 200
    assert db.scalar(select(EmailCode)) is None


def test_a_customer_with_no_email_is_told_to_ask_priveo(client, db, customer):
    customer.email = None
    db.commit()
    r = ask_code(client)
    assert r.status_code == 409 and r.json()["code"] == "no_email"
    assert "reset your MPIN" in r.json()["message"]
    assert db.scalar(select(EmailCode)) is None


def test_crew_cannot_get_a_code(client):
    assert ask_code(client, LOGIN_IDS["crew"]).status_code == 404


def test_a_wrong_code_and_then_the_right_one(client, customer):
    ask_code(client)
    r = verify(client, "000000")
    assert r.status_code == 400 and r.json()["code"] == "invalid_code"
    assert verify(client).status_code == 200


def test_five_wrong_codes_cancel_the_code(client, db, customer):
    ask_code(client)
    for _ in range(4):
        assert verify(client, "000000").json()["code"] == "invalid_code"
    assert verify(client, "000000").json()["code"] == "code_ended"
    # The right code no longer works. A new one does.
    assert verify(client).json()["code"] == "code_ended"
    age_codes(db, seconds=31)
    assert ask_code(client).status_code == 200
    assert verify(client).status_code == 200


def test_a_code_expires_after_30_minutes(client, db, customer):
    ask_code(client)
    row = db.scalar(select(EmailCode))
    assert timedelta(minutes=29) < row.expires_at - utcnow() <= timedelta(minutes=30)
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    r = verify(client)
    assert r.status_code == 400 and r.json()["code"] == "code_ended"


def test_asking_again_within_30_seconds_sends_nothing_new(client, db, customer):
    assert ask_code(client).json()["resend_in_seconds"] == 30
    again = ask_code(client).json()
    assert 0 < again["resend_in_seconds"] <= 30
    assert len(db.scalars(select(EmailCode)).all()) == 1

    age_codes(db, seconds=31)
    assert ask_code(client).json() == {"resend_in_seconds": 30}
    rows = db.scalars(select(EmailCode).order_by(EmailCode.created_at)).all()
    assert [r.ended_reason for r in rows] == ["replaced", None]


def test_at_most_five_codes_in_an_hour(client, db, customer):
    for _ in range(5):
        assert ask_code(client).status_code == 200
        age_codes(db, minutes=1)
    r = ask_code(client)
    assert r.status_code == 429 and r.json()["code"] == "too_many_codes"
    age_codes(db, hours=1)
    assert ask_code(client).status_code == 200


@pytest.fixture
def sent():
    from app.platform.email import _fake
    _fake.sent.clear()
    return _fake.sent


def test_the_code_goes_to_the_email_on_file_and_is_not_in_the_welcome(client, customer, sent):
    ask_code(client)
    assert [(m.to, m.purpose, m.code) for m in sent] == [(EMAIL, "mpin_reset_code", CODE)]


@pytest.mark.parametrize("env", [{"MOCK_EMAIL_CODE": ""}, {"MOCK_EMAIL_CODE": "12345"}])
def test_without_a_fixed_code_a_random_one_is_sent(client, db, customer, monkeypatch, sent, env):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    assert ask_code(client).status_code == 200
    code = sent[0].code
    assert len(code) == 6 and code.isdigit()
    assert verify(client, code).status_code == 200


def test_in_prod_without_resend_no_code_is_made(client, db, customer, monkeypatch, sent):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    get_settings.cache_clear()
    r = ask_code(client)
    assert r.status_code == 503 and r.json()["code"] == "not_configured"
    assert db.scalar(select(EmailCode)) is None and not sent


def test_a_failed_send_stores_nothing(client, db, customer, monkeypatch):
    from app.platform import email as mail

    def boom(self, to, code, purpose):
        raise mail.EmailSendError("down")

    monkeypatch.setattr(mail.FakeEmailSender, "send_code", boom)
    r = ask_code(client)
    assert r.status_code == 502 and r.json()["code"] == "email_failed"
    assert db.scalar(select(EmailCode)) is None


def test_the_old_email_flow_is_gone(client, customer):
    assert client.post("/v1/auth/start", json={"login_id": MOBILE}).status_code in (404, 405)
    assert client.post("/v1/auth/password", json={"password_token": "x", "password": "y"}
                       ).status_code in (404, 405)


def test_the_support_contact_needs_no_sign_in(client):
    r = client.get("/v1/auth/support-contact")
    assert r.status_code == 200 and set(r.json()) == {"helpline", "whatsapp", "hours"}


def test_the_admin_ends_a_customers_sessions(client, db):
    old = login(client, "customer")
    admin = login(client, "admin")
    cid = db.scalar(select(Customer.id).where(Customer.mobile == LOGIN_IDS["customer"]))
    assert cid is not None
    r = client.post(f"/v1/admin/customers/{cid}/sessions/logout",
                    headers=auth(admin["access_token"]))
    assert r.status_code == 200 and r.json()["ended"] >= 1
    assert client.get("/v1/customer/home",
                      headers=auth(old["access_token"])).status_code == 401
