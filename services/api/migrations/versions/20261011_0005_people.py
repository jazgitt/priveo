"""Crew members.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crew_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False,
                  unique=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("mobile", sa.String(10), nullable=False, unique=True),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("working_hours", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role in ('Manager', 'Member', 'Trainee')",
                           name="crew_members_role_check"),
    )
    op.create_index("ix_crew_members_society_id", "crew_members", ["society_id"])


def downgrade() -> None:
    op.drop_table("crew_members")
