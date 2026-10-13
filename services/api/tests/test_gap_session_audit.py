"""P08 audit transaction regressions; written, not executed."""
import pytest
from sqlalchemy import event, select

from app.customers.models import Customer
from app.directory.models import DirectoryAudit
from app.identity.models import AuthSession, Login
from app.identity.service import AuthService
from tests.test_api import auth, login


def test_admin_and_customer_reads_observe_last_committed_profile_edit(client, db):
    customer, admin = login(client, "customer"), login(client, "admin")
    c = db.scalar(select(Customer))
    body = {"first_name": "Admin", "last_name": "Edit", "mobile": "9876543210", "flat": "A1"}
    assert client.patch(f"/v1/admin/customers/{c.id}", headers=auth(admin["access_token"]), json=body).status_code == 200
    assert client.get("/v1/customer/profile", headers=auth(customer["access_token"])).json()["first_name"] == "Admin"
    body.pop("flat")
    body["first_name"] = "Customer"
    assert client.patch("/v1/customer/profile", headers=auth(customer["access_token"]), json=body).status_code == 200
    assert client.get(f"/v1/admin/customers/{c.id}", headers=auth(admin["access_token"])).json()["first_name"] == "Customer"


def test_customer_logout_all_records_admin_actor_and_reason(client, db):
    customer = login(client, "customer")
    admin = login(client, "admin")
    c = db.scalar(select(Customer))
    actor = db.scalar(select(Login).where(Login.role == "admin"))
    result = client.post(f"/v1/admin/customers/{c.id}/sessions/logout", headers=auth(admin["access_token"]))
    assert result.status_code == 200
    entry = db.scalar(select(DirectoryAudit).where(DirectoryAudit.action == "sessions_logout"))
    assert entry.admin_login_id == actor.id and entry.entity_id == str(c.id)
    assert entry.at and entry.detail == {"reason": "admin_logout", "ended": result.json()["ended"]}
    assert client.get("/v1/customer/home", headers=auth(customer["access_token"])).status_code == 401


def test_admin_logout_all_has_actor_target_count_and_time(client, db):
    one, two = login(client, "admin"), login(client, "admin")
    actor = db.scalar(select(Login).where(Login.role == "admin"))
    assert client.post("/v1/admin/sessions/logout-all", headers=auth(one["access_token"])).status_code == 204
    entry = db.scalar(select(DirectoryAudit).where(DirectoryAudit.action == "logout_all"))
    assert entry.admin_login_id == actor.id and entry.entity_id == str(actor.id)
    assert entry.at and entry.detail == {"reason": "logout_all", "ended": 2}
    assert client.get("/v1/admin/home", headers=auth(two["access_token"])).status_code == 401


def test_failed_audit_insert_rolls_back_session_revocation(client, db, settings):
    login(client, "customer")
    login(client, "admin")
    c = db.scalar(select(Customer))
    actor = db.scalar(select(Login).where(Login.role == "admin"))
    def fail(*_):
        raise RuntimeError("audit write failed")
    event.listen(DirectoryAudit, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="audit write failed"):
            AuthService(settings, db).end_customer_sessions(c.login_id, "admin_logout",
                actor_id=actor.id, customer_id=c.id)
    finally:
        event.remove(DirectoryAudit, "before_insert", fail)
        db.rollback()
    assert db.scalar(select(AuthSession).where(AuthSession.login_id == c.login_id)).ended_at is None
    assert db.scalar(select(DirectoryAudit)) is None
