"""Audit rows carry the society they belong to (ADM-AUD-01).

Adds the nullable, indexed `directory_audit.society_id` and fills it for the
rows that exist, from the row each entry points at (the same rules as
`app.directory.audit_scope`). Rows that belong to no society, or whose row no
longer exists, stay empty.

Revision ID: 0049
Revises: 0048
"""
import uuid
from collections import defaultdict

import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def _t(name: str, *cols: str):
    return sa.table(name, *[sa.column(c, sa.Uuid()) for c in cols])


audit = sa.table(
    "directory_audit", sa.column("id", sa.Uuid()), sa.column("entity", sa.String()),
    sa.column("entity_id", sa.String()), sa.column("detail", sa.JSON()),
    sa.column("society_id", sa.Uuid()))


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _map(conn, table: str, key: str, *cols: str) -> dict:
    t = _t(table, key, *cols)
    return {r[0]: r[1:] for r in conn.execute(sa.select(*[t.c[c] for c in (key, *cols)]))}


def upgrade() -> None:
    with op.batch_alter_table("directory_audit") as batch:
        batch.add_column(sa.Column("society_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_directory_audit_society", "societies", ["society_id"], ["id"])
        batch.create_index("ix_directory_audit_society_id", ["society_id"])

    conn = op.get_bind()
    societies = set(_map(conn, "societies", "id"))
    zones = _map(conn, "zones", "id", "society_id")
    slots = _map(conn, "working_slots", "id", "society_id")
    customers = _map(conn, "customers", "id", "society_id")
    vehicles = _map(conn, "vehicles", "id", "society_id", "customer_id")
    subs = _map(conn, "subscriptions", "id", "vehicle_id")
    payments = _map(conn, "payments", "id", "customer_id")
    changes = _map(conn, "schedule_changes", "id", "customer_id")
    bookings = _map(conn, "addon_bookings", "id", "customer_id")
    old_addons = _map(conn, "addon_requests", "id", "customer_id")
    schedules = _map(conn, "schedules", "id", "society_id")
    visits = _map(conn, "visits", "id", "schedule_id")
    jobs = _map(conn, "jobs", "id", "visit_id")
    crew = _map(conn, "crew_members", "id", "society_id")
    sched_crew = _map(conn, "scheduling_crew", "id", "society_id")

    def of_customer(i):
        return customers.get(i, (None,))[0]

    def of_vehicle(i):
        v = vehicles.get(i)
        return (v[0] or of_customer(v[1])) if v else None

    def of_visit(i):
        v = visits.get(i)
        return schedules.get(v[0], (None,))[0] if v else None

    def resolve(entity, entity_id, detail):
        key = _uuid(str(entity_id).split(":")[0] if entity == "queue" else entity_id)
        found = None
        if key is not None:
            if entity == "society":
                found = key if key in societies else None
            elif entity == "zone":
                found = zones.get(key, (None,))[0]
            elif entity == "slot":
                found = slots.get(key, (None,))[0]
            elif entity == "customer":
                found = of_customer(key)
            elif entity in ("vehicle", "parking"):
                found = of_vehicle(key)
            elif entity == "subscription":
                found = of_vehicle(subs[key][0]) if key in subs else None
            elif entity == "payment":
                found = of_customer(payments[key][0]) if key in payments else None
            elif entity in ("schedule_change", "cutoff_request"):
                found = of_customer(changes[key][0]) if key in changes else None
            elif entity == "addon":
                row = bookings.get(key) or old_addons.get(key)
                found = of_customer(row[0]) if row else None
            elif entity == "schedule":
                found = schedules.get(key, (None,))[0]
            elif entity == "job":
                found = of_visit(jobs[key][0]) if key in jobs else None
            elif entity == "operations":
                found = of_visit(jobs[key][0]) if key in jobs else of_visit(key)
            elif entity in ("crew", "queue"):
                found = (crew.get(key) or sched_crew.get(key) or (None,))[0]
        if found:
            return found
        named = _uuid(detail.get("society_id")) if isinstance(detail, dict) else None
        return named if named in societies else None

    by_society = defaultdict(list)
    rows = conn.execute(sa.select(audit.c.id, audit.c.entity, audit.c.entity_id, audit.c.detail))
    for row_id, entity, entity_id, detail in rows:
        society = resolve(entity, entity_id, detail)
        if society:
            by_society[society].append(row_id)
    for society, ids in by_society.items():
        for start in range(0, len(ids), 500):
            conn.execute(sa.update(audit).where(audit.c.id.in_(ids[start:start + 500]))
                         .values(society_id=society))


def downgrade() -> None:
    with op.batch_alter_table("directory_audit") as batch:
        batch.drop_index("ix_directory_audit_society_id")
        batch.drop_constraint("fk_directory_audit_society", type_="foreignkey")
        batch.drop_column("society_id")
