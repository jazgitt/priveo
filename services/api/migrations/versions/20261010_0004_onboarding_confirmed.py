"""When a customer confirmed the review of their details.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers",
                  sa.Column("onboarding_confirmed_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("customers", "onboarding_confirmed_at")
