"""Fixture integrity/reset tests; never use the application DATABASE_URL."""

import importlib.util
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.billing.models import Invoice, Payment
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Society, SystemSetting
from app.identity.models import AuthSession, Login
from app.identity.service import _password_matches
from app.main import create_app
from app.notifications.models import NotificationPreference
from app.platform.clock import today_ist
from app.platform.db import get_db
from app.scheduling.models import Job, SchedulingCrew
from app.support.models import AdminAlert, Complaint
from scripts.test_data import (
    ROOT,
    catalogue,
    fresh_start,
    identity,
    initialize,
    main,
    manifest,
    open_database,
    refresh,
    verify_database,
)

DAY = date(2026, 10, 13)


@pytest.fixture
def fixture_database(tmp_path):
    engine = open_database(tmp_path / "manual.sqlite3")
    initialize(engine, "FixturePassword123!", "AdminPassword123!")
    yield engine
    engine.dispose()


def test_all_scenarios_are_relationally_valid_and_have_one_admin(fixture_database):
    result = refresh(
        fixture_database, [item["id"] for item in catalogue()], DAY, "FixturePassword123!"
    )
    assert len(result["scenarios"]) == len(catalogue())
    with Session(fixture_database) as db:
        assert db.execute(text("PRAGMA foreign_key_check")).all() == []
        assert db.scalar(select(func.count()).select_from(Login).where(Login.role == "admin")) == 1
        assert db.scalar(select(func.count()).select_from(Customer)) == len(catalogue())
        # More-than-four vehicle cases really have five.
        for scenario in ["C13", "C14", "C15", "C16"]:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Vehicle)
                    .where(Vehicle.customer_id == identity(scenario, "customer"))
                )
                == 5
            )
        statuses = list(
            db.scalars(
                select(Subscription.status)
                .join(Vehicle)
                .where(Vehicle.customer_id == identity("C14", "customer"))
            )
        )
        assert statuses.count("Active") == 2
        assert statuses.count("Inactive") == 3
        assert set(
            db.scalars(
                select(Payment.status).where(Payment.customer_id == identity("C08", "customer"))
            )
        ) == {"Due", "Initiated", "Received", "Over due"}
        assert (
            db.scalar(
                select(func.count())
                .select_from(Subscription)
                .join(Vehicle)
                .where(Vehicle.customer_id == identity("C08", "customer"))
            )
            == 0
        )
        assert all(
            db.scalars(
                select(AddonBooking.standalone).where(
                    AddonBooking.customer_id == identity("C08", "customer")
                )
            )
        )
        assert all(
            payment.status == "Received"
            for payment in db.scalars(
                select(Payment).join(Invoice, Invoice.payment_id == Payment.id)
            )
        )
        assert (
            db.get(
                Invoice, identity("C03", f"invoice-{identity('C03', 'payment-addon-0')}")
            ).tax_details["rate_percent"]
            == 18
        )
        trainee = db.get(SchedulingCrew, identity("R01", "crew-2"))
        assert trainee.paired_member_id == identity("R01", "crew-1")
        assert not list(db.scalars(select(Job).where(Job.crew_id == trainee.id)))


