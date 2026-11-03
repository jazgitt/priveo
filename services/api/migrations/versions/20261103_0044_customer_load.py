"""Customer load from the owner's sheet: a customer may have no email or sign-in,
alternate names, wider car number and parking text, zones, and a note for a
"Custom" interior day.

Revision ID: 0044
Revises: 0043
"""
import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "zones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("society_id", "name", name="uq_zone_society_name"),
    )
    op.create_index("ix_zones_society_id", "zones", ["society_id"])

    with op.batch_alter_table("customers") as batch:
        batch.alter_column("login_id", existing_type=sa.Uuid(), nullable=True)
        batch.alter_column("email", existing_type=sa.String(254), nullable=True)
        batch.add_column(sa.Column("alternate_names", sa.Text(), nullable=True))

    with op.batch_alter_table("vehicles") as batch:
        batch.alter_column("registration", existing_type=sa.String(12),
                           type_=sa.String(20), existing_nullable=True)
        batch.alter_column("parking_number", existing_type=sa.String(20),
                           type_=sa.String(60), existing_nullable=False)
        batch.add_column(sa.Column("zone_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_vehicle_zone", "zones", ["zone_id"], ["id"])
        batch.create_index("ix_vehicles_zone_id", ["zone_id"])

    with op.batch_alter_table("subscriptions") as batch:
        batch.add_column(sa.Column("interior_day_notes", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("subscriptions") as batch:
        batch.drop_column("interior_day_notes")

    with op.batch_alter_table("vehicles") as batch:
        batch.drop_index("ix_vehicles_zone_id")
        batch.drop_constraint("fk_vehicle_zone", type_="foreignkey")
        batch.drop_column("zone_id")
        batch.alter_column("parking_number", existing_type=sa.String(60),
                           type_=sa.String(20), existing_nullable=False)
        batch.alter_column("registration", existing_type=sa.String(20),
                           type_=sa.String(12), existing_nullable=True)

    with op.batch_alter_table("customers") as batch:
        batch.drop_column("alternate_names")
        batch.alter_column("email", existing_type=sa.String(254), nullable=False)
        batch.alter_column("login_id", existing_type=sa.Uuid(), nullable=False)

    op.drop_index("ix_zones_society_id", table_name="zones")
    op.drop_table("zones")
