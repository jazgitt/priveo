"""Notification preferences, crew events and what a message opens.

Revision ID: 0015
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch:
        batch.alter_column("event", existing_type=sa.String(32), type_=sa.String(40),
                           existing_nullable=False)
        batch.add_column(sa.Column("ref_type", sa.String(24)))
        batch.add_column(sa.Column("ref_id", sa.String(64)))
        batch.add_column(sa.Column("dedupe_key", sa.String(160)))
        batch.create_unique_constraint("notifications_dedupe_unique",
                                       ["login_id", "dedupe_key"])
    op.create_table(
        "notification_preferences",
        sa.Column("login_id", sa.Uuid(), sa.ForeignKey("logins.id"), primary_key=True),
        sa.Column("event", sa.String(40), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    with op.batch_alter_table("notifications") as batch:
        batch.drop_constraint("notifications_dedupe_unique", type_="unique")
        batch.drop_column("dedupe_key")
        batch.drop_column("ref_id")
        batch.drop_column("ref_type")
        batch.alter_column("event", existing_type=sa.String(40), type_=sa.String(32),
                           existing_nullable=False)
