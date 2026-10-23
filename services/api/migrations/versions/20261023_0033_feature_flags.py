"""Admin-controlled feature flags (ADM-FLAG). A key with no row is on."""
import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.String(48), primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_by", sa.Uuid, sa.ForeignKey("logins.id"), nullable=True),
    )


def downgrade():
    op.drop_table("feature_flags")
