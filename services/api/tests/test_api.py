import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.platform.config import get_settings

LOGINS = {
    "customer": ("customer@priveo.test", "pw-customer"),
    "crew": ("9000000002", "pw-crew"),
    "admin": ("priveopapa", "pw-admin"),
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOCK_CUSTOMER_PASSWORD", "pw-customer")
    monkeypatch.setenv("MOCK_CREW_PASSWORD", "pw-crew")
    monkeypatch.setenv("MOCK_ADMIN_PASSWORD", "pw-admin")
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def login(client, role):
    login_id, password = LOGINS[role]
    r = client.post("/v1/auth/login", json={"login_id": login_id, "password": password})
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


def test_wrong_password_returns_envelope(client):
    r = client.post("/v1/auth/login", json={"login_id": "priveopapa", "password": "nope"})
    assert r.status_code == 401
    body = r.json()
    assert body["code"] == "invalid_credentials"
    assert body["message"] and body["request_id"]


def test_unset_password_disables_login(monkeypatch):
    monkeypatch.setenv("MOCK_ADMIN_PASSWORD", "")
    get_settings.cache_clear()
    r = TestClient(create_app()).post(
        "/v1/auth/login", json={"login_id": "priveopapa", "password": ""})
    assert r.status_code == 401
    get_settings.cache_clear()


def test_role_is_enforced(client):
    token = login(client, "customer")["access_token"]
    assert client.get("/v1/admin/home", headers=auth(token)).status_code == 403
    assert client.get("/v1/crew/home").status_code == 401


def test_refresh_and_token_kinds(client):
    data = login(client, "crew")
    r = client.post("/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 200
    # A refresh token must not work as an access token.
    assert client.get("/v1/crew/home", headers=auth(data["refresh_token"])).status_code == 401


def test_crew_home_has_no_customer_details(client):
    token = login(client, "crew")["access_token"]
    text = client.get("/v1/crew/home", headers=auth(token)).text.lower()
    assert "customer" not in text and "mobile" not in text and "phone" not in text


def test_validation_error_envelope(client):
    r = client.post("/v1/auth/login", json={})
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
