"""Working-slot exceptions (ADM-SVS-12, P3-3). A service-wise change to the Root
working slots (the `working_slots` rows) for a date range. Nothing is backfilled:
a site with no exception behaves as before.

Revision ID: 0057
Revises: 0056
"""
import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "working_slot_exceptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("service", sa.String(24), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days", sa.JSON(), nullable=False),
        sa.Column("windows", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_working_slot_exceptions_society_id", "working_slot_exceptions",
                    ["society_id"])


def downgrade() -> None:
    op.drop_index("ix_working_slot_exceptions_society_id", table_name="working_slot_exceptions")
    op.drop_table("working_slot_exceptions")
