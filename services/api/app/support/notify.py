"""Where email and push go. Real senders (Resend, FCM) arrive with the
notifications module; until then these Protocols have logging fakes."""
import logging
import uuid
from typing import Protocol

log = logging.getLogger("priveo.support.notify")


class EmailNotifier(Protocol):
    def send_admin_alert(self, title: str, body: str) -> None: ...


class PushNotifier(Protocol):
    def push_admin(self, title: str, body: str) -> None: ...

    def push_customer(self, login_id: uuid.UUID, title: str, body: str, *,
                      event: str | None = None, ref_type: str | None = None,
                      ref_id: str | None = None, dedupe_key: str | None = None) -> None: ...


class LoggingEmailNotifier:
    def send_admin_alert(self, title: str, body: str) -> None:
        log.info("admin alert email: %s | %s", title, body)


class LoggingPushNotifier:
    def push_admin(self, title: str, body: str) -> None:
        log.info("admin push: %s | %s", title, body)

    def push_customer(self, login_id: uuid.UUID, title: str, body: str, **_ref) -> None:
        log.info("customer push to %s: %s | %s", login_id, title, body)
