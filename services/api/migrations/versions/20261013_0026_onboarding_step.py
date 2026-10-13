"""Persist the review position without confirming or creating payments."""
import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("customers") as batch:
        batch.add_column(sa.Column("onboarding_step", sa.Integer(), nullable=False,
                                   server_default="0"))


def downgrade():
    with op.batch_alter_table("customers") as batch:
        batch.drop_column("onboarding_step")
