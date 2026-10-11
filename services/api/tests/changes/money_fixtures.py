"""Shared set-up for the changes, billing and addons tests: the app with the
three modules registered, a fixed clock, an in-memory schedule gateway, and one
customer with one Active subscription."""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.addons.models
import app.billing.models
import app.changes.models  # noqa: F401
from app import addons, billing, changes
from app.changes.gateway import InMemoryScheduleChangeGateway, get_schedule_gateway
from app.changes.rules import get_now
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Society
from app.identity.models import Login
from app.identity.seed import seed_logins
from app.identity.service import hash_password
from app.main import create_app
from app.platform.clock import IST
from app.platform.db import get_db
from tests.test_api import auth

EMAIL = "meera@example.com"
PASSWORD = "carwash2026"


class FakeClock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def at(day: int, hour: int = 10, minute: int = 0, month: int = 10) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=IST)


@dataclass
class Money:
    client: TestClient
    db: Session
    clock: FakeClock
    gateway: InMemoryScheduleChangeGateway
    customer: dict  # headers
    admin: dict  # headers
    customer_id: uuid.UUID
    vehicle_id: str
    subscription_id: uuid.UUID

    def add_vehicle(self, *, subscribed: bool, status: str = "Active") -> str:
        v = Vehicle(customer_id=self.customer_id, registration=None, model="Tata Punch")
        self.db.add(v)
        self.db.flush()
        if subscribed:
            self.db.add(Subscription(vehicle_id=v.id, monthly_price_rupees=999,
                                     status=status, first_service_date=date(2026, 10, 1)))
        self.db.commit()
        return str(v.id)

    def subscription(self) -> Subscription:
        self.db.expire_all()
        return self.db.get(Subscription, self.subscription_id)


@pytest.fixture
def money(settings, engine, db) -> Money:
    with Session(engine) as session:
        seed_logins(session, settings)
    login = Login(role="customer", login_id=EMAIL, display_name="Meera Rao",
                  password_hash=hash_password(PASSWORD))
    society = Society(name="DLF Meadows")
    db.add_all([login, society])
    db.flush()
    customer = Customer(login_id=login.id, first_name="Meera", last_name="Rao", email=EMAIL,
                        mobile="9000004321", society_id=society.id, flat="A-101",
                        onboarding_confirmed_at=datetime(2026, 9, 1, tzinfo=IST))
    db.add(customer)
    db.flush()
    vehicle = Vehicle(customer_id=customer.id, registration="HR26DK8337",
                      model="Hyundai Creta", parking_basement="B1", parking_number="223")
    db.add(vehicle)
    db.flush()
    sub = Subscription(vehicle_id=vehicle.id, monthly_price_rupees=1299, status="Active",
                       first_service_date=date(2026, 10, 1), cutoff_time=time(7, 0),
                       interior_day="Friday")
    db.add(sub)
    db.commit()

    def _get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    clock = FakeClock(at(11, 10))
    gateway = InMemoryScheduleChangeGateway()
    app = create_app()
    for module in (changes, billing, addons):
        module.register(app)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_now] = lambda: clock
    app.dependency_overrides[get_schedule_gateway] = lambda: gateway
    client = TestClient(app)

    def token(login_id, password):
        r = client.post("/v1/auth/login", json={"login_id": login_id, "password": password})
        assert r.status_code == 200, r.text
        return auth(r.json()["access_token"])

    return Money(client=client, db=db, clock=clock, gateway=gateway,
                 customer=token(EMAIL, PASSWORD), admin=token("priveopapa", "pw-admin1"),
                 customer_id=customer.id, vehicle_id=str(vehicle.id), subscription_id=sub.id)
