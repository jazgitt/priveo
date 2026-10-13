"""Sending email, behind one small interface.

The API asks an `EmailSender` to send a message and does not care how. With
`RESEND_API_KEY` set the Resend HTTP API sends it. Without it the fake sender
only logs the message, so a code can be read from the log on `dev`. A code is
never logged when `ENVIRONMENT=prod`.
"""
import html
import json
import logging
import secrets
import urllib.error
import urllib.request
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


class EmailSendError(Exception):
    """The provider did not accept the message."""


class FakeEmailSender:
    """Keeps the message in `sent`. Nothing leaves the process. The code is
    logged only when `log_codes` is true (dev), never in prod."""

    def __init__(self, log_codes: bool = True) -> None:
        self.sent: list[SentEmail] = []
        self._log_codes = log_codes

    def send_code(self, to: str, code: str, purpose: str) -> None:
        self.sent.append(SentEmail(to, purpose, code))
        if self._log_codes:
            log.info("fake email to %s (%s): code %s", to, purpose, code)
        else:
            log.info("fake email to %s (%s)", to, purpose)

    def send_welcome(self, to: str, first_name: str) -> None:
        self.sent.append(SentEmail(to, "welcome"))
        log.info("fake email to %s: welcome %s", to, first_name)


# --- Templates (plain text and simple HTML) ---

_SIGN_OFF = "The Priveo team"


def code_message(code: str, purpose: str) -> tuple[str, str, str]:
    """(subject, text, html) for a verification or password reset code
    (AUTH-03, AUTH-05, AUTH-16). The code is valid for 10 minutes."""
    if purpose == "password_reset_code":
        subject = "Your Priveo password reset code"
        lead = "Use this code to set a new password for your Priveo account."
    elif purpose == "email_change_code":
        subject = "Confirm your new Priveo email"
        lead = "Use this code to confirm this email address for your Priveo account."
    else:
        subject = "Your Priveo verification code"
        lead = "Use this code to verify your email and sign in to Priveo."
    tail = ("The code is valid for 10 minutes. If you did not ask for it, "
            "you can ignore this email.")
    text = f"{lead}\n\nYour code: {code}\n\n{tail}\n\n{_SIGN_OFF}\n"
    body = (f"<p>{lead}</p>"
            f"<p style=\"font-size:28px;letter-spacing:6px;font-weight:bold\">{code}</p>"
            f"<p>{tail}</p><p>{_SIGN_OFF}</p>")
    return subject, text, body


def welcome_message(first_name: str) -> tuple[str, str, str]:
    """(subject, text, html) for the welcome email (ADM-CUS-04). It carries no
    code and no password."""
    name = first_name.strip() or "there"
    subject = "Welcome to Priveo"
    lines = [f"Hello {name},", "Your Priveo account is ready.",
             "Open the Priveo app and sign in with this email address. "
             "We will send you a code to verify it, and you then set your password.",
             _SIGN_OFF]
    text = "\n\n".join(lines) + "\n"
    body = "".join(f"<p>{html.escape(line)}</p>" for line in lines)
    return subject, text, body


class ResendEmailSender:
    """Sends through the Resend HTTP API (https://resend.com/docs/api-reference/emails/send-email)."""

    URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, sender: str, timeout: float = 10.0) -> None:
        self._key = api_key
        self._from = sender
        self._timeout = timeout

    def _send(self, to: str, message: tuple[str, str, str], *, key: str | None = None) -> None:
        subject, text, body = message
        payload = json.dumps({"from": self._from, "to": [to], "subject": subject,
                              "text": text, "html": body}).encode()
        request = urllib.request.Request(
            self.URL, data=payload, method="POST",
            headers={"Authorization": f"Bearer {self._key}",
                     "Content-Type": "application/json",
                     "User-Agent": "priveo-api/1"})
        if key:
            request.add_header("Idempotency-Key", key)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout):
                pass
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            # The message and address are not logged: they may hold a code.
            log.warning("email send failed: %s", type(exc).__name__)
            raise EmailSendError("The email could not be sent.") from exc

    def send_code(self, to: str, code: str, purpose: str) -> None:
        self._send(to, code_message(code, purpose))

    def send_welcome(self, to: str, first_name: str) -> None:
        self._send(to, welcome_message(first_name))

    def send_alert(self, to: str, title: str, body: str, key: str) -> None:
        self._send(to, (title, body, f"<p>{html.escape(body)}</p>"), key=key)


_fake = FakeEmailSender()
_fake_prod = FakeEmailSender(log_codes=False)


def email_connected(settings: Settings | None) -> bool:
    """True when messages can really be delivered. In prod without a Resend
    key nothing can be, and a code must not be made."""
    return settings is None or settings.environment != "prod" or bool(
        settings.resend_api_key.strip())


def get_email_sender(settings: Settings | None = None) -> EmailSender:
    """Resend when `RESEND_API_KEY` is set, otherwise the fake sender."""
    if settings is not None and settings.resend_api_key.strip():
        return ResendEmailSender(settings.resend_api_key.strip(), settings.email_from)
    return _fake_prod if settings is not None and settings.environment == "prod" else _fake


def new_code(settings: Settings) -> str:
    """The 6-digit code to send. With MOCK_EMAIL_CODE set on dev it is that
    fixed value, as before; otherwise it is random."""
    fixed = settings.fixed_email_code
    return fixed if fixed is not None else f"{secrets.randbelow(10**6):06d}"
