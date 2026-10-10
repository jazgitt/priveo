"""The customer reads, run on a copy of the app that has the slice registered
(app/main.py is not changed by this slice) and an in-memory visit repository."""
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.customer_reads as customer_reads
import app.notifications as notifications
from app.customer_reads.deps import get_visit_read_repository
from app.customer_reads.repository import (
    InMemoryVisitReadRepository,
    Job,
    ProofItem,
    Visit,
)
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Society
from app.identity.models import Login
from app.identity.seed import seed_logins
from app.identity.service import hash_password
from app.main import create_app
from app.platform.db import get_db
from tests.test_api import auth

PASSWORD = "carwash2026"


def add_customer(db, email: str, vehicles: list[tuple[str, str, bool]], society="DLF Meadows"):
    """Adds a customer. Each vehicle is (registration, model, subscribed).
    Returns the vehicle IDs as strings."""
    login = Login(role="customer", login_id=email, display_name="Asha",
                  password_hash=hash_password(PASSWORD))
    soc = db.query(Society).filter_by(name=society).first() or Society(name=society)
    db.add_all([login, soc])
    db.flush()
    customer = Customer(login_id=login.id, first_name="Asha", last_name="Rao", email=email,
                        mobile="9000000001", society_id=soc.id, flat="A-101",
                        onboarding_confirmed_at=None)
    db.add(customer)
    db.flush()
    ids = []
    for index, (registration, model, subscribed) in enumerate(vehicles):
        v = Vehicle(customer_id=customer.id, registration=registration, make="Hyundai",
                    model=model, variant="SX", category="SUV", parking_basement="B2",
                    parking_number=str(14 + index), source_ref=f"{email}:{index}")
        db.add(v)
        db.flush()
        if subscribed:
            db.add(Subscription(vehicle_id=v.id, monthly_price_rupees=1299,
                                first_service_date=date(2026, 9, 14), cutoff_time=time(7, 0),
                                interior_day="Friday"))
        ids.append(str(v.id))
    db.commit()
    return ids


@pytest.fixture
def repo():
    return InMemoryVisitReadRepository()


@pytest.fixture
def api(settings, engine, repo):
    with Session(engine) as session:
        seed_logins(session, settings)

    def _get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    customer_reads.register(app)
    notifications.register(app)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_visit_read_repository] = lambda: repo
    return TestClient(app)


@pytest.fixture
def headers_for(api):
    def _headers(email: str):
        r = api.post("/v1/auth/login", json={"login_id": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return auth(r.json()["access_token"])

    return _headers


@pytest.fixture
def asha(db, repo, headers_for):
    """Two cars with a subscription and visits in Nov 2026."""
    ids = add_customer(db, "asha@example.com",
                       [("HR26DK8337", "Creta", True), ("DL3CAB1234", "Swift", True)])
    repo.visit_rows.extend([
        Visit("v-1", ids[0], date(2026, 11, 2), "Completed"),
        Visit("v-2", ids[0], date(2026, 11, 3), "Skipped"),
        Visit("v-3", ids[0], date(2026, 11, 20), "Scheduled"),
        Visit("v-4", ids[1], date(2026, 11, 21), "Scheduled"),
        Visit("v-5", ids[0], date(2026, 12, 1), "Scheduled"),
    ])
    repo.job_rows.extend([
        Job("j-1", "v-1", "Cleaning-External", "Done",
            [ProofItem("photo", "https://media.test/a.jpg"),
             ProofItem("photo", "https://media.test/b.jpg"),
             ProofItem("video", "https://media.test/c.mp4")]),
        Job("j-2", "v-1", "Cleaning-Internal", "Done", [ProofItem("photo", "https://m/d.jpg")]),
        Job("j-3", "v-3", "Cleaning-External", "Pending"),
    ])
    return {"headers": headers_for("asha@example.com"), "vehicles": ids}
