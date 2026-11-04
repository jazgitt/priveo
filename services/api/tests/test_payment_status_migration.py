"""Migration 0048: Received -> Paid, Due and Over due -> Open, due on the cycle's last day,
and the current cycle's payment for a live subscription that has none."""
import os
import uuid
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import app.models  # noqa: F401  (registers the tables)
from app.platform.db import Base, make_engine


def _fill(table, given):
    """Values for the other NOT NULL columns that have no default."""
    out = {}
    for col in table.columns:
        if col.name in given or col.nullable or col.server_default is not None:
            continue
        t = col.type
        if isinstance(t, sa.Boolean):
            out[col.name] = False
        elif isinstance(t, sa.Integer):
            out[col.name] = 0
        elif isinstance(t, sa.DateTime):
            out[col.name] = datetime.now(UTC)
        elif isinstance(t, sa.Date):
            out[col.name] = datetime.now(UTC).date()
        elif isinstance(t, sa.Uuid):
            out[col.name] = uuid.uuid4()
        elif isinstance(t, sa.JSON):
            out[col.name] = []
        else:
            out[col.name] = ""
    return out


def _insert(conn, table, **values):
    values = {k: v for k, v in values.items() if k in table.columns}
    conn.execute(table.insert().values(**values, **_fill(table, set(values))))


def test_the_status_migration_converts_rows_and_backfills(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'm.db'}"
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    command.upgrade(config, "0047")

    now = datetime.now(UTC)
    ids = {k: uuid.uuid4() for k in ("login", "society", "customer", "vehicle", "vehicle2",
                                     "sub", "sub2", "recv", "due", "over")}
    start = datetime.now(UTC).date() - timedelta(days=10)
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
        _insert(c, t["societies"], id=ids["society"], name="S", created_at=now)
        _insert(c, t["customers"], id=ids["customer"], login_id=ids["login"], first_name="A", society_id=ids["society"],
                last_name="B", email="a@example.com", mobile="9111111111", created_at=now)
        for v, s in (("vehicle", "sub"), ("vehicle2", "sub2")):
            _insert(c, t["vehicles"], id=ids[v], customer_id=ids["customer"], created_at=now)
            _insert(c, t["subscriptions"], id=ids[s], vehicle_id=ids[v], status="Active",
                    monthly_price_rupees=1299, first_service_date=start, created_at=now)

        def pay(key, status, kind="Plan", sub=None, **kw):
            _insert(c, t["payments"], id=ids[key], customer_id=ids["customer"],
                    vehicle_id=ids["vehicle"], subscription_id=sub, kind=kind,
                    description="d", amount_rupees=1299, status=status, created_at=now, **kw)

        pay("recv", "Received", sub=ids["sub"], due_date=start, cycle_start=start,
            cycle_end=start + timedelta(days=30))
        pay("due", "Due", sub=ids["sub"], due_date=start + timedelta(days=30),
            cycle_start=start + timedelta(days=30), cycle_end=start + timedelta(days=60))
        pay("over", "Over due", kind="Add-on", due_date=start, overdue_since=start)

    command.upgrade(config, "head")
    with engine.connect() as c:
        # Raw SQL gives hex text on SQLite and UUIDs on PostgreSQL.
        def norm(value):
            return None if value is None else str(value).replace("-", "")

        rows = [dict(r) for r in c.execute(sa.text("select * from payments")).mappings()]
        by_id = {k: next(r for r in rows if norm(r["id"]) == ids[k].hex)
                 for k in ("recv", "due", "over")}

        def day(value):
            return str(value)[:10]

        assert by_id["recv"]["status"] == "Paid"
        assert by_id["due"]["status"] == "Open"
        assert by_id["over"]["status"] == "Open"
        assert day(by_id["over"]["overdue_since"]) == start.isoformat()
        assert day(by_id["recv"]["due_date"]) == (start + timedelta(days=29)).isoformat()
        assert day(by_id["due"]["due_date"]) == (start + timedelta(days=59)).isoformat()
        # sub2 had no payment: one Open plan payment for its current cycle was added.
        added = [r for r in rows if norm(r["subscription_id"]) == ids["sub2"].hex]
        assert len(added) == 1 and added[0]["status"] == "Open" and added[0]["kind"] == "Plan"
        assert day(added[0]["cycle_start"]) == start.isoformat()
        assert day(added[0]["due_date"]) == (start + timedelta(days=29)).isoformat()
        assert added[0]["amount_rupees"] == 1299
        # sub already had a payment for its current cycle: nothing added to it.
        assert len([r for r in rows if norm(r["subscription_id"]) == ids["sub"].hex]) == 2

    command.downgrade(config, "0047")
    with engine.connect() as c:
        back = {r["id"]: r["status"] for r in c.execute(sa.text("select * from payments")).mappings()}
        statuses = sorted(back.values())
        assert statuses.count("Received") == 1 and statuses.count("Over due") == 1
        assert statuses.count("Due") == 2
        assert "rejected_at" not in {col["name"] for col in sa.inspect(c).get_columns("payments")}
    command.downgrade(config, "base")
    engine.dispose()
