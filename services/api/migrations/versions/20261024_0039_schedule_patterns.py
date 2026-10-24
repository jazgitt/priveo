"""Schedule patterns: a Weekly or Cycle pattern for a subscription.

S-02, ADM-SCH-41. A subscription with no row keeps today's behaviour (Exterior
every day, Interior on its interior care day), so no data is backfilled and
every existing schedule stays as it is.

Revision ID: 0039
Revises: 0038
"""
import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscription_schedule_patterns",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("subscription_id", sa.Uuid, sa.ForeignKey("subscriptions.id"),
                  nullable=False, unique=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("exterior_weekdays", sa.JSON, nullable=False),
        sa.Column("interior_weekdays", sa.JSON, nullable=False),
        sa.Column("exterior_days", sa.JSON, nullable=False),
        sa.Column("combined_days", sa.JSON, nullable=False),
        sa.Column("created_by", sa.Uuid, sa.ForeignKey("logins.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("subscription_schedule_patterns")
