import logging

import pytest

from app.platform.config import Settings
from app.platform.email import FakeEmailSender, get_email_sender, new_code


@pytest.fixture(autouse=True)
def offline_email(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "")
    monkeypatch.setenv("ENVIRONMENT", "dev")


def test_fake_sender_logs_the_code_and_keeps_it(caplog):
    sender = FakeEmailSender()
    with caplog.at_level(logging.INFO, logger="priveo.email"):
        sender.send_code("a@example.com", "123456", "sign_in_code")
    assert "123456" in caplog.text
    assert sender.sent[0].to == "a@example.com" and sender.sent[0].code == "123456"


def test_fake_sender_welcome_has_no_code():
    sender = FakeEmailSender()
    sender.send_welcome("a@example.com", "Asha")
    assert sender.sent[0].purpose == "welcome" and sender.sent[0].code is None


def test_the_mock_code_is_kept_on_dev_and_random_otherwise():
    fixed = Settings(mock_email_code="246810", environment="dev")
    assert new_code(fixed) == "246810"
    random_code = new_code(Settings(mock_email_code="", environment="dev"))
    assert len(random_code) == 6 and random_code.isdigit()
    # The fixed code is ignored in prod.
    prod = new_code(Settings(mock_email_code="246810", environment="prod"))
    assert len(prod) == 6 and prod.isdigit()


def test_a_sender_is_available():
    assert get_email_sender() is get_email_sender(Settings())


def test_templates_and_the_resend_sender(monkeypatch):
    monkeypatch.setenv("EMAIL_REDIRECT_TO", "")
    import json

    from app.platform import email as mail

    subject, text, body = mail.code_message("123456", "sign_in_code")
    assert "123456" in text and "123456" in body and "verification" in subject
    subject, text, _ = mail.code_message("123456", "email_change_code")
    assert "new Priveo email" in subject and "confirm this email address" in text
    _, text, body = mail.welcome_message("Asha")
    assert "Asha" in text and "code" not in text.lower().split("we will")[0]

    seen = {}

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(request, timeout):
        seen["body"] = json.loads(request.data)
        seen["auth"] = request.get_header("Authorization")
        return Reply()

    monkeypatch.setattr(mail.urllib.request, "urlopen", fake_open)
    sender = get_email_sender(Settings(resend_api_key="re_x", environment="prod"))
    assert isinstance(sender, mail.ResendEmailSender)
    sender.send_code("a@example.com", "123456", "password_reset_code")
    assert seen["auth"] == "Bearer re_x" and seen["body"]["to"] == ["a@example.com"]


def test_the_prod_fake_never_logs_a_code(caplog):
    sender = get_email_sender(Settings(environment="prod"))
    with caplog.at_level(logging.INFO, logger="priveo.email"):
        sender.send_code("a@example.com", "654321", "sign_in_code")
    assert "654321" not in caplog.text


def test_send_welcome_for_a_customer():
    from types import SimpleNamespace

    from app.customers.welcome import send_welcome

    sender = FakeEmailSender()
    customer = SimpleNamespace(id=1, email="a@example.com", first_name="Asha")
    assert send_welcome(None, customer, sender=sender) is True
    assert sender.sent[0].purpose == "welcome"
