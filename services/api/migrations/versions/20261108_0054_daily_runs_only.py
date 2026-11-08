"""The scheduler runs one day at a time: the scheduling period settings are removed.

A run covers the chosen day only (ADM-SCH-09, owner 08-Nov-26). The planning
period (`schedule.period`) and the planning week start (`schedule.week_start`)
no longer mean anything, so their stored values are deleted. The downgrade puts
back the old defaults (Weekly, Sunday).

Revision ID: 0054
Revises: 0053
"""
import sqlalchemy as sa
from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None

REMOVED = {"schedule.period": "Weekly", "schedule.week_start": "6"}


def upgrade() -> None:
    conn = op.get_bind()
    for key in REMOVED:
        conn.execute(sa.text("DELETE FROM system_settings WHERE key = :k"), {"k": key})


def downgrade() -> None:
    conn = op.get_bind()
    for key, value in REMOVED.items():
        conn.execute(
            sa.text("INSERT INTO system_settings (key, value, updated_at) VALUES (:k, :v, CURRENT_TIMESTAMP)"),
            {"k": key, "v": value},
        )
