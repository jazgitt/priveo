"""The in-app inbox, the device-token registry and the preferences (NOTIF-01
to NOTIF-03, SET-02, CRW-NOT-01 to 05)."""
import uuid

from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.notifications.events import CUSTOMER_EVENTS, EVENTS, LABELS, switchable
from app.notifications.models import DeviceToken, Notification, NotificationPreference
from app.notifications.push import PushSender
from app.platform.db import utcnow
from app.platform.errors import ApiError

__all__ = ["EVENTS", "Inbox", "NotificationOut", "NotificationService",
           "NotificationPreferenceOut", "NotificationPreferencesOut"]


class NotificationOut(BaseModel):
    id: str
    event: str
    title: str
    body: str
    visit_id: str | None
    # What a tap opens: visit, payment, complaint, checkin or job, with its ID.
    ref_type: str | None = None
    ref_id: str | None = None
    created_at: str
    read: bool


class Inbox(BaseModel):
    unread_count: int
    items: list[NotificationOut]


class NotificationPreferenceOut(BaseModel):
    event: str
    title: str
    description: str
    enabled: bool


class NotificationPreferencesOut(BaseModel):
    items: list[NotificationPreferenceOut]


class NotificationService:
    def __init__(self, db: Session, push: PushSender):
        self._db = db
        self._push = push

    def notify(self, login_id: uuid.UUID, event: str, title: str, body: str = "",
               visit_id: str | None = None, *, ref_type: str | None = None,
               ref_id: str | None = None, dedupe_key: str | None = None
               ) -> Notification | None:
        """Adds to the inbox and pushes to the person's phones. Other modules
        reach this through `app.notifications.emit`.

        Returns None when nothing was sent: the person switched this event off
        (NOTIF-03), or the same `dedupe_key` was sent before."""
        if event not in EVENTS:
            raise ValueError(f"Unknown notification event: {event}")
        if switchable(event) and not self.enabled(login_id, event):
            return None
        if dedupe_key is not None:
            found = self._db.scalar(select(Notification).where(
                Notification.login_id == login_id, Notification.dedupe_key == dedupe_key))
            if found is not None:
                return None
        if visit_id and ref_type is None:
            ref_type, ref_id = "visit", visit_id
        row = Notification(login_id=login_id, event=event, title=title[:120], body=body,
                           visit_id=visit_id, ref_type=ref_type, ref_id=ref_id,
                           dedupe_key=dedupe_key)
        self._db.add(row)
        self._db.commit()
        tokens = list(self._db.scalars(
            select(DeviceToken.token).where(DeviceToken.login_id == login_id)))
        if tokens:
            data = {"event": event}
            if visit_id:
                data["visit_id"] = visit_id
            if ref_type and ref_id and ref_type != "visit":  # a visit is `visit_id`
                data["ref_type"], data["ref_id"] = ref_type, ref_id
            self._push.send(tokens, title, body, data)
        return row

    def push_only(self, login_ids: list[uuid.UUID], title: str, body: str,
                  data: dict[str, str]) -> int:
        """A push with no inbox row (admin alerts keep their own list)."""
        tokens = list(self._db.scalars(
            select(DeviceToken.token).where(DeviceToken.login_id.in_(login_ids))))
        if tokens:
            self._push.send(tokens, title, body, data)
        return len(tokens)

    # --- preferences -------------------------------------------------------

    def enabled(self, login_id: uuid.UUID, event: str) -> bool:
        row = self._db.get(NotificationPreference, (login_id, event))
        return True if row is None else row.enabled

    def preferences(self, login_id: uuid.UUID) -> NotificationPreferencesOut:
        stored = {p.event: p.enabled for p in self._db.scalars(
            select(NotificationPreference).where(NotificationPreference.login_id == login_id))}
        return NotificationPreferencesOut(items=[
            NotificationPreferenceOut(event=e, title=LABELS[e][0], description=LABELS[e][1],
                                      enabled=stored.get(e, True))
            for e in CUSTOMER_EVENTS])

    def set_preferences(self, login_id: uuid.UUID, changes: dict[str, bool]
                        ) -> NotificationPreferencesOut:
        unknown = [e for e in changes if e not in CUSTOMER_EVENTS]
        if unknown:
            raise ApiError("validation_failed", "That notification cannot be switched.", 422,
                           {"event": f"Unknown: {unknown[0]}"})
        for event, enabled in changes.items():
            row = self._db.get(NotificationPreference, (login_id, event))
            if row is None:
                self._db.add(NotificationPreference(login_id=login_id, event=event,
                                                    enabled=enabled))
            else:
                row.enabled, row.updated_at = enabled, utcnow()
        self._db.commit()
        return self.preferences(login_id)

    # --- the inbox ---------------------------------------------------------

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
                            visit_id=r.visit_id, ref_type=r.ref_type, ref_id=r.ref_id,
                            created_at=r.created_at.isoformat(), read=r.read_at is not None)
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
