"""A society with crew and subscribed cars, and the app with scheduling wired in."""
from datetime import date, datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.scheduling  # noqa: F401  (registers the tables before they are created)
from app.changes.rules import get_now
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Society
from app.identity.models import Login
from app.identity.seed import seed_logins
from app.main import create_app
from app.platform.db import get_db
from app.scheduling import register
from app.scheduling.models import SchedulingCrew
from tests.test_api import auth, login

SUNDAY = date(2026, 10, 18)  # a week starts on Sunday (ADM-SCH-09)
PINNED_NOW = datetime(2026, 10, 17, 10, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))


class World:
    def __init__(self, db: Session):
        self.db = db
        self.society = Society(name="DLF Meadows")
        db.add(self.society)
        db.flush()
        self.customer_login = db.query(Login).filter_by(role="customer").one()
        self.customer = db.query(Customer).filter_by(login_id=self.customer_login.id).first()
        if self.customer is None:
            self.customer = Customer(
                login_id=self.customer_login.id, first_name="Asha", last_name="Rao",
                email=self.customer_login.login_id, mobile="9876543210", flat="A-101",
                society_id=self.society.id)
            db.add(self.customer)
        self.customer.first_name, self.customer.last_name = "Asha", "Rao"
        self.customer.mobile = "9876543210"
        self.customer.society_id = self.society.id
        # The demo login comes with cars of its own. These tests add theirs.
        for car in db.query(Vehicle).filter_by(customer_id=self.customer.id):
            car.active = False
        db.flush()
        self.crew: list[SchedulingCrew] = []
        self.vehicles: list[Vehicle] = []

    def add_crew(self, login_id=None, role="Member", start=360, end=420,
                 name="Ravi", society_id=None, paired=None) -> SchedulingCrew:
        if login_id is None:
            row = Login(role="crew", login_id=f"90000{len(self.crew) + 10:05d}",
                        display_name=name)
            self.db.add(row)
            self.db.flush()
            login_id = row.id
        member = SchedulingCrew(login_id=login_id, society_id=society_id or self.society.id,
                                role=role, start_minute=start, end_minute=end,
                                paired_member_id=paired)
        self.db.add(member)
        self.db.flush()
        self.crew.append(member)
        return member

    def add_vehicle(self, cutoff=None, interior_day=None, status="Active") -> Vehicle:
        n = len(self.vehicles) + 1
        vehicle = Vehicle(customer_id=self.customer.id, registration=f"MH12AB{n:04d}",
                          make="Hyundai", model="Creta", category="SUV",
                          parking_basement="B2", parking_number=str(n))
        self.db.add(vehicle)
        self.db.flush()
        self.db.add(Subscription(vehicle_id=vehicle.id, monthly_price_rupees=1299,
                                 status=status, first_service_date=date(2026, 9, 1),
                                 cutoff_time=cutoff, interior_day=interior_day))
        self.db.flush()
        self.vehicles.append(vehicle)
        return vehicle


@pytest.fixture
def world(settings, engine):
    with Session(engine) as session:
        seed_logins(session, settings)
    with Session(engine, expire_on_commit=False) as session:
        yield World(session)
        session.commit()


@pytest.fixture
def api(world, engine, monkeypatch):
    world.db.commit()

    def _get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    register(app)
    app.dependency_overrides[get_db] = _get_db
    # The tests plan the week of SUNDAY. Pin the clock to the day before, so the
    # 9 PM change rule does not depend on the date the tests are run on.
    app.dependency_overrides[get_now] = lambda: lambda: PINNED_NOW
    monkeypatch.setattr("app.platform.clock.today_ist", lambda: PINNED_NOW.date())
    return TestClient(app)


@pytest.fixture
def admin(api):
    return auth(login(api, "admin")["access_token"])


@pytest.fixture
def run_week(api, admin, world):
    def _run(**extra):
        r = api.post("/v1/admin/scheduling/run", headers=admin, json={
            "society_id": str(world.society.id), "start_date": SUNDAY.isoformat(), **extra})
        assert r.status_code == 200, r.text
        return r.json()["schedules"][0]
    return _run


__all__ = ["SUNDAY", "World", "time"]
