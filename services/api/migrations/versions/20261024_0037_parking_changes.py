"""Parking changes: a temporary or permanent change of a vehicle's slot.

S-07, ADM-CUS-27, CRW-SCH-17. A change with an end date is temporary; without
one it is permanent from the start date. The vehicle's own slot is unchanged.

Revision ID: 0037
Revises: 0036
"""
import sqlalchemy as sa
from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vehicle_parking_changes",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("vehicle_id", sa.Uuid, sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("basement", sa.String(20), nullable=False),
        sa.Column("number", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("note", sa.String(160), nullable=False, server_default=""),
        sa.Column("created_by", sa.Uuid, sa.ForeignKey("logins.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_vehicle_parking_changes_vehicle_id", "vehicle_parking_changes",
                    ["vehicle_id"])


def downgrade():
    op.drop_index("ix_vehicle_parking_changes_vehicle_id", table_name="vehicle_parking_changes")
    op.drop_table("vehicle_parking_changes")
