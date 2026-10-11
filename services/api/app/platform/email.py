"""Sending email, behind one small interface.

The API asks an `EmailSender` to send a message and does not care how. Until
Resend is connected (Phase 2, "You arrange"), the fake sender only logs the
message, so a code can be read from the log on `dev`.
"""
import logging
import secrets
from dataclasses import dataclass
from typing import Protocol

from app.platform.config import Settings

log = logging.getLogger("priveo.email")


@dataclass(frozen=True)
class SentEmail:
    to: str
    purpose: str  # "sign_in_code" | "password_reset_code" | "welcome"
    code: str | None = None


class EmailSender(Protocol):
    def send_code(self, to: str, code: str, purpose: str) -> None:
        """Emails a 6-digit code (AUTH-03, AUTH-16)."""
        ...

    def send_welcome(self, to: str, first_name: str) -> None:
        """The welcome email after the admin creates a customer (ADM-CUS-04)."""
        ...


class FakeEmailSender:
    """Logs the message and keeps it in `sent`. Nothing leaves the process."""

    def __init__(self) -> None:
        self.sent: list[SentEmail] = []

    def send_code(self, to: str, code: str, purpose: str) -> None:
        self.sent.append(SentEmail(to, purpose, code))
        log.info("fake email to %s (%s): code %s", to, purpose, code)

    def send_welcome(self, to: str, first_name: str) -> None:
        self.sent.append(SentEmail(to, "welcome"))
        log.info("fake email to %s: welcome %s", to, first_name)


_fake = FakeEmailSender()


def get_email_sender(settings: Settings | None = None) -> EmailSender:
    """The sender in use. Only the fake one exists until Resend is connected."""
    return _fake


def new_code(settings: Settings) -> str:
    """The 6-digit code to send. With MOCK_EMAIL_CODE set on dev it is that
    fixed value, as before; otherwise it is random."""
    fixed = settings.fixed_email_code
    return fixed if fixed is not None else f"{secrets.randbelow(10**6):06d}"
