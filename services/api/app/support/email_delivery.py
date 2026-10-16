"""Preference-aware admin Resend delivery with bounded durable retries."""
import logging
from datetime import timedelta

from sqlalchemy import select

from app.identity.models import Login
from app.platform.config import get_settings
from app.platform.db import utcnow
from app.platform.email import EmailSendError, ResendEmailSender
from app.support.models import AdminAlert, AdminAlertEmail

log = logging.getLogger(__name__)


def enqueue(db, alert):
    for login in db.scalars(select(Login).where(Login.role == "admin", Login.active.is_(True),
                                               Login.alert_email_enabled.is_(True),
                                               Login.alert_email != "")):
        db.add(AdminAlertEmail(alert_id=alert.id, login_id=login.id, recipient_email=login.alert_email))


def deliver_pending(db, *, now=None, sender=None, limit=50):
    now = now or utcnow()
    settings = get_settings()
    if sender is None and settings.resend_api_key.strip():
        sender = ResendEmailSender(settings.resend_api_key.strip(), settings.email_from,
                                   redirect_to=settings.email_redirect_to)
    sent = 0
    # Concurrent cron workers serialize rows; Resend also receives a stable key.
    rows = list(db.scalars(select(AdminAlertEmail).where(
        AdminAlertEmail.delivered_at.is_(None), AdminAlertEmail.stopped_at.is_(None),
        AdminAlertEmail.next_attempt_at <= now,
    ).order_by(AdminAlertEmail.next_attempt_at, AdminAlertEmail.id).limit(limit)
       .with_for_update(skip_locked=True)))
    for row in rows:
        login = db.get(Login, row.login_id)
        if (not login or not login.active or not login.alert_email_enabled
                or login.alert_email != row.recipient_email):
            row.stopped_at = now
            continue
        # Missing configuration preserves pending work without consuming retries.
        if sender is None:
            continue
        alert = db.get(AdminAlert, row.alert_id)
        row.attempts += 1
        try:
            sender.send_alert(row.recipient_email, alert.title, alert.body, f"admin-alert/{row.id}")
        except EmailSendError:
            row.next_attempt_at = now + timedelta(minutes=min(60, 5 * 2 ** (row.attempts - 1)))
            if row.attempts >= 5:
                row.stopped_at = now
            log.warning("Admin alert email failed; delivery %s attempt %s", row.id, row.attempts)
        else:
            row.delivered_at = now
            sent += 1
    db.commit()
    return sent
