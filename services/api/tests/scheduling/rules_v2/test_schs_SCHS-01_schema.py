"""SCHS-01: the schema for the scheduler rules exists, unused and optional."""
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

import app.models  # noqa: F401  (registers the tables)
from app.platform.db import Base, make_engine

NEW_TABLES = {
    "society_settings", "break_rules", "interior_entitlements",
    "schedule_run_config", "schedule_findings", "scheduling_crew_home_zones",
}
NEW_COLUMNS = {
    "jobs": {"service_week_start", "cross_zone_reason", "reason_code"},
    "scheduling_crew": {"reporting_minute", "first_job_minute"},
    "cnc_reasons": {"defers"},
}


def test_models_hold_the_new_tables_and_columns():
    for table in NEW_TABLES:
        assert table in Base.metadata.tables, table
    for table, names in NEW_COLUMNS.items():
        assert names <= set(Base.metadata.tables[table].columns.keys()), table


def test_every_new_column_is_nullable_or_defaulted():
    for table, names in NEW_COLUMNS.items():
        for name in names:
            col = Base.metadata.tables[table].columns[name]
            assert col.nullable or col.server_default is not None, (table, name)


def _config(url):
    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    return config


def test_0051_upgrades_and_downgrades(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 's.db'}"
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    config = _config(url)
    command.upgrade(config, "head")
    built = inspect(engine)
    assert NEW_TABLES <= set(built.get_table_names())
    for table, names in NEW_COLUMNS.items():
        cols = {c["name"]: c for c in built.get_columns(table)}
        assert names <= set(cols), table
        for name in names:
            assert cols[name]["nullable"] or cols[name]["default"] is not None, (table, name)

    command.downgrade(config, "0050")
    after = inspect(engine)
    assert not NEW_TABLES & set(after.get_table_names())
    for table, names in NEW_COLUMNS.items():
        assert not names & {c["name"] for c in after.get_columns(table)}, table
    command.downgrade(config, "base")
    engine.dispose()
