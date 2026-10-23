"""Add the new could-not-complete (exception) reasons.

A data migration. It inserts each missing reason by key and leaves existing
rows and any admin edits (label, order, active) untouched. It does nothing on
an empty table, because the seed fills an empty table with every default.

Revision ID: 0034
Revises: 0032 (change to 0033 if the feature-flags migration lands first)
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None

NEW_REASONS = (
    ("different_parking_location", "Different parking location"),
    ("keys_customer_unavailable", "Keys/customer unavailable"),
    ("access_restricted", "Access restricted"),
    ("customer_requested_no_cleaning", "Customer requested no cleaning"),
    ("weather_operational_issue", "Weather/operational issue"),
)


def add_missing_reasons(bind) -> int:
    """Insert the reasons whose key is absent. Safe to run any number of times."""
    table = sa.table(
        "cnc_reasons",
        sa.column("id", sa.Uuid),
        sa.column("key", sa.String),
        sa.column("label", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("active", sa.Boolean),
    )
    rows = bind.execute(sa.select(table.c.key, table.c.sort_order)).all()
    if not rows:
        return 0
    taken = {r.key for r in rows}
    order = max(r.sort_order for r in rows) + 1
    added = 0
    for key, label in NEW_REASONS:
        if key in taken:
            continue
        bind.execute(
            sa.insert(table).values(
                id=uuid.uuid4(), key=key, label=label, sort_order=order, active=True
            )
        )
        order += 1
        added += 1
    return added


def upgrade() -> None:
    add_missing_reasons(op.get_bind())


def downgrade() -> None:
    # Past records keep their reason keys, so the rows stay.
    pass
