import pytest
from fastapi.testclient import TestClient

from app import webauth
from app.webauth import portal
from tests.conftest import LOGIN_IDS, PASSWORDS

LOGIN = "/v1/web/login"
ME = "/v1/web/me"
LOGOUT = "/v1/web/logout"
ADMIN_HOME = "/v1/admin/home"
ALL_DEVICES = "/v1/admin/sessions/logout-all"


@pytest.fixture
def web(client):
    """A browser: https, so the Secure cookies are kept and sent."""
    app = client.app
    if not any(getattr(r, "path", "") == LOGIN for r in app.routes):
        webauth.register(app)
    return TestClient(app, base_url="https://testserver")


def sign_in(web, password=None, login_id=None):
    return web.post(LOGIN, json={
        "login_id": login_id or LOGIN_IDS["admin"],
        "password": PASSWORDS["admin"] if password is None else password,
    })


def csrf(web):
    return {"X-CSRF-Token": web.cookies.get("priveo_csrf")}


def test_login_sets_the_cookies_and_returns_the_profile(web):
    r = sign_in(web)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "admin" and body["display_name"]
    set_cookie = r.headers.get_list("set-cookie")
    session = next(c for c in set_cookie if c.startswith("priveo_session="))
    token = next(c for c in set_cookie if c.startswith("priveo_csrf="))
    for flag in ("httponly", "secure", "samesite=strict"):
        assert flag in session.lower()
    assert "httponly" not in token.lower()
    assert "secure" in token.lower() and "samesite=strict" in token.lower()
    # The token is not also handed to the page script in the body.
    assert "access_token" not in body and "refresh_token" not in body


def test_me_reads_the_cookie_session(web):
    assert web.get(ME).status_code == 401
    sign_in(web)
    r = web.get(ME)
    assert r.status_code == 200 and r.json()["role"] == "admin"
    assert web.get(ADMIN_HOME).status_code == 200  # reads need no CSRF header


def test_a_change_by_cookie_needs_the_csrf_header(web):
    sign_in(web)
    missing = web.post(ALL_DEVICES)
    assert missing.status_code == 403 and missing.json()["code"] == "csrf_failed"
    wrong = web.post(ALL_DEVICES, headers={"X-CSRF-Token": "not-it"})
    assert wrong.status_code == 403
    # A header with no matching cookie fails too.
    good = csrf(web)
    web.cookies.delete("priveo_csrf")
    assert web.post(ALL_DEVICES, headers=good).status_code == 403


def test_a_matching_csrf_header_is_accepted(web):
    sign_in(web)
    assert web.post(ALL_DEVICES, headers=csrf(web)).status_code == 204


def test_a_csrf_value_from_another_session_is_refused(web, client):
    sign_in(web)
    other = TestClient(client.app, base_url="https://testserver")
    sign_in(other)
    stolen = {"X-CSRF-Token": other.cookies.get("priveo_csrf")}
    web.cookies.set("priveo_csrf", stolen["X-CSRF-Token"])
    assert web.post(ALL_DEVICES, headers=stolen).status_code == 403


def test_logout_ends_the_session(web):
    sign_in(web)
    session_cookie = web.cookies.get("priveo_session")
    assert web.post(LOGOUT).status_code == 403  # a live session needs the header
    r = web.post(LOGOUT, headers=csrf(web))
    assert r.status_code == 204
    assert web.cookies.get("priveo_session") is None
    # The old cookie no longer works, even if someone kept a copy.
    web.cookies.set("priveo_session", session_cookie)
    assert web.get(ME).status_code == 401


def test_logout_without_a_session_just_clears(web):
    assert web.post(LOGOUT).status_code == 204


def test_five_wrong_passwords_lock_the_admin(web):
    for _ in range(4):
        assert sign_in(web, "nope").status_code == 401
    r = sign_in(web, "nope")
    assert r.status_code == 403 and r.json()["code"] == "account_locked"
    assert sign_in(web).status_code == 403  # even the right password
    assert "set-cookie" not in sign_in(web).headers


def test_crew_and_customers_cannot_sign_in_to_the_portal(web):
    for role in ("crew", "customer"):
        r = sign_in(web, PASSWORDS[role], LOGIN_IDS[role])
        assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"
    assert web.get(ME).status_code == 401


def test_bearer_tokens_still_work_without_csrf(web, client):
    token = client.post("/v1/auth/login", json={
        "login_id": LOGIN_IDS["admin"], "password": PASSWORDS["admin"]}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    plain = TestClient(client.app)  # no cookies at all
    assert plain.get(ADMIN_HOME, headers=headers).status_code == 200
    assert plain.post(ALL_DEVICES, headers=headers).status_code == 204
    assert plain.get(ADMIN_HOME, headers=headers).status_code == 401


def test_a_crew_token_is_refused_on_admin_routes(web, client):
    crew = client.post("/v1/auth/login", json={
        "login_id": LOGIN_IDS["crew"], "password": PASSWORDS["crew"]}).json()["access_token"]
    r = web.get(ADMIN_HOME, headers={"Authorization": f"Bearer {crew}"})
    assert r.status_code == 403
    r = web.get(ME, headers={"Authorization": f"Bearer {crew}"})
    assert r.status_code == 403


def test_a_crew_token_in_the_cookie_is_refused_too(web, client):
    crew = client.post("/v1/auth/login", json={
        "login_id": LOGIN_IDS["crew"], "password": PASSWORDS["crew"]}).json()["access_token"]
    web.cookies.set("priveo_session", crew)
    assert web.get(ADMIN_HOME).status_code == 403


# --- the static portal ---

@pytest.fixture
def built(web, tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>portal</html>")
    (tmp_path / "assets" / "app-abc.js").write_text("console.log(1)")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    monkeypatch.setattr(portal, "PORTAL_DIR", tmp_path)
    return web


def test_portal_pages_fall_back_to_index(built):
    for path in ("/portal/", "/portal/customers", "/portal/customers/12/edit"):
        r = built.get(path)
        assert r.status_code == 200 and "portal" in r.text
        assert r.headers["cache-control"] == "no-cache"
    assert built.get("/portal", follow_redirects=False).headers["location"] == "/portal/"


def test_portal_files_are_served_and_cached(built):
    r = built.get("/portal/assets/app-abc.js")
    assert r.status_code == 200 and "immutable" in r.headers["cache-control"]
    assert built.get("/portal/favicon.svg").status_code == 200


def test_portal_missing_file_is_404_not_index(built):
    assert built.get("/portal/assets/gone.js").status_code == 404


def test_portal_cannot_escape_its_folder(built, tmp_path):
    (tmp_path.parent / "secret.txt").write_text("secret")
    r = built.get("/portal/..%2Fsecret.txt")
    assert r.status_code == 404 and "secret" not in r.text


def test_portal_not_built(web, tmp_path, monkeypatch):
    monkeypatch.setattr(portal, "PORTAL_DIR", tmp_path / "missing")
    r = web.get("/portal/")
    assert r.status_code == 404 and r.json()["code"] == "portal_not_built"
