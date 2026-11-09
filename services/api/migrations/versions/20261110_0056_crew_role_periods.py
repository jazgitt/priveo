"""Temporary crew roles: a role for a date range (P2-4, owner decisions 7 and 11).

A crew member keeps their permanent role on `scheduling_crew.role`. A row here
gives another role from `start_date` to `end_date`, both days included. An
empty `end_date` lasts until the role is changed. The role never applies to a
day before today, so a run that has passed is not changed.

Revision ID: 0056
Revises: 0055
"""
import sqlalchemy as sa
from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduling_crew_role_periods",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("crew_id", sa.Uuid(), sa.ForeignKey("scheduling_crew.id"), nullable=False),
        sa.Column("role", sa.String(8), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scheduling_crew_role_periods_crew_id", "scheduling_crew_role_periods", ["crew_id"])


def downgrade() -> None:
    op.drop_index("ix_scheduling_crew_role_periods_crew_id", table_name="scheduling_crew_role_periods")
    op.drop_table("scheduling_crew_role_periods")