def test_partial_reset_removes_test_actions_and_preserves_other_scenario_and_admin(
    fixture_database,
):
    refresh(fixture_database, ["C07", "C12"], DAY, "FixturePassword123!")
    with Session(fixture_database) as db:
        db.get(Vehicle, identity("C07", "vehicle-0")).model = "Changed by tester"
        db.get(Vehicle, identity("C12", "vehicle-0")).model = "Keep this change"
        admin = db.get(Login, identity("shared", "admin"))
        admin.locked = True
        admin.failed_attempts = 3
        original_admin_hash = admin.password_hash
        db.get(SystemSetting, "schedule.auto_enabled").value = "0"
        extra = Complaint(
            number=999999,
            customer_id=identity("C07", "customer"),
            category="Other",
            description="Created manually",
            photo_keys=[],
        )
        db.add(extra)
        db.flush()
        extra_id = extra.id
        db.add(
            AdminAlert(
                kind="complaint",
                title="Manual test action alert",
                ref_type="complaint",
                ref_id=str(extra_id),
            )
        )
        db.add(
            AuthSession(
                login_id=identity("C07", "customer-login"), channel="mobile", refresh_hash="a" * 64
            )
        )
        db.add(
            NotificationPreference(
                login_id=identity("C07", "customer-login"), event="service_completed", enabled=False
            )
        )
        db.commit()
    before = {item["id"]: item for item in manifest(fixture_database)["scenarios"]}
    after = refresh(fixture_database, ["C07"], DAY, "DifferentPassword123!")
    assert {item["id"]: item for item in after["scenarios"]}["C12"] == before["C12"]
    with Session(fixture_database) as db:
        assert db.get(Vehicle, identity("C07", "vehicle-0")).model == "Creta"
        assert db.get(Vehicle, identity("C12", "vehicle-0")).model == "Keep this change"
        assert db.get(Complaint, extra_id) is None
        assert not list(db.scalars(select(AdminAlert).where(AdminAlert.ref_id == str(extra_id))))
        assert not list(db.scalars(select(AuthSession)))
        assert not list(
            db.scalars(
                select(NotificationPreference).where(
                    NotificationPreference.login_id == identity("C07", "customer-login")
                )
            )
        )
        admin = db.get(Login, identity("shared", "admin"))
        assert admin.password_hash == original_admin_hash
        assert admin.locked and admin.failed_attempts == 3
        assert _password_matches(
            db.get(Login, identity("C07", "customer-login")).password_hash, "DifferentPassword123!"
        )


def test_refresh_is_repeatable_and_supports_relative_dates(fixture_database):
    first = refresh(fixture_database, ["C07", "R01"], DAY, "FixturePassword123!")
    second = refresh(fixture_database, ["C07", "R01"], DAY, "FixturePassword123!")
    assert first == second
    later = refresh(fixture_database, ["C07"], date(2026, 10, 20), "FixturePassword123!")
    assert later["scenarios"][0]["as_of"] == "2026-10-20"
    assert later["scenarios"][1]["as_of"] == "2026-10-13"


