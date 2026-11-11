"""B-23: an access-control matrix over every route of the app.

The routes are read from the app itself (each route's dependency tree says which role it needs), so a
route added later is covered without editing this file. A new route that needs no sign-in fails
`test_every_route_is_protected_or_listed_as_public` until it is added to PUBLIC on purpose.

(a) a call with no token gets 401 on every protected route;
(b) a token of any other role gets 403, never 200 or 500;
(c) a customer who does not own a vehicle, payment, complaint or upload gets 403 or 404.
"""
import re
import uuid
from datetime import date

import pytest
from fastapi.routing import APIRoute

from app.billing.models import Payment
from app.customers.models import Customer
from app.identity.models import Login
from app.identity.service import hash_password
from app.main import create_app
from app.support.models import Complaint
from tests.customer_reads.conftest import PASSWORD, add_customer
from tests.people import sign_in_customer
from tests.test_api import auth, login

ROLES = ("customer", "crew", "admin")

# Routes that need no sign-in, listed on purpose. Each is one (method, path).
PUBLIC = {
    ("GET", "/v1/public/health"),
    ("GET", "/v1/public/config"),
    ("GET", "/v1/auth/support-contact"),
    ("GET", "/v1/auth/legal-links"),
    ("POST", "/v1/auth/code"),
    ("POST", "/v1/auth/code/verify"),
    ("POST", "/v1/auth/mpin"),
    ("POST", "/v1/auth/login"),
    ("POST", "/v1/auth/refresh"),
    ("POST", "/v1/auth/logout"),
    # The portal's own sign-in and sign-out (a cookie session starts or ends here).
    ("POST", "/v1/web/login"),
    ("POST", "/v1/web/logout"),
    # Signed object-store URLs: the signature in the query is the credential.
    ("PUT", "/v1/media/local/{upload_id}"),
    ("GET", "/v1/media/local/{upload_id}"),
    ("GET", "/v1/media/blob/{upload_id}"),
    # The static portal files.
    ("GET", "/portal"),
    ("GET", "/portal/"),
    ("GET", "/portal/{path:path}"),
}
# Scheduled jobs: guarded by the cron secret, not by a role.
CRON = {("GET", "/v1/internal/cron/{job}"), ("POST", "/v1/internal/cron/{job}")}
# Parts of the app that are not API routes and are never gated.
NOT_API = {"/openapi.json"}


