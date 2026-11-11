"""Loads the logins that are not created in the app.

The admin is seeded (ADM-ACC-05) under the ID in ADMIN_LOGIN_ID. Its ID and
password come from the environment and are never in the repository. The two demo logins are
for the dev environment only, until the admin can create customers and crew.
"""
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Society
from app.identity.models import Login
from app.identity.service import _password_matches, hash_password
from app.platform.clock import today_ist
from app.platform.config import Settings
from app.platform.db import utcnow


def _upsert(db: Session, role: str, login_id: str, display_name: str, password: str) -> str:
    login = db.scalar(select(Login).where(Login.login_id == login_id, Login.role == role))
    if login is None:
        login = Login(role=role, login_id=login_id, display_name=display_name)
        db.add(login)
        outcome = "created"
    else:
        outcome = "kept"
    if not _password_matches(login.password_hash, password):
        login.password_hash = hash_password(password)
        login.password_changed_at = utcnow()
        outcome = "created" if outcome == "created" else "password set"
    # A demo customer signs in at once, without choosing a new MPIN.
    login.must_change_mpin = False
    # Seeding is also how a locked admin gets back in.
    login.locked = False
    login.failed_attempts = 0
    login.blocked_until = None
    return outcome


def _rename_single_admin(db: Session, admin_id: str) -> None:
    """When the configured ID is new and there is exactly one admin under another
    ID, rename that row (keeps its password, sessions and audit history) instead
    of creating a second admin."""
    admins = list(db.scalars(select(Login).where(Login.role == "admin")))
    if len(admins) == 1 and admins[0].login_id != admin_id:
        admins[0].login_id = admin_id
        db.flush()


# The demo customer signs in with this mobile number (it was customer@priveo.test
# before customers signed in with their mobile number).
DEMO_CUSTOMER = "9000000001"
_OLD_DEMO_CUSTOMER = "customer@priveo.test"
DEMO_SOCIETY = "Priveo Demo Society"


def _demo_customer(db: Session) -> None:
    """The demo customer's own record: two vehicles, already reviewed, so the
    demo login opens Home and shows the vehicle switcher."""
    login = db.scalar(select(Login).where(
        Login.login_id == DEMO_CUSTOMER, Login.role == "customer"))
    db.flush()
    if db.scalar(select(Customer).where(Customer.login_id == login.id)) is not None:
        return
    society = db.scalar(select(Society).where(Society.name == DEMO_SOCIETY))
    if society is None:
        society = Society(name=DEMO_SOCIETY)
        db.add(society)
        db.flush()
    now = utcnow()
    customer = Customer(
        login_id=login.id, first_name="Aarav", last_name="Mehta", email=_OLD_DEMO_CUSTOMER,
        mobile=DEMO_CUSTOMER, society_id=society.id, flat="A-101", source="demo",
        terms_accepted_at=now, onboarding_confirmed_at=now)
    db.add(customer)
    db.flush()
    cars = [("MH12AB1234", "Hyundai Creta", "14", 1299, time(7, 0), "Friday"),
            ("MH12CD5678", "Maruti Swift", "15", 999, time(7, 30), None)]
    for registration, model, parking, price, cutoff, day in cars:
        vehicle = Vehicle(customer_id=customer.id, registration=registration, model=model,
                          parking_basement="B2", parking_number=parking,
                          source_ref=f"demo:{registration}")
        db.add(vehicle)
        db.flush()
        db.add(Subscription(vehicle_id=vehicle.id, monthly_price_rupees=price,
                            status="Active", first_service_date=today_ist(),
                            cutoff_time=cutoff, interior_day=day))


def seed_logins(db: Session, settings: Settings) -> dict[str, str]:
    """Returns what happened to each login ID. Safe to run again."""
    done: dict[str, str] = {}
    admin_id = settings.admin_login_id.strip()
    if not admin_id:
        done["admin"] = "skipped: no ADMIN_LOGIN_ID is configured"
    elif not settings.admin_password:
        done[admin_id] = "skipped: no admin password is configured"
    else:
        _rename_single_admin(db, admin_id)
        done[admin_id] = _upsert(db, "admin", admin_id, "Priveo Admin", settings.admin_password)
    if settings.seed_demo_logins and settings.environment == "prod":
        done["demo logins"] = "skipped: never seeded in prod"
    elif settings.seed_demo_logins:
        demo = [
            ("customer", DEMO_CUSTOMER, "Aarav Mehta", settings.mock_customer_password),
            ("crew", "9000000002", "Ravi Kumar", settings.mock_crew_password),
        ]
        # An earlier demo customer signed in with the email: move it to the mobile number.
        old = db.scalar(select(Login).where(
            Login.login_id == _OLD_DEMO_CUSTOMER, Login.role == "customer"))
        if old is not None and db.scalar(select(Login.id).where(
                Login.login_id == DEMO_CUSTOMER, Login.role == "customer")) is None:
            old.login_id = DEMO_CUSTOMER
        for role, login_id, name, password in demo:
            done[login_id] = (_upsert(db, role, login_id, name, password) if password
                              else "skipped: no password is configured")
        if settings.mock_customer_password:
            _demo_customer(db)
    db.commit()
    return done
