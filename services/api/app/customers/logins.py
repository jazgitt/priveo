"""A customer's sign-in: the mobile number and a 6-digit MPIN.

The admin never types an MPIN. Every customer starts with the last 6 digits of
their mobile number and must choose their own at the first sign-in."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Customer
from app.identity.models import Login
from app.identity.mpin import default_mpin
from app.identity.service import hash_password
from app.platform.db import utcnow
from app.platform.errors import ApiError


def mobile_in_use(mobile: str) -> ApiError:
    return ApiError("mobile_in_use", "This mobile number already belongs to a customer.", 409,
                    {"mobile": "Already in use."})


def mobile_taken(db: Session, mobile: str, *, except_id: uuid.UUID | None = None) -> bool:
    """Another customer, or another customer sign-in, already has this number."""
    found = select(Customer.id).where(Customer.mobile == mobile)
    if except_id is not None:
        found = found.where(Customer.id != except_id)
    if db.scalar(found) is not None:
        return True
    own = db.scalar(select(Customer.login_id).where(Customer.id == except_id)) if except_id else None
    login = select(Login.id).where(Login.role == "customer", Login.login_id == mobile)
    if own is not None:
        login = login.where(Login.id != own)
    return db.scalar(login) is not None


def give_default_mpin(login: Login, mobile: str) -> None:
    """The first MPIN again: after a reset, or when the mobile number changes
    before the customer has chosen their own."""
    login.password_hash = hash_password(default_mpin(mobile))
    login.password_changed_at = utcnow()
    login.must_change_mpin = True
    login.failed_attempts = 0
    login.blocked_until = None
    login.locked = False


def ensure_login(db: Session, customer: Customer) -> Login:
    """The customer's login, made with the first MPIN when they have none.
    The caller commits."""
    if customer.login_id is not None:
        return db.get(Login, customer.login_id)
    if db.scalar(select(Login.id).where(
            Login.role == "customer", Login.login_id == customer.mobile)) is not None:
        raise mobile_in_use(customer.mobile)
    login = Login(role="customer", login_id=customer.mobile,
                  display_name=f"{customer.first_name} {customer.last_name}".strip())
    give_default_mpin(login, customer.mobile)
    db.add(login)
    db.flush()
    customer.login_id = login.id
    return login
