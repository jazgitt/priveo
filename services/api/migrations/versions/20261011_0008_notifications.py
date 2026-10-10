"""The in-app inbox and the device tokens for push.

Revision ID: 0008
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
# The task named 20261010_0004_onboarding_confirmed, which is the file name;
# the revision ID inside that file is "0004". Re-chain at integration.
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visit_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_login_id", "notifications", ["login_id"])
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("token", sa.String(512), nullable=False, unique=True),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_device_tokens_login_id", "device_tokens", ["login_id"])


def downgrade() -> None:
    op.drop_table("device_tokens")
    op.drop_table("notifications")
