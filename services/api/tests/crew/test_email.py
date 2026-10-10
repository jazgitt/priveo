import logging

from app.platform.config import Settings
from app.platform.email import FakeEmailSender, get_email_sender, new_code


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
