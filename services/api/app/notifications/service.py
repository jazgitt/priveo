"""The in-app inbox and the device-token registry (NOTIF-01, NOTIF-02)."""
import uuid

from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.notifications.models import DeviceToken, Notification
from app.notifications.push import PushSender
from app.platform.db import utcnow
from app.platform.errors import ApiError

# The MVP events (NOTIF-02). No other event notifies.
EVENTS = ("service_completed", "service_skipped", "complaint_update",
          "renewal_reminder", "monthly_check_in")


class NotificationOut(BaseModel):
    id: str
    event: str
    title: str
    body: str
    visit_id: str | None
    created_at: str
    read: bool


class Inbox(BaseModel):
    unread_count: int
    items: list[NotificationOut]


class NotificationService:
    def __init__(self, db: Session, push: PushSender):
        self._db = db
        self._push = push

    def notify(self, login_id: uuid.UUID, event: str, title: str, body: str = "",
               visit_id: str | None = None) -> Notification:
        """Adds to the inbox and pushes to the person's phones. Other modules
        call this when something happens (a visit is completed, and so on)."""
        if event not in EVENTS:
            raise ValueError(f"Unknown notification event: {event}")
        row = Notification(login_id=login_id, event=event, title=title, body=body,
                           visit_id=visit_id)
        self._db.add(row)
        self._db.commit()
        tokens = list(self._db.scalars(
            select(DeviceToken.token).where(DeviceToken.login_id == login_id)))
        if tokens:
            data = {"event": event}
            if visit_id:
                data["visit_id"] = visit_id
            self._push.send(tokens, title, body, data)
        return row

    def inbox(self, login_id: uuid.UUID, unread_only: bool, limit: int,
              offset: int) -> Inbox:
        query = select(Notification).where(Notification.login_id == login_id)
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        rows = self._db.scalars(
            query.order_by(Notification.created_at.desc(), Notification.id)
            .limit(limit).offset(offset)).all()
        unread = self._db.scalar(
            select(func.count()).select_from(Notification)
            .where(Notification.login_id == login_id, Notification.read_at.is_(None)))
        return Inbox(unread_count=unread or 0, items=[
            NotificationOut(id=str(r.id), event=r.event, title=r.title, body=r.body,
                            visit_id=r.visit_id, created_at=r.created_at.isoformat(),
                            read=r.read_at is not None)
            for r in rows])

    def mark_read(self, login_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        row = self._db.get(Notification, notification_id)
        if row is None or row.login_id != login_id:
            raise ApiError("notification_not_found", "This message was not found.", 404)
        if row.read_at is None:
            row.read_at = utcnow()
            self._db.commit()

    def mark_all_read(self, login_id: uuid.UUID) -> None:
        self._db.execute(
            update(Notification)
            .where(Notification.login_id == login_id, Notification.read_at.is_(None))
            .values(read_at=utcnow()))
        self._db.commit()

    def register_token(self, login_id: uuid.UUID, token: str, platform: str) -> None:
        """One token belongs to one login: signing in on a phone moves it."""
        row = self._db.scalar(select(DeviceToken).where(DeviceToken.token == token))
        if row is None:
            self._db.add(DeviceToken(login_id=login_id, token=token, platform=platform))
        else:
            row.login_id, row.platform, row.updated_at = login_id, platform, utcnow()
        self._db.commit()

    def remove_token(self, login_id: uuid.UUID, token: str) -> None:
        row = self._db.scalar(select(DeviceToken).where(
            DeviceToken.token == token, DeviceToken.login_id == login_id))
        if row is not None:
            self._db.delete(row)
            self._db.commit()
