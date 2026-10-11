"""Shared set-up for the visits and media tests. Every test makes its own rows."""
from dataclasses import dataclass
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.media.models
import app.scheduling.models
import app.visits.models  # noqa: F401
from app import media, visits
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Society
from app.identity.models import Login
from app.identity.service import hash_password
from app.main import create_app
from app.media.store import LocalObjectStore, get_object_store
from app.platform.db import get_db
from app.scheduling.models import Job, Schedule, SchedulingCrew, Visit

PASSWORD = "Crew-pass-1"
DAY = date(2026, 11, 7)


@dataclass
class World:
    society: Society
    vehicles: list[Vehicle]


@pytest.fixture
def world(db: Session) -> World:
    society = Society(name="Green Meadows")
    db.add(society)
    db.flush()
    owner = Login(role="customer", login_id="owner@priveo.test", display_name="Secret Name")
    db.add(owner)
    db.flush()
    customer = Customer(login_id=owner.id, first_name="Secret", last_name="Name",
                        email="owner@priveo.test", mobile="9123456789",
                        society_id=society.id, flat="A-101")
    db.add(customer)
    db.flush()
    vehicles = []
    for registration, model, number, cutoff in (("MH12AB1234", "Creta", "14", time(7, 0)),
                                                ("MH12CD5678", "Swift", "15", time(7, 30))):
        v = Vehicle(customer_id=customer.id, registration=registration, make="Brand",
                    model=model, category="SUV", parking_basement="B2", parking_number=number)
        db.add(v)
        db.flush()
        db.add(Subscription(vehicle_id=v.id, monthly_price_rupees=999, first_service_date=DAY,
                            cutoff_time=cutoff))
        vehicles.append(v)
    db.commit()
    return World(society=society, vehicles=vehicles)


@pytest.fixture
def make_crew(db: Session, world: World):
    def make(mobile: str, name: str, role: str = "Member",
             member: SchedulingCrew | None = None,
             society: Society | None = None) -> SchedulingCrew:
        login = Login(role="crew", login_id=mobile, display_name=name,
                      password_hash=hash_password(PASSWORD))
        db.add(login)
        db.flush()
        crew = SchedulingCrew(login_id=login.id, society_id=(society or world.society).id,
                              role=role, paired_member_id=member.id if member else None)
        db.add(crew)
        db.commit()
        return crew

    return make


@pytest.fixture
def store(tmp_path) -> LocalObjectStore:
    return LocalObjectStore(root=tmp_path / "media", secret="test-signing-secret")


@pytest.fixture
def crew_client(settings, engine, store) -> TestClient:
    def _get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    visits.register(app)
    media.register(app)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_object_store] = lambda: store
    return TestClient(app)


@pytest.fixture
def signin(crew_client: TestClient, db: Session):
    def go(member: SchedulingCrew) -> dict[str, str]:
        login = db.get(Login, member.login_id)
        r = crew_client.post("/v1/auth/login",
                             json={"login_id": login.login_id, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return go


@pytest.fixture
def new_visit(db: Session, world: World):
    """A visit with a job for each service, on a schedule of the society."""

    def make(services=("Cleaning-External",), vehicle=0, assigned: SchedulingCrew | None = None,
             day: date = DAY, status: str = "Frozen", society: Society | None = None):
        society = society or world.society
        schedule = db.scalar(select(Schedule).where(
            Schedule.society_id == society.id, Schedule.status == status,
            Schedule.start_date == DAY - timedelta(days=7 if status == "Draft" else 0)))
        if schedule is None:
            schedule = Schedule(
                society_id=society.id, status=status,
                start_date=DAY - timedelta(days=7 if status == "Draft" else 0),
                end_date=DAY + timedelta(days=6))
            db.add(schedule)
            db.flush()
        visit = Visit(schedule_id=schedule.id, vehicle_id=world.vehicles[vehicle].id, date=day)
        db.add(visit)
        db.flush()
        jobs = []
        for service in sorted(services):
            job = Job(visit_id=visit.id, service=service, duration_minutes=20,
                      crew_id=assigned.id if assigned else None, start_minute=420,
                      finish_by_minute=450)
            db.add(job)
            jobs.append(job)
        db.commit()
        return visit, jobs

    return make


def upload_file(client: TestClient, headers, job_id: str, *, kind="photo", stage="Before",
                content_type=None, data: bytes = b"x" * 2048, purpose="proof") -> str:
    """Request, send and confirm one upload. Returns its ID."""
    content_type = content_type or ("image/jpeg" if kind == "photo" else "video/mp4")
    r = client.post("/v1/media/uploads", headers=headers, json={
        "purpose": purpose, "job_id": job_id, "kind": kind, "stage": stage,
        "content_type": content_type, "size_bytes": len(data)})
    assert r.status_code == 201, r.text
    ticket = r.json()
    sent = client.put(ticket["upload_url"], content=data, headers=ticket["headers"])
    assert sent.status_code == 204, sent.text
    done = client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=headers)
    assert done.status_code == 200, done.text
    return ticket["id"]
