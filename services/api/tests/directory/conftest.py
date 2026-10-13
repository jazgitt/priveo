"""Directory tests start the app with the directory module registered. The
coordinator does this in `create_app`; until then the test does it."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.directory import lookup, register
from app.identity.seed import seed_logins
from app.main import create_app
from app.platform.db import get_db
from tests.test_api import auth, login


@pytest.fixture(autouse=True)
def _fresh_settings_cache():
    lookup.invalidate()
    yield
    lookup.invalidate()


@pytest.fixture
def client(settings, engine):
    with Session(engine) as session:
        seed_logins(session, settings)

    def _get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    register(app)
    app.dependency_overrides[get_db] = _get_db
    return TestClient(app)


@pytest.fixture
def admin(client):
    return auth(login(client, "admin")["access_token"])


@pytest.fixture
def customer(client):
    return auth(login(client, "customer")["access_token"])


@pytest.fixture
def crew(client):
    return auth(login(client, "crew")["access_token"])
