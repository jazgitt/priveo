"""Plan history: each plan change of a subscription, with its date.

S-11, ADM-SUB-08. A change is Scheduled until its date comes, then Applied; a
cancelled change stays. Plan names and prices are kept as they were.

Revision ID: 0038
Revises: 0037
"""
from datetime import UTC

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscription_plan_changes",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("subscription_id", sa.Uuid, sa.ForeignKey("subscriptions.id"), nullable=False),
        sa.Column("from_plan_id", sa.Uuid, sa.ForeignKey("plans.id"), nullable=True),
        sa.Column("from_plan_name", sa.String(80), nullable=False, server_default=""),
        sa.Column("from_price_rupees", sa.Integer, nullable=True),
        sa.Column("to_plan_id", sa.Uuid, sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("to_plan_name", sa.String(80), nullable=False),
        sa.Column("to_price_rupees", sa.Integer, nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("chosen", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(10), nullable=False, server_default="Scheduled"),
        sa.Column("created_by", sa.Uuid, sa.ForeignKey("logins.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_subscription_plan_changes_subscription_id", "subscription_plan_changes",
                    ["subscription_id"])
    # A change already scheduled before this migration gets a history row.
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT s.id, s.plan_id, s.monthly_price_rupees, s.pending_plan_id, s.pending_from, "
        "cp.name, np.name, np.monthly_price_rupees "
        "FROM subscriptions s JOIN plans np ON np.id = s.pending_plan_id "
        "LEFT JOIN plans cp ON cp.id = s.plan_id WHERE s.pending_plan_id IS NOT NULL")).all()
    import uuid
    from datetime import datetime
    for sid, plan_id, price, new_id, starts, old_name, new_name, new_price in rows:
        bind.execute(sa.text(
            "INSERT INTO subscription_plan_changes (id, subscription_id, from_plan_id, "
            "from_plan_name, from_price_rupees, to_plan_id, to_plan_name, to_price_rupees, "
            "effective_from, chosen, status, created_at) VALUES (:id, :sid, :fp, :fn, :fprice, "
            ":tp, :tn, :tprice, :starts, :chosen, 'Scheduled', :now)"),
            {"id": uuid.uuid4(), "sid": sid, "fp": plan_id, "fn": old_name or "",
             "fprice": price, "tp": new_id, "tn": new_name, "tprice": new_price,
             "starts": starts, "chosen": False, "now": datetime.now(UTC)})


def downgrade():
    op.drop_index("ix_subscription_plan_changes_subscription_id",
                  table_name="subscription_plan_changes")
    op.drop_table("subscription_plan_changes")
