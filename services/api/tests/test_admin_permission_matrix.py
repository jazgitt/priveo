"""A-03: every admin route that changes data refuses an anonymous call (401) and a
customer or crew token (403). The routes are read from the app, so a route
another change adds later is covered without editing this file."""
import re
import uuid

import pytest

from app.main import create_app
from tests.test_api import auth, login

MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
SKIPPED_PREFIXES = ("/v1/admin/auth",)  # the admin's own sign-in routes


def admin_write_routes():
    # The OpenAPI document lists every route, however the routers are mounted.
    out = []
    for path, item in create_app().openapi()["paths"].items():
        if not path.startswith("/v1/admin") or path.startswith(SKIPPED_PREFIXES):
            continue
        if "/internal" in path:
            continue
        for method in item:
            if method.upper() in MUTATING:
                out.append((method.upper(), path))
    return sorted(out)


ROUTES = admin_write_routes()


def concrete(path: str) -> str:
    # The auth dependency runs before the handler, so any id will do.
    return re.sub(r"\{[^}]+\}", lambda _: str(uuid.uuid4()), path)


def test_the_matrix_finds_the_admin_write_routes():
    assert len(ROUTES) > 50
    assert not any(p.startswith("/v1/admin/auth") or "/internal" in p for _, p in ROUTES)


@pytest.mark.parametrize(("method", "path"), ROUTES, ids=[f"{m} {p}" for m, p in ROUTES])
def test_admin_writes_need_an_admin(client, method, path):
    url = concrete(path)
    anonymous = client.request(method, url, json={})
    assert anonymous.status_code == 401, f"anonymous {method} {path}: {anonymous.status_code}"


@pytest.fixture
def tokens(client):
    return {role: auth(login(client, role)["access_token"]) for role in ("customer", "crew")}


@pytest.mark.parametrize("role", ["customer", "crew"])
def test_admin_writes_refuse_other_roles(client, tokens, role):
    wrong = []
    for method, path in ROUTES:
        r = client.request(method, concrete(path), json={}, headers=tokens[role])
        if r.status_code != 403:
            wrong.append(f"{method} {path}: {r.status_code}")
    assert not wrong, f"{role} token was not refused with 403:\n" + "\n".join(wrong)
