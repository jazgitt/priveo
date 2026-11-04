"""Payment status rework: stored Open | Initiated | Paid, due on the cycle's last day.

Received becomes Paid; Due and Over due become Open (an Over due payment keeps
its `overdue_since`). A plan payment is due on the last day of its cycle
(`cycle_end` is stored as the day after, so `cycle_end - 1 day`). A new
`rejected_at` records an admin rejection. Every Active or Activating
subscription with no payment for its current cycle gets one.

Revision ID: 0048
Revises: 0047
"""
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None

CYCLE_DAYS = 30  # the starting value of the `billing.cycle_days` setting

payments = sa.table(
    "payments",
    sa.column("id", sa.Uuid()), sa.column("customer_id", sa.Uuid()),
    sa.column("vehicle_id", sa.Uuid()), sa.column("subscription_id", sa.Uuid()),
    sa.column("kind", sa.String()), sa.column("description", sa.String()),
    sa.column("amount_rupees", sa.Integer()), sa.column("status", sa.String()),
    sa.column("due_date", sa.Date()), sa.column("cycle_start", sa.Date()),
    sa.column("cycle_end", sa.Date()), sa.column("overdue_since", sa.Date()),
    sa.column("voided_at", sa.DateTime(timezone=True)),
    sa.column("created_at", sa.DateTime(timezone=True)),
)
subscriptions = sa.table(
    "subscriptions",
    sa.column("id", sa.Uuid()), sa.column("vehicle_id", sa.Uuid()),
    sa.column("status", sa.String()), sa.column("first_service_date", sa.Date()),
    sa.column("monthly_price_rupees", sa.Integer()),
)
vehicles = sa.table("vehicles", sa.column("id", sa.Uuid()), sa.column("customer_id", sa.Uuid()))


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def upgrade():
    op.add_column("payments", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    bind = op.get_bind()
    bind.execute(payments.update().where(payments.c.status == "Received").values(status="Paid"))
    bind.execute(payments.update().where(payments.c.status.in_(("Due", "Over due")))
                 .values(status="Open"))
    # Plan payments are due on the cycle's last day.
    rows = bind.execute(sa.select(payments.c.id, payments.c.cycle_end).where(
        payments.c.kind == "Plan", payments.c.cycle_end.is_not(None))).all()
    for pid, cycle_end in rows:
        bind.execute(payments.update().where(payments.c.id == pid)
                     .values(due_date=_as_date(cycle_end) - timedelta(days=1)))
    # The current cycle's payment for each live subscription that has none.
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    subs = bind.execute(
        sa.select(subscriptions.c.id, subscriptions.c.vehicle_id,
                  subscriptions.c.first_service_date, subscriptions.c.monthly_price_rupees,
                  vehicles.c.customer_id)
        .join(vehicles, vehicles.c.id == subscriptions.c.vehicle_id)
        .where(subscriptions.c.status.in_(("Active", "Activating")))).all()
    for sub_id, vehicle_id, first, price, customer_id in subs:
        first = _as_date(first)
        start = first + timedelta(days=CYCLE_DAYS * max(0, (today - first).days // CYCLE_DAYS))
        found = bind.execute(sa.select(payments.c.id).where(
            payments.c.subscription_id == sub_id, payments.c.cycle_start == start)).first()
        if found is not None:
            continue
        end = start + timedelta(days=CYCLE_DAYS)
        bind.execute(payments.insert().values(
            id=uuid.uuid4(), customer_id=customer_id, vehicle_id=vehicle_id,
            subscription_id=sub_id, kind="Plan",
            description=f"Plan {start:%d-%b-%y} to {end - timedelta(days=1):%d-%b-%y}",
            amount_rupees=price, status="Open", due_date=end - timedelta(days=1),
            cycle_start=start, cycle_end=end, created_at=datetime.now(UTC)))


def downgrade():
    bind = op.get_bind()
    bind.execute(payments.update().where(payments.c.status == "Paid").values(status="Received"))
    bind.execute(payments.update().where(
        payments.c.status == "Open", payments.c.overdue_since.is_not(None))
        .values(status="Over due"))
    bind.execute(payments.update().where(payments.c.status == "Open").values(status="Due"))
    # A plan payment was due on the first day of its cycle.
    bind.execute(payments.update().where(
        payments.c.kind == "Plan", payments.c.cycle_start.is_not(None))
        .values(due_date=payments.c.cycle_start))
    op.drop_column("payments", "rejected_at")
