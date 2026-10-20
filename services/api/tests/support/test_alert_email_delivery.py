"""P11 preference, provider failure/retry and escalation transaction sources."""
from datetime import timedelta

import pytest
from sqlalchemy import event, select

from app.identity.models import Login
from app.platform.db import utcnow
from app.platform.email import EmailSendError
from app.support import alerts
from app.support.email_delivery import deliver_pending
from app.support.models import AdminAlert, AdminAlertEmail, Complaint
from app.support.service import SupportService
from tests.support.test_support import raise_complaint


class Sender:
    def __init__(self, fail=False):
        self.fail, self.sent = fail, []
    def send_alert(self, to, title, body, key, link=None):
        self.sent.append((to, title, body, key))
        self.links = getattr(self, "links", []) + [link]
        if self.fail:
            raise EmailSendError("provider unavailable")


def configure(db, enabled=True):
    admin = db.scalar(select(Login).where(Login.role == "admin"))
    admin.alert_email, admin.alert_email_enabled = "admin@example.com", enabled
    db.commit()
    return admin


def test_preference_is_own_admin_only_and_persists(client, admin, customer, db):
    path = "/v1/admin/alerts/email-preferences"
    assert client.put(path, headers=customer, json={"email": "x@example.com", "enabled": True}).status_code == 403
    assert client.put(path, headers=admin, json={"email": "invalid", "enabled": True}).status_code == 422
    assert client.put(path, headers=admin, json={"email": "Admin@Example.com", "enabled": False}).status_code == 200
    assert client.get(path, headers=admin).json() == {"email": "admin@example.com", "enabled": False}


def test_disabled_email_preserves_inbox_and_push(client, db):
    configure(db, False)
    alert = alerts.raise_alert(db, "test", "Saved", push=client.push)
    assert db.get(AdminAlert, alert.id) and client.push.admin == [("Saved", "")]
    assert db.scalar(select(AdminAlertEmail)) is None


def test_delivery_retries_once_due_with_same_key_and_no_duplicate_success(client, db):
    configure(db)
    # Keep the queued email pending without any real provider.
    alerts.raise_alert(db, "test", "Saved", email=client.email)
    now = utcnow()
    sender = Sender(fail=True)
    assert deliver_pending(db, now=now, sender=sender) == 0
    row = db.scalar(select(AdminAlertEmail))
    assert row.attempts == 1 and row.delivered_at is None
    sender.fail = False
    assert deliver_pending(db, now=now, sender=sender) == 0
    assert deliver_pending(db, now=now + timedelta(minutes=5), sender=sender) == 1
    assert sender.sent[0][3] == sender.sent[1][3]
    assert deliver_pending(db, now=now + timedelta(hours=1), sender=sender) == 0
    assert db.scalar(select(AdminAlert)) is not None


def test_turning_off_email_stops_pending_delivery(client, db):
    configure(db)
    alerts.raise_alert(db, "test", "Saved", email=client.email)
    configure(db, False)
    sender = Sender()
    assert deliver_pending(db, sender=sender) == 0 and sender.sent == []
    assert db.scalar(select(AdminAlertEmail)).stopped_at is not None


def test_retry_exhaustion_is_bounded_and_does_not_lose_inbox(client, db):
    configure(db)
    alerts.raise_alert(db, "test", "Saved", email=client.email)
    sender, now = Sender(fail=True), utcnow()
    for attempt in range(6):
        deliver_pending(db, now=now + timedelta(hours=attempt), sender=sender)
    assert len(sender.sent) == 5
    assert db.scalar(select(AdminAlertEmail)).stopped_at is not None
    assert db.scalar(select(AdminAlert)) is not None