def _walk(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _walk(dep)


def _role_of(call):
    if getattr(call, "__qualname__", "").startswith("require_role"):
        cells = dict(zip(call.__code__.co_freevars, (c.cell_contents for c in call.__closure__), strict=False))
        return cells["role"]
    return None


def _flatten(routes, prefix=""):
    # FastAPI keeps an included router as one object; its routes are opened here.
    for r in routes:
        if hasattr(r, "original_router"):
            yield from _flatten(r.original_router.routes, prefix + r.include_context.prefix)
        elif isinstance(r, APIRoute):
            yield prefix + r.path, r
        else:
            yield prefix + getattr(r, "path", "?"), r


# Routes behind a feature switch. FastAPI runs that check before the sign-in check, so while the
# feature is off an anonymous call is refused with 403 feature_disabled instead of 401. Nothing is
# opened by it (the route is refused either way); it only tells a stranger that a switch is off.
FEATURE_GATED: set[str] = set()


def collect():
    """[(method, path, role_or_None, is_cron)] for every route, and the non-API paths."""
    out, other = [], set()
    for path, r in _flatten(create_app().routes):
        if not isinstance(r, APIRoute):
            other.add(path)
            continue
        calls = list(_walk(r.dependant))
        roles = {_role_of(c) for c in calls} - {None}
        assert len(roles) <= 1, f"{path} asks for more than one role: {roles}"
        cron = any(getattr(c, "__name__", "") == "require_cron_secret" for c in calls)
        if any(getattr(c, "__qualname__", "").startswith("require_feature") for c in calls):
            FEATURE_GATED.add(path)
        for method in sorted(r.methods - {"HEAD", "OPTIONS"}):
            out.append((method, path, next(iter(roles), None), cron))
    return out, other


ROUTES, NON_API = collect()
PROTECTED = sorted((m, p, role) for m, p, role, _ in ROUTES if role)
IDS = [f"{m} {p}" for m, p, _ in PROTECTED]


def concrete(path: str, values: dict | None = None) -> str:
    values = values or {}
    return re.sub(r"\{([^}:]+)[^}]*\}", lambda m: values.get(m.group(1), str(uuid.uuid4())), path)


def test_the_matrix_sees_the_whole_app():
    by_role = {r: sum(1 for *_, role in PROTECTED if role == r) for r in ROLES}
    assert by_role["admin"] > 150 and by_role["customer"] > 40 and by_role["crew"] > 20, by_role
    paths = {(m, p) for m, p, *_ in ROUTES}
    # Every route in the published contract is one the matrix walks.
    contract = {(m.upper(), p) for p, item in create_app().openapi()["paths"].items() for m in item}
    assert contract <= paths, sorted(contract - paths)


def test_every_route_is_protected_or_listed_as_public():
    open_routes = {(m, p) for m, p, role, cron in ROUTES if not role and not cron}
    assert open_routes == PUBLIC, (
        f"not listed: {sorted(open_routes - PUBLIC)}; listed but not open: {sorted(PUBLIC - open_routes)}")
    assert {(m, p) for m, p, _, cron in ROUTES if cron} == CRON
    assert NON_API == NOT_API


@pytest.fixture
def tokens(client):
    return {role: auth(login(client, role)["access_token"]) for role in ROLES}


@pytest.mark.parametrize(("method", "path", "role"), PROTECTED, ids=IDS)
def test_no_token_is_401(client, method, path, role):
    r = client.request(method, concrete(path), json={})
    if path in FEATURE_GATED and r.status_code == 403:
        assert r.json()["code"] == "feature_disabled", r.text
        return
    assert r.status_code == 401, f"{role} route without a token: {r.status_code}"


@pytest.mark.parametrize(("method", "path", "role"), PROTECTED, ids=IDS)
def test_a_garbage_token_is_401(client, method, path, role):
    r = client.request(method, concrete(path), json={}, headers=auth("not-a-token"))
    if path in FEATURE_GATED and r.status_code == 403:
        return
    assert r.status_code == 401, f"{role} route with a bad token: {r.status_code}"


def test_cron_needs_its_secret(client):
    for method, path in sorted(CRON):
        r = client.request(method, concrete(path))
        assert r.status_code in (401, 503), f"{method} {path}: {r.status_code}"
        r = client.request(method, concrete(path), headers=auth("wrong-secret"))
        assert r.status_code in (401, 503), f"{method} {path}: {r.status_code}"


@pytest.mark.parametrize("token_role", ROLES)
def test_other_roles_are_refused_with_403(client, tokens, token_role):
    wrong = []
    for method, path, role in PROTECTED:
        if role == token_role:
            continue
        r = client.request(method, concrete(path), json={}, headers=tokens[token_role])
        if r.status_code != 403:
            wrong.append(f"{method} {path} (needs {role}): {r.status_code}")
    assert not wrong, f"a {token_role} token was not refused with 403:\n" + "\n".join(wrong)


def test_admins_who_are_not_the_founder_are_refused_by_mani(client, db):
    db.add(Login(role="admin", login_id="second-admin", display_name="Second",
                 password_hash=hash_password("Second-pw-1")))
    db.commit()
    r = client.post("/v1/auth/login", json={"login_id": "second-admin", "password": "Second-pw-1",
                                            "role": "admin"})
    assert r.status_code == 200, r.text
    headers = auth(r.json()["access_token"])
    mani = [(m, p) for m, p, role in PROTECTED if p.startswith("/v1/admin/mani")]
    assert mani
    for method, path in mani:
        r = client.request(method, concrete(path), json={}, headers=headers)
        assert r.status_code == 403, f"{method} {path}: {r.status_code}"


# (c) Objects that belong to another customer.

@pytest.fixture
def owned(client, engine, db):
    """Another customer's vehicle, payment, complaint and upload, and the demo customer's token."""
    vehicle_id = add_customer(db, "owner@example.com", [("MH12AB0001", "Alto", True)])[0]
    owner = db.query(Customer).filter_by(email="owner@example.com").one()
    payment = Payment(customer_id=owner.id, vehicle_id=uuid.UUID(vehicle_id), kind="Plan",
                      description="Plan", amount_rupees=1299, due_date=date(2026, 11, 20))
    complaint = Complaint(number=9001, customer_id=owner.id, category="Quality", description="x")
    db.add_all([payment, complaint])
    db.commit()
    owner_headers = auth(sign_in_customer(client, "owner@example.com", PASSWORD).json()["access_token"])
    upload = client.post("/v1/customer/uploads", headers=owner_headers,
                         json={"purpose": "vehicle", "content_type": "image/jpeg", "size_bytes": 5})
    assert upload.status_code == 201, upload.text
    return {
        "headers": owner_headers,
        "values": {
            "vehicle_id": vehicle_id,
            "payment_id": str(payment.id),
            "complaint_id": str(complaint.id),
            "upload_id": upload.json()["id"],
        },
    }


# One body that satisfies every object route's schema, so the ownership check is what refuses.
BODY = {"date": "2026-12-01", "from_date": "2026-12-01", "to_date": "2026-12-03", "cutoff_time": "08:00",
        "finish_by": "09:00", "note": "hello"}
OWNED_PLACEHOLDERS = {"vehicle_id", "payment_id", "complaint_id", "upload_id"}
OBJECT_ROUTES = [(m, p) for m, p, role in PROTECTED
                 if role == "customer" and OWNED_PLACEHOLDERS & set(re.findall(r"\{([^}:]+)", p))]


def test_the_matrix_finds_the_customer_object_routes():
    assert len(OBJECT_ROUTES) > 15


def test_the_owner_can_reach_their_own_objects(client, owned):
    values = owned["values"]
    for path in ("/v1/customer/vehicles/{vehicle_id}", "/v1/customer/payments/{payment_id}",
                 "/v1/customer/complaints/{complaint_id}"):
        r = client.get(concrete(path, values), headers=owned["headers"])
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text}"


@pytest.mark.parametrize(("method", "path"), OBJECT_ROUTES, ids=[f"{m} {p}" for m, p in OBJECT_ROUTES])
def test_another_customer_cannot_use_the_object(client, tokens, owned, method, path):
    url = concrete(path, owned["values"])
    # The demo customer owns none of these objects.
    r = client.request(method, url, json=BODY, headers=tokens["customer"])
    assert r.status_code in (403, 404), f"{method} {path}: {r.status_code} {r.text[:200]}"


def test_crew_and_admin_tokens_do_not_open_the_customers_objects(client, tokens, owned):
    for method, path in OBJECT_ROUTES:
        url = concrete(path, owned["values"])
        for role in ("crew", "admin"):
            r = client.request(method, url, json={}, headers=tokens[role])
            assert r.status_code == 403, f"{role} {method} {path}: {r.status_code}"
