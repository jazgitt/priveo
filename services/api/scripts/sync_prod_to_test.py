"""Overwrite the test database with a copy of the prod database. Run on demand.

    SOURCE_DATABASE_URL=<prod>  TARGET_DATABASE_URL=<test>  python scripts/sync_prod_to_test.py
    ... add --apply to write. It asks you to type SYNC TEST first; --yes skips the question.

Without --apply nothing is written: it prints what would be copied.

What happens, all in one transaction on the test database:
- every table test shares with prod is emptied and copied from prod, as-is,
  except that the photo tables (media_uploads, crew_photos) are left empty and
  the references to photos (vehicle photo and RC, job outcome photo, complaint
  photo keys) are cleared, so no row points at a file test does not have;
- test's own admin password is put back, so the test admin login and the deploy
  smoke test keep working with the test ADMIN_PASSWORD;
- the shared test-data manifest is emptied, because its scenarios were removed;
- a row is added to db_sync_log. Seed and load scripts refuse to write to a
  database with that row (app/platform/sync_guard.py).

Prints counts and identities (host and database name), never a password or data.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg
from copy_dev_db import copy_database, libpq, tables
from switch_off_test_crons import registered_jobs

from app.platform.sync_guard import SYNC_LOG_TABLE

# Photo tables are never copied: test keeps no photo files, so these stay empty.
SKIP_ROWS = frozenset({"media_uploads", "crew_photos"})

# References to photos, cleared after the copy so they do not point at nothing.
PHOTO_CLEARS = (
    "update vehicles set photo_upload_id = null, rc_upload_id = null",
    "update job_outcomes set upload_id = null",
    "update complaints set photo_keys = '[]'::json",
)

TEST_ADMIN_LOGIN = "priveopapa"
MANIFEST_TABLE = "shared_test_data_manifest"
CONFIRMATION = "SYNC TEST"


def identity(url: str) -> str:
    """host:port/database, with no user or password."""
    parts = urlsplit(libpq(url))
    return f"{parts.hostname}:{parts.port or 5432}/{parts.path.lstrip('/')}"


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    assume_yes = "--yes" in argv
    source_url = os.environ.get("SOURCE_DATABASE_URL", "")
    target_url = os.environ.get("TARGET_DATABASE_URL", "")
    if not source_url or not target_url:
        print("Set SOURCE_DATABASE_URL (prod) and TARGET_DATABASE_URL (test).")
        return 2
    if identity(source_url) == identity(target_url):
        print("Source and target are the same database. Refused.")
        return 2

    print(f"Source (prod): {identity(source_url)}")
    print(f"Target (test): {identity(target_url)}")

    source = psycopg.connect(libpq(source_url))
    target = psycopg.connect(libpq(target_url), autocommit=False)
    source.read_only = True
    try:
        if not apply:
            return dry_run(source, target)
        if not assume_yes:
            if not sys.stdin.isatty():
                print("Not a terminal: pass --yes to apply without the question.")
                return 2
            typed = input(f"This replaces every row in the test database. Type {CONFIRMATION}: ")
            if typed.strip() != CONFIRMATION:
                print("Not confirmed. Nothing written.")
                return 2
        return apply_sync(source, target)
    finally:
        source.close()
        target.close()


def dry_run(source: psycopg.Connection, target: psycopg.Connection) -> int:
    source_head = source.execute("select version_num from alembic_version").fetchone()
    target_head = target.execute("select version_num from alembic_version").fetchone()
    print(f"Migration head: source {source_head[0] if source_head else None}, "
          f"target {target_head[0] if target_head else None}.")
    if source_head != target_head:
        print("The migrations differ. A sync is refused until both are at the same head.")
        return 1
    shared = [t for t in tables(target) if t != "alembic_version" and t in set(tables(source))]
    total = 0
    for table in shared:
        count = source.execute(f'select count(*) from "{table}"').fetchone()[0]
        total += count
        note = "  (not copied: photos)" if table in SKIP_ROWS else ""
        print(f"  {table}: {count}{note}")
    print(f"{len(shared)} tables, {total} rows in prod.")
    admin = target.execute(
        "select 1 from logins where login_id = %s and role = 'admin'", (TEST_ADMIN_LOGIN,)
    ).fetchone()
    print("Test admin login will be kept: " + ("yes" if admin else "no, test has none"))
    last = last_sync(target)
    print(f"Last sync into test: {last or 'none'}")
    print("Dry run. Nothing was written. Add --apply to copy.")
    return 0


def last_sync(target: psycopg.Connection) -> str | None:
    if SYNC_LOG_TABLE not in tables(target):
        return None
    row = target.execute(
        f"select synced_at from {SYNC_LOG_TABLE} order by id desc limit 1").fetchone()
    return str(row[0]) if row else None


def apply_sync(source: psycopg.Connection, target: psycopg.Connection) -> int:
    # Read the test admin's password before the copy replaces the logins.
    kept = target.execute(
        "select password_hash, password_changed_at from logins "
        "where login_id = %s and role = 'admin'", (TEST_ADMIN_LOGIN,)
    ).fetchone()

    code = copy_database(source, target, skip_rows=SKIP_ROWS)
    if code:
        target.rollback()
        print("Nothing was written to test.")
        return code

    target_tables = set(tables(target))
    if kept is not None:
        target.execute(
            "update logins set password_hash = %s, password_changed_at = %s "
            "where login_id = %s and role = 'admin'",
            (kept[0], kept[1], TEST_ADMIN_LOGIN))
        print("Test admin login kept.")
    else:
        print("Test had no admin login; the admin login is prod's.")
    for statement in PHOTO_CLEARS:
        target.execute(statement)
    if MANIFEST_TABLE in target_tables:
        target.execute(f"truncate table {MANIFEST_TABLE}")

    # Prod's scheduled-job switches are copied too: test switches every job off (decision, 9-Nov-26).
    for job in registered_jobs():
        target.execute(
            "insert into cron_jobs (job, enabled, updated_at) values (%s, false, now()) "
            "on conflict (job) do update set enabled = false, updated_at = now()", (job,))
    print(f"Scheduled jobs off on test: {len(registered_jobs())}.")

    head = source.execute("select version_num from alembic_version").fetchone()[0]
    target.execute(
        f"create table if not exists {SYNC_LOG_TABLE} ("
        "id bigserial primary key, "
        "synced_at timestamptz not null default now(), "
        "source text not null, "
        "migration_head text not null)")
    target.execute(
        f"insert into {SYNC_LOG_TABLE} (source, migration_head) values (%s, %s)",
        ("prod", head))
    target.commit()
    print("Synced: test now holds a copy of prod. Seed and load scripts are switched off for test.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
