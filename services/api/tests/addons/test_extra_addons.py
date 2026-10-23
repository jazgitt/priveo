# ruff: noqa: F811
"""S-08: 'Extra interior cleaning' and 'Special exterior cleaning'. The owner has
not set their prices, so they start inactive at 0 until the admin activates them."""
import importlib.util
import os
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text

from app.addons.models import AddonBooking
from app.billing.models import Payment
from app.directory import defaults
from app.directory.models import AddonCatalogueItem
from app.directory.seed import seed_defaults
from app.platform.db import Base, make_engine
from app.scheduling.models import Job
from tests.addons.test_addons import request
from tests.changes.money_fixtures import money  # noqa: F401
from tests.scheduling.conftest import SUNDAY, admin, api, world  # noqa: F401
from tests.scheduling.test_operations import setup
from tests.test_api import auth, login

EXTRAS = {
    "Extra interior cleaning": "Cleaning-Internal",
    "Special exterior cleaning": "Cleaning-External",
}


def _extras(db):
    rows = db.scalars(select(AddonCatalogueItem).where(
        AddonCatalogueItem.name.in_(EXTRAS))).all()
    return {r.name: r for r in rows}


def test_seed_creates_both_rows_inactive_at_zero_and_is_repeatable(money):
    seed_defaults(money.db)
    seed_defaults(money.db)
    money.db.commit()
    rows = _extras(money.db)
    assert set(rows) == set(EXTRAS)
    for name, row in rows.items():
        assert (row.service, row.price_rupees, row.active, row.duration_minutes) == (
            EXTRAS[name], 0, False, 20)
    codes = [r.code for r in money.db.scalars(select(AddonCatalogueItem))]
    assert sorted(codes) == ["ADN-0001", "ADN-0002", "ADN-0003"]
    assert len(defaults.EXTRA_ADDONS) == 2


def test_an_inactive_add_on_is_not_offered_and_cannot_be_booked(money):
    m = money
    seed_defaults(m.db)
    m.db.commit()
    offers = m.client.get("/v1/customer/addons", headers=m.customer).json()["offers"]
    assert [o["name"] for o in offers] == ["Deep Spa"]
    listed = m.client.get("/v1/customer/directory/addons", headers=m.customer).json()
    assert [a["name"] for a in listed] == ["Deep Spa"]
    for row in _extras(m.db).values():
        r = request(m, addon=row.code, service=row.service)
        assert r.status_code == 422, r.text
    assert m.db.scalars(select(Payment)).all() == []


def test_once_the_admin_prices_and_activates_it_a_subscriber_can_book_it(money):
    m = money
    seed_defaults(m.db)
    m.db.commit()
    for name in EXTRAS:
        row = _extras(m.db)[name]
        r = m.client.patch(f"/v1/admin/directory/addons/{row.id}", headers=m.admin,
                           json={"price_rupees": 299})
        assert r.status_code == 200, r.text
        r = m.client.post(f"/v1/admin/directory/addons/{row.id}/reactivate", headers=m.admin)
        assert r.status_code == 200 and r.json()["active"] is True
    offers = m.client.get("/v1/customer/addons", headers=m.customer).json()["offers"]
    assert {o["name"] for o in offers} == {"Deep Spa", *EXTRAS}
    for day, (name, service) in zip(("2026-10-20", "2026-10-21"), EXTRAS.items(), strict=True):
        m.db.expire_all()
        code = _extras(m.db)[name].code
        r = request(m, addon=code, service="Deep Spa", date=day)
        assert r.status_code == 201, r.text
        a = r.json()
        assert (a["service"], a["addon_name"], a["price_rupees"]) == (service, name, 299)
        pay = m.db.get(Payment, uuid.UUID(a["payment_id"]))
        assert (pay.kind, pay.amount_rupees, pay.status) == ("Add-on", 299, "Due")
    # Any job made for these bookings carries the add-on's own service.
    for job in m.db.scalars(select(Job).where(Job.addon_booking_id.is_not(None))):
        assert job.service in EXTRAS.values()


# ---- the migration ---------------------------------------------------------------

def _config(url):
    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    return config


def _insert(c, code, name, service, price, active, sqlite):
    c.execute(text(
        "INSERT INTO addon_catalogue (id, code, name, description, service, price_rupees,"
        " duration_minutes, active, sort_order) VALUES (:i, :c, :n, 'd', :s, :p, 20, :a, 0)"),
        {"i": uuid.uuid4().hex if sqlite else str(uuid.uuid4()), "c": code, "n": name,
         "s": service, "p": price, "a": active})


def _rows(engine):
    with engine.connect() as c:
        return c.execute(text(
            "SELECT code, name, price_rupees, active FROM addon_catalogue ORDER BY code")).all()


def test_the_migration_adds_missing_rows_once_and_keeps_admin_edits(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'x.db'}"
    sqlite = url.startswith("sqlite")
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    config = _config(url)
    command.upgrade(config, "0032")
    with engine.begin() as c:
        _insert(c, "ADN-0001", "Deep Spa", "Deep Spa", 1500, True, sqlite)
        # The admin already made and priced one of them, with a changed case.
        _insert(c, "ADN-0004", "EXTRA interior cleaning", "Cleaning-Internal", 250, True, sqlite)
    command.upgrade(config, "0035")
    rows = _rows(engine)
    assert [(r[1], r[2], bool(r[3])) for r in rows] == [
        ("Deep Spa", 1500, True),
        ("EXTRA interior cleaning", 250, True),
        ("Special exterior cleaning", 0, False),
    ]
    assert rows[2][0] == "ADN-0005"  # The next free ID, after the admin's ADN-0004.

    # Running the same step again changes nothing.
    path = Path("migrations/versions/20261023_0035_extra_addons.py")
    spec = importlib.util.spec_from_file_location("extra_addons_mig", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with engine.begin() as c, Operations.context(MigrationContext.configure(c)):
        mod.upgrade()
    assert _rows(engine) == rows

    # Down and up again also leaves the admin's priced row alone.
    command.downgrade(config, "0032")
    assert [r[1] for r in _rows(engine)] == ["Deep Spa", "EXTRA interior cleaning"]
    command.upgrade(config, "0035")
    assert [(r[1], r[2]) for r in _rows(engine)] == [
        ("Deep Spa", 1500), ("EXTRA interior cleaning", 250), ("Special exterior cleaning", 0)]
    command.downgrade(config, "base")
    engine.dispose()


# ---- the job a booking creates -----------------------------------------------------

def test_a_booked_extra_add_on_creates_a_job_for_its_own_service(world, api, admin):
    vehicle, _sid, _visit, _jobs = setup(world, api, admin)
    seed_defaults(world.db)
    for row in _extras(world.db).values():
        row.price_rupees, row.active = 199, True
    world.db.commit()
    customer = auth(login(api, "customer")["access_token"])
    for name, service in EXTRAS.items():
        code = _extras(world.db)[name].code
        r = api.post(f"/v1/customer/vehicles/{vehicle.id}/addons", headers=customer,
                     json={"addon": code, "service": "Deep Spa",
                           "date": SUNDAY.isoformat(), "finish_by": "14:00"})
        assert r.status_code == 201, r.text
        booking = world.db.get(AddonBooking, uuid.UUID(r.json()["id"]))
        assert (booking.service, booking.price_rupees) == (service, 199)
        job = world.db.scalar(select(Job).where(Job.addon_booking_id == booking.id))
        assert job is not None and job.service == service
        assert world.db.get(Payment, booking.payment_id).amount_rupees == 199
