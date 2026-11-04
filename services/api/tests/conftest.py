"""The tests run on an in-memory SQLite database by default. Set
TEST_DATABASE_URL to run them on PostgreSQL, as CI does. That database is
emptied for every test, so never point it at one that holds real data."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.identity.seed import seed_logins
from app.main import create_app
from app.platform.config import get_settings
from app.platform.db import Base, get_db, make_engine

# The demo customer's MPIN is 6 digits; crew and admin have passwords.
PASSWORDS = {"customer": "483920", "crew": "Rav4821$", "admin": "pw-admin1"}
LOGIN_IDS = {"customer": "9000000001", "crew": "9000000002", "admin": "priveopapa"}


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORDS["admin"])
    monkeypatch.setenv("MOCK_CUSTOMER_PASSWORD", PASSWORDS["customer"])
    monkeypatch.setenv("MOCK_CREW_PASSWORD", PASSWORDS["crew"])
    monkeypatch.setenv("SEED_DEMO_LOGINS", "true")
    monkeypatch.setenv("MOCK_EMAIL_CODE", "246810")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    # Never deliver real email when tests inherit a developer's provider config.
    monkeypatch.setenv("RESEND_API_KEY", "")
    monkeypatch.setenv("EMAIL_REDIRECT_TO", "")
    monkeypatch.setenv("TOKEN_SECRET", "test-secret-that-is-long-enough-for-hs256")
    # Tokens are checked against the wall clock, not the tests' fake clocks. With the default of 15
    # minutes, a machine that sleeps or stalls for 15 minutes in the middle of a test (the nightly
    # run on a laptop) turns the next request into a 401 and the test fails for no reason in the
    # code. A test of expiry sets its own value.
    monkeypatch.setenv("ACCESS_TOKEN_MINUTES", "720")
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
