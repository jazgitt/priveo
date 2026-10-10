"""The tests run on an in-memory SQLite database by default. Set
TEST_DATABASE_URL to run them on PostgreSQL, as CI does. That database is
emptied for every test, so never point it at one that holds real data."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.identity import models  # noqa: F401  (registers the tables)
from app.identity.seed import seed_logins
from app.main import create_app
from app.platform.config import get_settings
from app.platform.db import Base, get_db, make_engine

PASSWORDS = {"customer": "pw-customer1", "crew": "Rav4821$", "admin": "pw-admin1"}
LOGIN_IDS = {"customer": "customer@priveo.test", "crew": "9000000002", "admin": "priveopapa"}


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORDS["admin"])
    monkeypatch.setenv("MOCK_CUSTOMER_PASSWORD", PASSWORDS["customer"])
    monkeypatch.setenv("MOCK_CREW_PASSWORD", PASSWORDS["crew"])
    monkeypatch.setenv("SEED_DEMO_LOGINS", "true")
    monkeypatch.setenv("TOKEN_SECRET", "test-secret-that-is-long-enough-for-hs256")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def engine():
    engine = make_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine):
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def client(settings, engine):
    with Session(engine) as session:
        seed_logins(session, settings)

    def _get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    return TestClient(app)
