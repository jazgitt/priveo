"""Copy the data of one PostgreSQL database into another, table by table.

    SOURCE_DATABASE_URL=...  TARGET_DATABASE_URL=...  python scripts/copy_dev_db.py

Used by tools/dev/local-db.ps1 to make a local copy of the shared dev database.
Reads from the source only. It does not need pg_dump, so the server versions may
differ. The target must be empty and already hold the schema (alembic upgrade
head); both databases must be at the same migration. Prints counts, never data.
"""
import os
import sys

import psycopg


def libpq(url: str) -> str:
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def tables(conn: psycopg.Connection) -> list[str]:
    rows = conn.execute(
        "select table_name from information_schema.tables "
        "where table_schema = 'public' and table_type = 'BASE TABLE' order by table_name"
    ).fetchall()
    return [r[0] for r in rows]


def columns(conn: psycopg.Connection, table: str) -> list[str]:
    rows = conn.execute(
        "select column_name from information_schema.columns "
        "where table_schema = 'public' and table_name = %s order by ordinal_position", (table,)
    ).fetchall()
    return [r[0] for r in rows]


def main() -> int:
    source = psycopg.connect(libpq(os.environ["SOURCE_DATABASE_URL"]))
    target = psycopg.connect(libpq(os.environ["TARGET_DATABASE_URL"]), autocommit=False)
    source.read_only = True

    a = source.execute("select version_num from alembic_version").fetchone()
    b = target.execute("select version_num from alembic_version").fetchone()
    if a != b:
        print(f"Migrations differ: source {a[0] if a else None}, target {b[0] if b else None}.")
        return 1
    missing = set(tables(source)) - set(tables(target))
    if missing:
        # Tables made outside the migrations (the shared test-data manifest) are left behind.
        print(f"Skipping table(s) the migrations do not create: {sorted(missing)}.")

    names = [t for t in tables(target) if t != "alembic_version" and t in set(tables(source))]
    # Constraints are checked at the end, so the order of the tables does not matter.
    target.execute("set session_replication_role = replica")
    # Empty every table first, in one statement. Truncating one at a time with
    # cascade would wipe the child tables already copied.
    target.execute("truncate table " + ", ".join(f'"{t}"' for t in names))
    total = 0
    for table in names:
        cols = columns(target, table)
        if cols != columns(source, table):
            print(f"Columns of {table} differ between the databases.")
            target.rollback()
            return 1
        quoted = ", ".join(f'"{c}"' for c in cols)
        count = 0
        with source.cursor().copy(f'copy "{table}" ({quoted}) to stdout') as out, \
                target.cursor().copy(f'copy "{table}" ({quoted}) from stdin') as inn:
            for chunk in out:
                inn.write(chunk)
        count = target.execute(f'select count(*) from "{table}"').fetchone()[0]
        total += count
        print(f"{table}: {count}")
    # Serial columns, if any, continue after the copied rows.
    for table in names:
        for (col,) in target.execute(
            "select column_name from information_schema.columns "
            "where table_schema = 'public' and table_name = %s", (table,)
        ).fetchall():
            seq = target.execute("select pg_get_serial_sequence(%s, %s)",
                                 (f'public."{table}"', col)).fetchone()[0]
            if seq:
                target.execute(
                    f'select setval(%s, coalesce((select max("{col}") from "{table}"), 1))', (seq,))
    # Every table must hold what the source holds, whatever the order was.
    for table in names:
        want = source.execute(f'select count(*) from "{table}"').fetchone()[0]
        got = target.execute(f'select count(*) from "{table}"').fetchone()[0]
        if want != got:
            print(f"{table}: source {want}, copy {got}")
            target.rollback()
            return 1
    target.commit()
    print(f"Copied {len(names)} tables, {total} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
