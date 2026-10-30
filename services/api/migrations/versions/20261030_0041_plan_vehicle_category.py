"""Plan vehicle category: an optional link from a plan to a vehicle category.

Stored and shown only; it does not yet change which plans a customer is offered.

Revision ID: 0041
Revises: 0040
"""
import sqlalchemy as sa
from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("plans") as batch:
        batch.add_column(sa.Column("vehicle_category", sa.String(40), nullable=True))


def downgrade():
    with op.batch_alter_table("plans") as batch:
        batch.drop_column("vehicle_category")
