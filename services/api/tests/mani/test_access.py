"""Founder-only access (D6): the role is admin AND the login is the bound one."""
import pytest
from sqlalchemy import select

from app.identity.models import Login
from app.identity.service import hash_password
from app.mani.config import get_mani_settings
from app.platform.db import utcnow
from tests.test_api import auth, login

STATUS = "/v1/admin/mani/status"


@pytest.fixture(autouse=True)
def fresh_settings():
    get_mani_settings.cache_clear()
    yield
    get_mani_settings.cache_clear()


def add_admin(db, login_id="otheradmin", password="pw-other-admin1", active=True):
    db.add(Login(role="admin", login_id=login_id, display_name="Other Admin",
                 password_hash=hash_password(password), password_changed_at=utcnow(), active=active))
    db.commit()
    return password


def sign_in_as(client, login_id, password):
    r = client.post("/v1/auth/login", json={"login_id": login_id, "password": password})
    assert r.status_code == 200, r.text
    return auth(r.json()["access_token"])


def test_the_founder_login_can_open_mani(client):
    r = client.get(STATUS, headers=auth(login(client, "admin")["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["founder"] is True and body["backend"] == "local"
    assert "key" not in str(body).lower()


def test_an_anonymous_request_is_refused(client):
    assert client.get(STATUS).status_code == 401


@pytest.mark.parametrize("role", ["customer", "crew"])
def test_other_roles_are_refused(client, role):
    assert client.get(STATUS, headers=auth(login(client, role)["access_token"])).status_code == 403


def test_another_admin_is_refused(client, db):
    password = add_admin(db)
    r = client.get(STATUS, headers=sign_in_as(client, "otheradmin", password))
    assert r.status_code == 403 and r.json()["code"] == "forbidden"


def test_the_binding_follows_the_configured_login(client, db, monkeypatch):
    password = add_admin(db)
    monkeypatch.setenv("MANI_FOUNDER_LOGIN_ID", "OtherAdmin")  # case does not matter
    get_mani_settings.cache_clear()
    assert client.get(STATUS, headers=sign_in_as(client, "otheradmin", password)).status_code == 200
    original = auth(login(client, "admin")["access_token"])
    assert client.get(STATUS, headers=original).status_code == 403


def test_an_empty_binding_lets_nobody_in(client, monkeypatch):
    monkeypatch.setenv("MANI_FOUNDER_LOGIN_ID", "")
    get_mani_settings.cache_clear()
    assert client.get(STATUS, headers=auth(login(client, "admin")["access_token"])).status_code == 403


def test_a_deactivated_founder_is_refused(client, db):
    headers = auth(login(client, "admin")["access_token"])
    founder = db.scalars(select(Login).where(Login.login_id == "priveopapa")).one()
    founder.active = False
    db.commit()
    assert client.get(STATUS, headers=headers).status_code in (401, 403)
