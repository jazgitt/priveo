"""Marks a database that was copied from prod, so the seed and load scripts leave it alone.

`scripts/sync_prod_to_test.py` writes one row to `db_sync_log` each time it
copies prod into test. While that table has a row, the seed and load scripts
refuse to write (see `scripts/seed.py`, which skips quietly so the deploy still
passes). The table is created by the sync script, not by a migration, so prod
never gets it.
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

SYNC_LOG_TABLE = "db_sync_log"


def restored_from_prod(engine: Engine) -> str | None:
    """The time of the last copy from prod, or None when this database was never copied."""
    if not inspect(engine).has_table(SYNC_LOG_TABLE):
        return None
    with engine.connect() as conn:
        row = conn.execute(text(
            f"select synced_at from {SYNC_LOG_TABLE} order by id desc limit 1")).first()
    return None if row is None else str(row[0])


def refuse_if_restored(engine: Engine, script: str) -> None:
    """Stops a script that would write to a database copied from prod."""
    when = restored_from_prod(engine)
    if when:
        raise SystemExit(
            f"{script}: refused. This database was copied from prod at {when} "
            f"({SYNC_LOG_TABLE}), and its data must not be changed by seed or load scripts.")
