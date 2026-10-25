"""Plan change charge: what the admin charged for the days before the renewal.

The admin decides for each change: no charge, the prorated difference, or an amount.

Revision ID: 0040
Revises: 0039
"""
import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("subscription_plan_changes") as batch:
        batch.add_column(sa.Column("charge_rupees", sa.Integer, nullable=True))
        batch.add_column(sa.Column("payment_id", sa.Uuid, nullable=True))
        batch.create_foreign_key("fk_plan_change_payment", "payments", ["payment_id"], ["id"])


def downgrade():
    with op.batch_alter_table("subscription_plan_changes") as batch:
        batch.drop_constraint("fk_plan_change_payment", type_="foreignkey")
        batch.drop_column("payment_id")
        batch.drop_column("charge_rupees")
