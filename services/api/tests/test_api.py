from datetime import timedelta

import pytest
from sqlalchemy import select

from app.identity.models import AuthEvent, AuthSession, Login
from app.identity.seed import seed_logins
from app.identity.service import role_for
from app.platform.db import utcnow
from tests.conftest import LOGIN_IDS, PASSWORDS


def sign_in(client, role, password=None):
    return client.post("/v1/auth/login", json={
        "login_id": LOGIN_IDS[role],
        "password": PASSWORDS[role] if password is None else password,
    })


def login(client, role):
    r = sign_in(client, role)
    assert r.status_code == 200, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_and_config(client):
    r = client.get("/v1/public/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert "X-Request-ID" in r.headers
    assert "min_app_version" in client.get("/v1/public/config").json()


@pytest.mark.parametrize("role", ["customer", "crew", "admin"])
def test_login_and_home(client, role):
    data = login(client, role)
    assert data["role"] == role
    r = client.get(f"/v1/{role}/home", headers=auth(data["access_token"]))
    assert r.status_code == 200


def test_login_id_decides_the_role():
    assert role_for("someone@example.com") == "customer"
    assert role_for("9000000002") == "crew"
    assert role_for("priveopapa") == "admin"
    assert role_for("900000000") == "admin"  # nine digits is not a mobile number


def test_login_id_ignores_case_and_spaces(client):
    r = client.post("/v1/auth/login", json={
        "login_id": "  PriveoPapa ", "password": PASSWORDS["admin"]})
    assert r.status_code == 200


def test_wrong_password_returns_envelope(client):
    r = sign_in(client, "admin", "nope")
    assert r.status_code == 401
    body = r.json()
    assert body["code"] == "invalid_credentials"
    assert body["message"] and body["request_id"]


def test_unknown_login_looks_like_a_wrong_password(client):
    r = client.post("/v1/auth/login", json={"login_id": "nobody", "password": "x"})
    assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"


def test_only_the_hash_is_stored(client, db):
    row = db.scalar(select(Login).where(Login.login_id == "priveopapa"))
    assert row.password_hash.startswith("$argon2")
    assert PASSWORDS["admin"] not in row.password_hash


@pytest.mark.parametrize("role", ["crew", "admin"])
def test_five_wrong_passwords_lock_crew_and_admin(client, role):
    for _ in range(4):
        assert sign_in(client, role, "wrong").json()["code"] == "invalid_credentials"
    fifth = sign_in(client, role, "wrong")
    assert fifth.status_code == 403 and fifth.json()["code"] == "account_locked"
    # The right password no longer works until the password is reset.
    assert sign_in(client, role).json()["code"] == "account_locked"


def test_seeding_again_unlocks_the_admin(client, db, settings):
    for _ in range(5):
        sign_in(client, "admin", "wrong")
    assert sign_in(client, "admin").status_code == 403
    seed_logins(db, settings)
    assert sign_in(client, "admin").status_code == 200


def test_five_wrong_passwords_block_a_customer_for_15_minutes(client, db):
    for _ in range(4):
        sign_in(client, "customer", "wrong")
    fifth = sign_in(client, "customer", "wrong")
    assert fifth.status_code == 429 and fifth.json()["code"] == "too_many_attempts"
    assert sign_in(client, "customer").status_code == 429

    row = db.scalar(select(Login).where(Login.role == "customer"))
    assert timedelta(minutes=14) < row.blocked_until - utcnow() <= timedelta(minutes=15)
    row.blocked_until = utcnow() - timedelta(seconds=1)
    db.commit()
    assert sign_in(client, "customer").status_code == 200


def test_a_right_password_clears_the_wrong_count(client):
    for _ in range(4):
        sign_in(client, "crew", "wrong")
    assert sign_in(client, "crew").status_code == 200
    for _ in range(4):
        assert sign_in(client, "crew", "wrong").json()["code"] == "invalid_credentials"


def test_an_inactive_login_cannot_sign_in(client, db):
    data = login(client, "crew")
    row = db.scalar(select(Login).where(Login.role == "crew"))
    row.active = False
    db.commit()
    assert sign_in(client, "crew").status_code == 401
    # The session it already had ends at once (CRW-ACC-11).
    assert client.get("/v1/crew/home", headers=auth(data["access_token"])).status_code == 401


def test_role_is_enforced(client):
    token = login(client, "customer")["access_token"]
    assert client.get("/v1/admin/home", headers=auth(token)).status_code == 403
    assert client.get("/v1/crew/home").status_code == 401


def test_refresh_gives_new_tokens_and_the_old_one_stops(client):
    data = login(client, "crew")
    r = client.post("/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != data["refresh_token"]
    assert client.get("/v1/crew/home", headers=auth(new["access_token"])).status_code == 200
    again = client.post("/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert again.status_code == 401
    # A refresh token must not work as an access token.
    assert client.get("/v1/crew/home", headers=auth(new["refresh_token"])).status_code == 401


def test_logout_ends_the_session_at_once(client):
    data = login(client, "customer")
    headers = auth(data["access_token"])
    assert client.post("/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/v1/customer/home", headers=headers).status_code == 401
    r = client.post("/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 401


def test_logout_without_a_token_still_succeeds(client):
    assert client.post("/v1/auth/logout").status_code == 204
    assert client.post("/v1/auth/logout", headers=auth("junk")).status_code == 204


def test_admin_signs_out_of_all_devices(client, db):
    phone = login(client, "admin")
    tablet = login(client, "admin")
    crew = login(client, "crew")
    r = client.post("/v1/admin/sessions/logout-all", headers=auth(phone["access_token"]))
    assert r.status_code == 204
    for device in (phone, tablet):
        assert client.get("/v1/admin/home",
                          headers=auth(device["access_token"])).status_code == 401
    # Other people stay signed in, and the action is recorded with its time.
    assert client.get("/v1/crew/home", headers=auth(crew["access_token"])).status_code == 200
    event = db.scalar(select(AuthEvent).where(AuthEvent.kind == "logout_all"))
    assert event is not None and event.at is not None


def test_only_an_admin_can_sign_out_of_all_devices(client):
    token = login(client, "crew")["access_token"]
    assert client.post("/v1/admin/sessions/logout-all",
                       headers=auth(token)).status_code == 403


def test_admin_phone_signs_out_after_24_idle_hours(client, db):
    admin = login(client, "admin")
    crew = login(client, "crew")
    for session in db.scalars(select(AuthSession)):
        session.last_used_at = utcnow() - timedelta(hours=25)
    db.commit()
    assert client.get("/v1/admin/home", headers=auth(admin["access_token"])).status_code == 401
    r = client.post("/v1/auth/refresh", json={"refresh_token": admin["refresh_token"]})
    assert r.status_code == 401
    # Crew and customers have no idle time-out (CRW-ACC-11, AUTH-17).
    assert client.get("/v1/crew/home", headers=auth(crew["access_token"])).status_code == 200


def test_demo_logins_are_not_seeded_unless_asked(monkeypatch, db, settings):
    monkeypatch.setenv("SEED_DEMO_LOGINS", "false")
    from app.platform.config import get_settings
    get_settings.cache_clear()
    done = seed_logins(db, get_settings())
    assert list(done) == ["priveopapa"]
    assert db.scalar(select(Login).where(Login.role == "crew")) is None


def test_crew_home_has_no_customer_details(client):
    token = login(client, "crew")["access_token"]
    text = client.get("/v1/crew/home", headers=auth(token)).text.lower()
    assert "customer" not in text and "mobile" not in text and "phone" not in text


def test_validation_error_envelope(client):
    r = client.post("/v1/auth/login", json={})
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
