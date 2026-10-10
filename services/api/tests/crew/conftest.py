import pytest

import app.crew  # noqa: F401  (registers the crew table)
from app.crew import register
from app.directory.models import Society


@pytest.fixture
def client(client):
    """The shared client, with the crew routes included as `create_app` will."""
    register(client.app)
    return client


@pytest.fixture
def society(db):
    row = Society(name="Green Meadows", sector="Sector 1")
    db.add(row)
    db.commit()
    return row