def test_rejects_unmarked_existing_application_database(tmp_path):
    engine = open_database(tmp_path / "application.sqlite3")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE real_records (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO real_records VALUES (1)"))
    with pytest.raises(ValueError, match="not marked"):
        initialize(engine, "password", "admin-password")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM real_records")) == 1
    engine.dispose()


def test_validation_happens_before_any_reset(fixture_database):
    refresh(fixture_database, ["C01"], DAY, "FixturePassword123!")
    before = manifest(fixture_database)
    with pytest.raises(ValueError, match="Unknown scenarios"):
        refresh(fixture_database, ["C01", "not-a-scenario"], DAY, "FixturePassword123!")
    with pytest.raises(ValueError, match="TEST_DATA_PASSWORD"):
        refresh(fixture_database, ["C01"], DAY, "")
    assert manifest(fixture_database) == before
    with Session(fixture_database) as db:
        assert db.get(Customer, identity("C01", "customer")) is not None


def test_full_fresh_start_resets_settings_and_preserves_admin_password(tmp_path):
    path = tmp_path / "fresh.sqlite3"
    engine = open_database(path)
    initialize(engine, "FixturePassword123!", "AdminPassword123!")
    refresh(engine, ["C01"], DAY, "FixturePassword123!")
    with Session(engine) as db:
        admin_hash = db.get(Login, identity("shared", "admin")).password_hash
        db.get(Login, identity("shared", "admin")).locked = True
        db.get(SystemSetting, "schedule.auto_enabled").value = "1"
        db.add(Society(name="Added manually during testing"))
        db.commit()
    engine.dispose()
    data = fresh_start(path, DAY, "FixturePassword123!")
    assert len(data["scenarios"]) == len(catalogue())
    engine = open_database(path)
    with Session(engine) as db:
        assert db.get(SystemSetting, "schedule.auto_enabled").value == "0"
        admin = db.get(Login, identity("shared", "admin"))
        assert admin.password_hash == admin_hash and not admin.locked
        assert (
            db.scalar(select(Society).where(Society.name == "Added manually during testing"))
            is None
        )
    engine.dispose()


def test_reset_rolls_back_if_seeding_fails(fixture_database, monkeypatch):
    refresh(fixture_database, ["C01", "C07"], DAY, "FixturePassword123!")
    before = manifest(fixture_database)

    def fail(*_args):
        raise RuntimeError("Injected seed failure")

    monkeypatch.setattr("scripts.test_data._seed_scenario", fail)
    with pytest.raises(RuntimeError, match="Injected seed failure"):
        refresh(fixture_database, ["C01", "C07"], DAY, "FixturePassword123!")
    assert manifest(fixture_database) == before
    with Session(fixture_database) as db:
        assert db.get(Customer, identity("C01", "customer")) is not None
    verify_database(fixture_database)


def test_every_fixture_is_readable_through_real_role_routes(fixture_database, settings):
    data = refresh(
        fixture_database, [item["id"] for item in catalogue()], today_ist(), "FixturePassword123!"
    )
    app = create_app()

    def database():
        with Session(fixture_database) as db:
            yield db

    app.dependency_overrides[get_db] = database
    spec = importlib.util.spec_from_file_location(
        "fixture_api_smoke", ROOT / "tools/test-data/api_smoke.py"
    )
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    with TestClient(app, base_url="https://testserver") as client:

        def call(path, body, token):
            headers = {"Authorization": "Bearer " + token} if token else {}
            response = (
                client.post(path, json=body, headers=headers)
                if body is not None
                else client.get(path, headers=headers)
            )
            return response.status_code, response.json()

        result = smoke.run_suite(call, data, "FixturePassword123!", "AdminPassword123!")
        assert len(result) == len(catalogue())
        # The Admin portal uses cookies; exercise that distinct auth path too.
        response = client.post(
            "/v1/web/login", json={"login_id": "priveopapa", "password": "AdminPassword123!"}
        )
        assert response.status_code == 200
        assert client.get("/v1/web/me").json()["role"] == "admin"
        assert client.get("/v1/admin/home").status_code == 200


def test_initialization_uses_placeholders_not_real_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEY_UPI_ID", "some-real-payee@bank")
    monkeypatch.setenv("MONEY_SELLER_NAME", "Private real supplier")
    engine = open_database(tmp_path / "placeholder.sqlite3")
    initialize(engine, "FixturePassword123!", "AdminPassword123!")
    with Session(engine) as db:
        assert db.get(SystemSetting, "payment.upi_id").value == "priveo-placeholder@upi"
        assert "placeholder" in db.get(SystemSetting, "invoice.seller_name").value
    engine.dispose()


def test_cli_dry_run_is_read_only_without_credentials(tmp_path, monkeypatch, capsys):
    target = tmp_path / "not-created.sqlite3"
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setattr(
        "sys.argv", ["test_data", "--refresh", "C07", "--dry-run", "--database-file", str(target)]
    )
    main()
    assert json.loads(capsys.readouterr().out)["scenarios"][0]["id"] == "C07"
    assert not target.exists()


def test_cli_rejects_production_writes_before_opening_file(tmp_path, monkeypatch):
    target = tmp_path / "not-created.sqlite3"
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setattr("sys.argv", ["test_data", "--init", "--database-file", str(target)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert not target.exists()


def test_cli_rejects_manifest_overwriting_database(tmp_path, monkeypatch):
    target = tmp_path / "not-created.sqlite3"
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setattr(
        "sys.argv", ["test_data", "--init", "--database-file", str(target), "--output", str(target)]
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert not target.exists()


def test_full_fresh_start_failure_preserves_original_file(tmp_path, monkeypatch):
    path = tmp_path / "fresh-failure.sqlite3"
    engine = open_database(path)
    initialize(engine, "FixturePassword123!", "AdminPassword123!")
    refresh(engine, ["C01"], DAY, "FixturePassword123!")
    before = manifest(engine)
    engine.dispose()

    def fail(*_args):
        raise RuntimeError("Injected replacement failure")

    monkeypatch.setattr("scripts.test_data._seed_scenario", fail)
    with pytest.raises(RuntimeError, match="Injected replacement failure"):
        fresh_start(path, DAY, "FixturePassword123!")
    engine = open_database(path)
    assert manifest(engine) == before
    engine.dispose()
    assert list(tmp_path.glob("*.refresh-*.sqlite3")) == []
