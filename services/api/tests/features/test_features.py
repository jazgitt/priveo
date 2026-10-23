import pytest
from sqlalchemy.orm import Session

from app.directory.models import DirectoryAudit
from app.features import registry, service
from app.features.models import FeatureFlag
from tests.test_api import auth, login


def _login(client, role):
    return auth(login(client, role)["access_token"])


@pytest.fixture
def admin(client):
    return _login(client, "admin")


def test_registry_keys_are_unique_and_valid():
    assert len({f.key for f in registry.FLAGS}) == len(registry.FLAGS)
    assert all(f.audience in ("customer", "crew", "both") for f in registry.FLAGS)


def test_only_admin_can_list_or_change(client, admin):
    assert client.get("/v1/admin/features").status_code == 401
    cust = _login(client, "customer")
    assert client.get("/v1/admin/features", headers=cust).status_code == 403
    assert client.put("/v1/admin/features/customer.deep_spa", headers=cust,
                      json={"enabled": False}).status_code == 403
    listed = client.get("/v1/admin/features", headers=admin).json()
    assert len(listed) == len(registry.FLAGS)
    assert all(f["enabled"] for f in listed)


def test_toggle_is_audited_and_reaches_the_app(client, admin, engine):
    r = client.put("/v1/admin/features/customer.deep_spa", headers=admin,
                   json={"enabled": False})
    assert r.status_code == 200 and r.json()["enabled"] is False
    cust = _login(client, "customer")
    flags = client.get("/v1/customer/features", headers=cust).json()["flags"]
    assert flags["customer.deep_spa"] is False
    assert flags["customer.addons"] is True
    assert "crew.notifications" not in flags and "common.push" in flags
    with Session(engine) as db:
        rows = db.query(DirectoryAudit).filter_by(entity="feature_flag").all()
        assert rows[0].detail == {"enabled": [True, False]}


def test_unknown_flag_is_404(client, admin):
    assert client.put("/v1/admin/features/nope", headers=admin,
                      json={"enabled": False}).status_code == 404


def test_etag_gives_304_until_a_flag_changes(client, admin):
    cust = _login(client, "customer")
    first = client.get("/v1/customer/features", headers=cust)
    etag = first.headers["ETag"]
    again = client.get("/v1/customer/features", headers={**cust, "If-None-Match": etag})
    assert again.status_code == 304 and again.content == b""
    client.put("/v1/admin/features/customer.history", headers=admin, json={"enabled": False})
    after = client.get("/v1/customer/features", headers={**cust, "If-None-Match": etag})
    assert after.status_code == 200 and after.headers["ETag"] != etag


def test_crew_sees_only_crew_and_common_flags(client):
    crew = _login(client, "crew")
    flags = client.get("/v1/crew/features", headers=crew).json()["flags"]
    assert "crew.notifications" in flags and "common.push" in flags
    assert not any(k.startswith("customer.") for k in flags)


def test_disabled_feature_is_refused_by_the_server(client, admin):
    cust = _login(client, "customer")
    client.put("/v1/admin/features/customer.deep_spa", headers=admin, json={"enabled": False})
    r = client.post("/v1/customer/addons/standalone", headers=cust, json={})
    assert r.status_code == 403 and r.json()["code"] == "feature_disabled"


def test_add_vehicle_is_refused_when_off(client, admin):
    cust = _login(client, "customer")
    client.put("/v1/admin/features/customer.add_vehicle", headers=admin, json={"enabled": False})
    r = client.post("/v1/customer/vehicles", headers=cust, json={})
    assert r.status_code == 403 and r.json()["code"] == "feature_disabled"


def test_missing_row_means_on_and_cache_expires(db, engine):
    assert service.is_enabled(db, "customer.deep_spa") is True
    with Session(engine) as other:
        other.add(FeatureFlag(key="customer.deep_spa", enabled=False))
        other.commit()
    # Still cached.
    assert service.is_enabled(db, "customer.deep_spa") is True
    service.invalidate()
    assert service.is_enabled(db, "customer.deep_spa") is False
    with pytest.raises(KeyError):
        service.is_enabled(db, "typo")
