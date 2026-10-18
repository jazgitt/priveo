"""Loads the logins that are not created in the app.

The admin `priveopapa` is always seeded (ADM-ACC-05). Its password comes
from the environment and is never in the repository. The two demo logins are
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

ADMIN_LOGIN_ID = "priveopapa"


def _upsert(db: Session, role: str, login_id: str, display_name: str, password: str) -> str:
    login = db.scalar(select(Login).where(Login.login_id == login_id))
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
    # Seeding is also how a locked admin gets back in.
    login.locked = False
    login.failed_attempts = 0
    login.blocked_until = None
    return outcome


DEMO_CUSTOMER = "customer@priveo.test"
DEMO_SOCIETY = "Priveo Demo Society"


def _demo_customer(db: Session) -> None:
    """The demo customer's own record: two vehicles, already reviewed, so the
    demo login opens Home and shows the vehicle switcher."""
    login = db.scalar(select(Login).where(Login.login_id == DEMO_CUSTOMER))
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
        login_id=login.id, first_name="Aarav", last_name="Mehta", email=DEMO_CUSTOMER,
        mobile="9000000001", society_id=society.id, flat="A-101", source="demo",
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
    if settings.admin_password:
        done[ADMIN_LOGIN_ID] = _upsert(
            db, "admin", ADMIN_LOGIN_ID, "Priveo Admin", settings.admin_password)
    else:
        done[ADMIN_LOGIN_ID] = "skipped: no admin password is configured"
    if settings.seed_demo_logins and settings.environment == "prod":
        done["demo logins"] = "skipped: never seeded in prod"
    elif settings.seed_demo_logins:
        demo = [
            ("customer", DEMO_CUSTOMER, "Aarav Mehta", settings.mock_customer_password),
            ("crew", "9000000002", "Ravi Kumar", settings.mock_crew_password),
        ]
        for role, login_id, name, password in demo:
            done[login_id] = (_upsert(db, role, login_id, name, password) if password
                              else "skipped: no password is configured")
        if settings.mock_customer_password:
            _demo_customer(db)
    db.commit()
    return done
