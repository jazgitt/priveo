"""Support tests start the app with the support module registered. The
platform will do this in `create_app`; until then the test does it."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.identity.seed import seed_logins
from app.main import create_app
from app.platform.db import get_db
from app.support import register
from app.support.router import get_email_notifier, get_push_notifier
from tests.test_api import auth, login


class RecordingPush:
    def __init__(self):
        self.admin = []
        self.customer = []

    def push_admin(self, title, body):
        self.admin.append((title, body))

    def push_customer(self, login_id, title, body):
        self.customer.append((login_id, title, body))


class RecordingEmail:
    def __init__(self):
        self.sent = []

    def send_admin_alert(self, title, body):
        self.sent.append((title, body))


@pytest.fixture
def client(settings, engine):
    with Session(engine) as session:
        seed_logins(session, settings)

    def _get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    register(app)
    push, email = RecordingPush(), RecordingEmail()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_push_notifier] = lambda: push
    app.dependency_overrides[get_email_notifier] = lambda: email
    c = TestClient(app)
    c.push, c.email = push, email
    return c


@pytest.fixture
def customer(client):
    return auth(login(client, "customer")["access_token"])


@pytest.fixture
def admin(client):
    return auth(login(client, "admin")["access_token"])


@pytest.fixture
def crew(client):
    return auth(login(client, "crew")["access_token"])
