from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.customers.models import Customer
from app.identity.models import Login
from app.identity.service import _password_matches
from scripts import seed_shared_test_data as shared


@pytest.fixture(autouse=True)
def clean_fixture_manifest(engine):
    # This metadata table is outside application ORM metadata and its test reset.
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS shared_test_data_manifest"))
    yield
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS shared_test_data_manifest"))


def test_additive_seed_all_scenarios_preserves_admin_and_repeat_edits(client, engine):
    with Session(engine) as db:
        admin = db.scalar(select(Login).where(Login.role == "admin"))
        admin_id, admin_hash = admin.id, admin.password_hash
        before = db.scalar(select(func.count()).select_from(Customer))
    result = shared.seed_additive(engine, date(2026, 10, 13), "FixturePassword123!")
    assert len(result["added"]) == len(shared.catalogue()) == 39
    with Session(engine) as db:
        login = db.get(Login, shared.identity("C01", "customer-login"))
        login.display_name = "Manual edit"
        db.commit()
    repeated = shared.seed_additive(engine, date(2026, 10, 14), "DifferentPassword123!")
    assert repeated["added"] == []
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Customer)) == before + 39
        admin = db.get(Login, admin_id)
        assert admin.password_hash == admin_hash
        login = db.get(Login, shared.identity("C01", "customer-login"))
        assert login.display_name == "Manual edit"
        assert _password_matches(login.password_hash, "FixturePassword123!")


def test_additive_seed_rolls_back_on_late_failure(client, engine, monkeypatch):
    builder = shared._seed_scenario

    def fail_later(db, config, day, password_hash):
        if config["id"] == "C03":
            raise ValueError("Simulated seed failure")
        return builder(db, config, day, password_hash)

    monkeypatch.setattr(shared, "_seed_scenario", fail_later)
    with pytest.raises(ValueError, match="Simulated seed failure"):
        shared.seed_additive(engine, date(2026, 10, 13), "FixturePassword123!")
    with Session(engine) as db:
        assert db.get(Login, shared.identity("C01", "customer-login")) is None
        assert db.get(Login, shared.identity("C02", "customer-login")) is None
