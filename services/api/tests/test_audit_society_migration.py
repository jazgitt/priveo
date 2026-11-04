"""Migration 0049: audit rows get the society they belong to, from the row they point at."""
import os
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import app.models  # noqa: F401  (registers the tables)
from app.platform.db import Base, make_engine
from tests.test_payment_status_migration import _insert


def test_the_audit_migration_scopes_existing_rows(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'a.db'}"
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    command.upgrade(config, "0048")

    now = datetime.now(UTC)
    ids = {k: uuid.uuid4() for k in ("login", "s1", "s2", "customer", "vehicle", "sub", "zone")}
    with engine.begin() as c:
        md = sa.MetaData()
        md.reflect(bind=c)
        t = md.tables
        for table in t.values():  # SQLite reflects a Uuid column as CHAR(32)
            for col in table.columns:
                if isinstance(col.type, sa.CHAR) and col.type.length == 32:
                    col.type = sa.Uuid()
        _insert(c, t["logins"], id=ids["login"], role="customer", login_id="9111111111",
                display_name="X", password_hash="x", created_at=now)
        _insert(c, t["societies"], id=ids["s1"], name="One", created_at=now)
        _insert(c, t["societies"], id=ids["s2"], name="Two", created_at=now)
        _insert(c, t["zones"], id=ids["zone"], society_id=ids["s2"], name="Z", created_at=now)
        _insert(c, t["customers"], id=ids["customer"], login_id=ids["login"], first_name="A",
                last_name="B", email="a@example.com", mobile="9111111111",
                society_id=ids["s1"], created_at=now)
        _insert(c, t["vehicles"], id=ids["vehicle"], customer_id=ids["customer"], created_at=now)
        _insert(c, t["subscriptions"], id=ids["sub"], vehicle_id=ids["vehicle"], status="Active",
                monthly_price_rupees=1299, first_service_date=now.date(), created_at=now)
        rows = [("society", ids["s2"]), ("customer", ids["customer"]), ("vehicle", ids["vehicle"]),
                ("subscription", ids["sub"]), ("zone", ids["zone"]), ("setting", "billing.x"),
                ("customer", uuid.uuid4())]
        for entity, entity_id in rows:
            _insert(c, t["directory_audit"], id=uuid.uuid4(), at=now, entity=entity,
                    entity_id=str(entity_id), action="update", detail={})

    command.upgrade(config, "0049")

    with engine.connect() as c:
        got = {(e, i): s for e, i, s in c.execute(
            sa.text("SELECT entity, entity_id, society_id FROM directory_audit"))}
    def society(entity, entity_id):
        value = got[(entity, str(entity_id))]
        return None if value is None else uuid.UUID(str(value))

    assert society("society", ids["s2"]) == ids["s2"]
    assert society("customer", ids["customer"]) == ids["s1"]
    assert society("vehicle", ids["vehicle"]) == ids["s1"]  # through the customer
    assert society("subscription", ids["sub"]) == ids["s1"]
    assert society("zone", ids["zone"]) == ids["s2"]
    assert society("setting", "billing.x") is None
    assert [v for (e, _), v in got.items() if e == "customer" and v is None]  # a row that is gone

    command.downgrade(config, "0048")
    command.downgrade(config, "base")
    engine.dispose()
