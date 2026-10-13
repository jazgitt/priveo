"""A customer's pending email change (ACC-08).

Revision ID: 0019
Revises: 0018
"""
import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_changes",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("new_email", sa.String(254), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wrong_attempts", sa.Integer, nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_email_changes_customer_id", "email_changes", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_email_changes_customer_id", table_name="email_changes")
    op.drop_table("email_changes")
