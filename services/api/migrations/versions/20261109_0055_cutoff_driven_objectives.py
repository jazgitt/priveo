"""Cutoff-driven scheduling: the two new objectives join the stored objective order.

The seed (`rule_seed`) only adds rows that are missing and never changes one, so
a site that already holds the old default order would leave the new objectives
`protected_late` and `cutoff_order` at the end of the order, below the early
objectives. This step moves a stored order that equals the old default to the
new default (SCHR-HIER-09), and adds the two new weights when they have no row
(SCHR-CFG-03). Any order an admin changed is left alone.

Revision ID: 0055
Revises: 0054
"""
import sqlalchemy as sa
from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None

ORDER_KEY = "scheduler.objective_order"
OLD_ORDER = "placed,zone,break,fifo,late,early_capacity,early"
NEW_ORDER = "placed,protected_late,zone,break,fifo,cutoff_order,late,early_capacity,early"
NEW_WEIGHTS = {"scheduler.weight_protected_late": "20000000000",
               "scheduler.weight_cutoff_order": "1000"}


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE system_settings SET value = :new WHERE key = :k AND value = :old"),
        {"new": NEW_ORDER, "k": ORDER_KEY, "old": OLD_ORDER},
    )
    conn.execute(
        sa.text("UPDATE society_settings SET value = :new WHERE key = :k AND value = :old"),
        {"new": NEW_ORDER, "k": ORDER_KEY, "old": OLD_ORDER},
    )
    for key, value in NEW_WEIGHTS.items():
        exists = conn.execute(
            sa.text("SELECT 1 FROM system_settings WHERE key = :k"), {"k": key}
        ).first()
        if exists is None:
            conn.execute(
                sa.text("INSERT INTO system_settings (key, value, updated_at) VALUES (:k, :v, CURRENT_TIMESTAMP)"),
                {"k": key, "v": value},
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE system_settings SET value = :old WHERE key = :k AND value = :new"),
        {"new": NEW_ORDER, "k": ORDER_KEY, "old": OLD_ORDER},
    )
    conn.execute(
        sa.text("UPDATE society_settings SET value = :old WHERE key = :k AND value = :new"),
        {"new": NEW_ORDER, "k": ORDER_KEY, "old": OLD_ORDER},
    )
    for key in NEW_WEIGHTS:
        conn.execute(sa.text("DELETE FROM system_settings WHERE key = :k"), {"k": key})
