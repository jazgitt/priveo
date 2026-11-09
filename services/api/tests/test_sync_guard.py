"""The prod-copy marker: a database with a sync-log row is refused by the seed and load scripts."""
import pytest
from sqlalchemy import create_engine, text

from app.platform.sync_guard import SYNC_LOG_TABLE, refuse_if_restored, restored_from_prod


def _engine():
    return create_engine("sqlite://")


def test_database_without_the_log_is_not_restored():
    assert restored_from_prod(_engine()) is None


def test_database_with_an_empty_log_is_not_restored():
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(text(f"create table {SYNC_LOG_TABLE} (id integer primary key, synced_at text)"))
    assert restored_from_prod(engine) is None


def test_last_sync_time_is_reported_and_writes_are_refused():
    engine = _engine()
    with engine.begin() as conn:
        conn.execute(text(f"create table {SYNC_LOG_TABLE} (id integer primary key, synced_at text)"))
        conn.execute(text(f"insert into {SYNC_LOG_TABLE} (synced_at) values "
                          "('2026-11-08 02:00'), ('2026-11-09 02:00')"))
    assert restored_from_prod(engine) == "2026-11-09 02:00"
    with pytest.raises(SystemExit, match="copied from prod at 2026-11-09"):
        refuse_if_restored(engine, "seed")
