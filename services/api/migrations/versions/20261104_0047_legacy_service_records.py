"""Service history from before the app: one row for each vehicle and day, read-only.

Revision ID: 0047
Revises: 0046
"""
import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "legacy_service_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("services", sa.String(40), nullable=False, server_default=""),
        sa.Column("outcome", sa.String(12), nullable=False),
        sa.Column("skip_reason", sa.String(60), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vehicle_id", "service_date", name="uq_legacy_service_vehicle_date"),
    )
    op.create_index("ix_legacy_service_records_vehicle_id", "legacy_service_records", ["vehicle_id"])


def downgrade():
    op.drop_index("ix_legacy_service_records_vehicle_id", table_name="legacy_service_records")
    op.drop_table("legacy_service_records")
