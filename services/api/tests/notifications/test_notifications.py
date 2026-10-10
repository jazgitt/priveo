"""The in-app inbox, mark read and the device-token registry (NOTIF-01, NOTIF-02)."""
import pytest
from sqlalchemy.orm import Session

from app.customers.models import Customer
from app.notifications.push import LoggingPushSender
from app.notifications.service import NotificationService
from tests.customer_reads.conftest import add_customer


@pytest.fixture
def asha(db, headers_for):
    add_customer(db, "asha@example.com", [("HR26DK8337", "Creta", True)])
    login_id = db.query(Customer).filter_by(email="asha@example.com").one().login_id
    return {"headers": headers_for("asha@example.com"), "login_id": login_id}


def service(engine, push=None):
    return NotificationService(Session(engine, expire_on_commit=False),
                               push or LoggingPushSender())


def test_inbox_lists_newest_first_with_unread_count(api, asha, engine):
    s = service(engine)
    s.notify(asha["login_id"], "service_completed", "Today's clean is done", "5 of 5",
             visit_id="v-1")
    s.notify(asha["login_id"], "service_skipped", "Visit skipped")
    r = api.get("/v1/customer/notifications", headers=asha["headers"])
    body = r.json()
    assert body["unread_count"] == 2
    assert [i["title"] for i in body["items"]] == ["Visit skipped", "Today's clean is done"]
    assert body["items"][1]["visit_id"] == "v-1" and body["items"][1]["read"] is False


def test_mark_one_and_mark_all_read(api, asha, engine):
    s = service(engine)
    a = s.notify(asha["login_id"], "service_completed", "One")
    s.notify(asha["login_id"], "renewal_reminder", "Two")
    h = asha["headers"]
    assert api.post(f"/v1/customer/notifications/{a.id}/read", headers=h).status_code == 204
    body = api.get("/v1/customer/notifications?unread_only=true", headers=h).json()
    assert body["unread_count"] == 1 and [i["title"] for i in body["items"]] == ["Two"]
    assert api.post("/v1/customer/notifications/read-all", headers=h).status_code == 204
    assert api.get("/v1/customer/notifications", headers=h).json()["unread_count"] == 0


def test_a_message_of_someone_else_cannot_be_marked(api, asha, engine, db):
    add_customer(db, "other@example.com", [("MH12AB0001", "Alto", True)])
    other = db.query(Customer).filter_by(email="other@example.com").one().login_id
    n = service(engine).notify(other, "service_completed", "Theirs")
    r = api.post(f"/v1/customer/notifications/{n.id}/read", headers=asha["headers"])
    assert r.status_code == 404


def test_device_tokens_register_move_and_remove(api, asha, engine):
    h = asha["headers"]
    body = {"token": "fcm-token-123456", "platform": "android"}
    assert api.put("/v1/customer/devices", json=body, headers=h).status_code == 204
    assert api.put("/v1/customer/devices", json=body, headers=h).status_code == 204
    push = LoggingPushSender()
    service(engine, push).notify(asha["login_id"], "service_completed", "Done", visit_id="v-9")
    assert len(push.sent) == 1
    assert push.sent[0].tokens == ("fcm-token-123456",)
    assert push.sent[0].data == {"event": "service_completed", "visit_id": "v-9"}
    assert api.delete("/v1/customer/devices/fcm-token-123456",
                      headers=h).status_code == 204
    service(engine, push).notify(asha["login_id"], "service_skipped", "Skipped")
    assert len(push.sent) == 1


def test_bad_device_body_and_unknown_event(api, asha, engine):
    r = api.put("/v1/customer/devices", json={"token": "x", "platform": "web"},
                headers=asha["headers"])
    assert r.status_code == 422
    with pytest.raises(ValueError):
        service(engine).notify(asha["login_id"], "promo", "Sale")


def test_inbox_needs_a_customer_sign_in(api):
    assert api.get("/v1/customer/notifications").status_code == 401
