"""The support module's `PushNotifier`, backed by the real inbox.

Support asks for "a push to this customer" or "a push to the admin". Here the
customer one becomes an inbox message plus a push, following the customer's
switches (CMP-04, CHK-01), and the admin one a push to the admin phones."""
import logging
import uuid

from sqlalchemy.orm import Session

from app.notifications import emit
from app.notifications.push import get_default_sender
from app.notifications.service import NotificationService

log = logging.getLogger("priveo.notifications")

# Support names the message by its title when it gives no event.
_EVENT_BY_TITLE = {
    "Complaint update": "complaint_update",
    "Monthly check-in": "monthly_check_in",
}


class SupportNotifier:
    def __init__(self, db: Session):
        self._db = db

    def push_admin(self, title: str, body: str) -> None:
        emit.admin_push(self._db, title, body)

    def push_customer(self, login_id: uuid.UUID, title: str, body: str, *,
                      event: str | None = None, ref_type: str | None = None,
                      ref_id: str | None = None, dedupe_key: str | None = None) -> None:
        event = event or _EVENT_BY_TITLE.get(title)
        if event is None:
            log.warning("support push without an event was dropped: %s", title)
            return
        try:
            NotificationService(self._db, get_default_sender()).notify(
                login_id, event, title, body, ref_type=ref_type, ref_id=ref_id,
                dedupe_key=dedupe_key)
        except Exception:
            log.exception("customer notification %s failed", event)
            self._db.rollback()
