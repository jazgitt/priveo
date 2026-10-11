"""Admin alerts (ADM-ACC-09, ADM-SCH-24).

Every alert is saved, so the app and the web bell can list it with an unread
count. The phone push and the email go through the notifier Protocols.
Other modules raise their alerts with `raise_alert`.
"""
import logging

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.platform.db import utcnow
from app.platform.errors import ApiError
from app.support.models import AdminAlert
from app.support.notify import (
    EmailNotifier,
    LoggingEmailNotifier,
    LoggingPushNotifier,
    PushNotifier,
)

log = logging.getLogger("priveo.support.alerts")


def raise_alert(db: Session, kind: str, title: str, body: str = "", *,
                ref_type: str | None = None, ref_id: str | None = None,
                push: PushNotifier | None = None,
                email: EmailNotifier | None = None) -> AdminAlert:
    alert = AdminAlert(kind=kind, title=title[:160], body=body[:500],
                       ref_type=ref_type, ref_id=ref_id)
    db.add(alert)
    db.commit()
    # A failed push or email must not lose the alert, which is already saved.
    try:
        (push or LoggingPushNotifier()).push_admin(title, body)
        (email or LoggingEmailNotifier()).send_admin_alert(title, body)
    except Exception:
        log.exception("alert %s saved, but the push or email failed", alert.id)
    return alert


def unread_count(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(AdminAlert).where(AdminAlert.read_at.is_(None))) or 0


def list_alerts(db: Session, unread_only: bool = False, limit: int = 100) -> list[AdminAlert]:
    query = select(AdminAlert).order_by(AdminAlert.created_at.desc()).limit(limit)
    if unread_only:
        query = query.where(AdminAlert.read_at.is_(None))
    return list(db.scalars(query))


def mark_read(db: Session, alert_id) -> None:
    alert = db.get(AdminAlert, alert_id)
    if alert is None:
        raise ApiError("not_found", "That alert was not found.", 404)
    if alert.read_at is None:
        alert.read_at = utcnow()
        db.commit()


def mark_all_read(db: Session) -> None:
    db.execute(update(AdminAlert).where(AdminAlert.read_at.is_(None)).values(read_at=utcnow()))
    db.commit()
