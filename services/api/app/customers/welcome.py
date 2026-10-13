"""The welcome email after the admin creates a customer (ADM-CUS-04)."""
import logging

from sqlalchemy.orm import Session

from app.customers.models import Customer
from app.platform.config import Settings, get_settings
from app.platform.email import EmailSender, EmailSendError, get_email_sender

log = logging.getLogger("priveo.email")


def send_welcome(db: Session, customer: Customer, *, settings: Settings | None = None,
                 sender: EmailSender | None = None) -> bool:
    """Emails the customer that the account is ready. It holds no code and no
    password. A failure never blocks creating the customer: it returns False
    and the admin can try again."""
    sender = sender or get_email_sender(settings or get_settings())
    try:
        sender.send_welcome(customer.email, customer.first_name)
    except EmailSendError:
        log.warning("welcome email for customer %s was not sent", customer.id)
        return False
    return True