def test_four_hour_boundary_alerts_once(client, customer, db):
    raise_complaint(client, customer)
    complaint = db.scalar(select(Complaint))
    now = utcnow()
    complaint.created_at = now - timedelta(hours=4)
    db.commit()
    service = SupportService(db, client.push, client.email, now=lambda: now)
    service._now = lambda: now - timedelta(seconds=1)
    assert service.alert_overdue_complaints() == 0
    service._now = lambda: now
    assert service.alert_overdue_complaints() == 1
    assert service.alert_overdue_complaints() == 0


def test_address_change_does_not_redirect_an_old_pending_email(client, db):
    admin = configure(db)
    alerts.raise_alert(db, "test", "Saved", email=client.email)
    admin.alert_email = "new@example.com"
    db.commit()
    sender = Sender()
    assert deliver_pending(db, sender=sender) == 0 and sender.sent == []
    assert db.scalar(select(AdminAlertEmail)).stopped_at is not None


def test_push_failure_does_not_suppress_email_or_inbox(client, db):
    class BrokenPush:
        def push_admin(self, *_):
            raise RuntimeError("push failed")
    alert = alerts.raise_alert(db, "test", "Saved", push=BrokenPush(), email=client.email)
    assert db.get(AdminAlert, alert.id) and client.email.sent == [("Saved", "")]


def test_resend_alert_email_has_a_portal_link_in_text_and_html(monkeypatch):
    import json
    from contextlib import nullcontext

    from app.platform.email import ResendEmailSender
    requests = []
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda request, **_: requests.append(request) or nullcontext())
    ResendEmailSender("k", "s@example.com").send_alert(
        "a@example.com", "New complaint #C-0001", "Asha: Damage\nIt <hurts>", "key",
        link="https://x.example/portal/complaints/1")
    payload = json.loads(requests[0].data)
    assert payload["text"].endswith("Open in the admin portal: https://x.example/portal/complaints/1")
    assert "It &lt;hurts&gt;" in payload["html"] and "<br>" in payload["html"]
    assert '<a href="https://x.example/portal/complaints/1">' in payload["html"]


def test_a_complaint_email_carries_the_text_and_a_portal_link(client, customer, db, monkeypatch):
    from app.platform.config import get_settings
    configure(db)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://dev.example/")
    get_settings.cache_clear()
    raise_complaint(client, customer)
    sender = Sender()
    deliver_pending(db, sender=sender)
    complaint = db.scalar(select(Complaint))
    assert sender.links == [f"https://dev.example/portal/complaints/{complaint.id}"]
    body = sender.sent[0][2]
    assert body.splitlines()[0].endswith(complaint.category)
    assert complaint.description.split()[0] in body
    get_settings.cache_clear()


def test_resend_alert_escapes_html_and_sends_stable_provider_key(monkeypatch):
    import json
    from contextlib import nullcontext

    from app.platform.email import ResendEmailSender
    requests = []
    def accept(request, **_):
        requests.append(request)
        return nullcontext()
    monkeypatch.setattr("urllib.request.urlopen", accept)
    sender = ResendEmailSender("test-key", "sender@example.com")
    sender.send_alert("admin@example.com", "Waiting", "<private>", "stable-key")
    request = requests[0]
    payload = json.loads(request.data)
    assert payload["to"] == ["admin@example.com"] and payload["text"] == "<private>"
    assert payload["html"] == "<p>&lt;private&gt;</p>"
    assert dict(request.header_items())["Idempotency-key"] == "stable-key"


def test_escalation_failure_rolls_back_marker_and_alert(client, customer, db):
    raise_complaint(client, customer)
    complaint = db.scalar(select(Complaint))
    complaint.created_at = utcnow() - timedelta(hours=5)
    db.commit()
    def fail(*_):
        raise RuntimeError("alert insert failed")
    event.listen(AdminAlert, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError):
            SupportService(db, client.push, client.email).alert_overdue_complaints()
    finally:
        event.remove(AdminAlert, "before_insert", fail)
        db.rollback()
    db.refresh(complaint)
    assert complaint.overdue_alerted_at is None
    assert db.scalar(select(AdminAlert).where(AdminAlert.kind == "complaint_overdue")) is None
