"""Several home zones for each cleaner (SCHS-29, item 8).

A cleaner's home zones move from one column to an association table. The
existing single zone is copied across, then the column goes.

Revision ID: 0052
Revises: 0051
"""
import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduling_crew_home_zones",
        sa.Column("crew_id", sa.Uuid(), sa.ForeignKey("scheduling_crew.id"), primary_key=True),
        sa.Column("zone_id", sa.Uuid(), sa.ForeignKey("zones.id"), primary_key=True),
    )
    op.create_index("ix_scheduling_crew_home_zones_zone_id", "scheduling_crew_home_zones", ["zone_id"])
    op.execute(
        "INSERT INTO scheduling_crew_home_zones (crew_id, zone_id) "
        "SELECT id, home_zone_id FROM scheduling_crew WHERE home_zone_id IS NOT NULL")
    with op.batch_alter_table("scheduling_crew") as batch:
        batch.drop_constraint("fk_scheduling_crew_home_zone", type_="foreignkey")
        batch.drop_column("home_zone_id")


def downgrade() -> None:
    with op.batch_alter_table("scheduling_crew") as batch:
        batch.add_column(sa.Column("home_zone_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_scheduling_crew_home_zone", "zones", ["home_zone_id"], ["id"])
    # Several zones cannot all fit one column: each cleaner keeps one of them.
    op.execute(
        "UPDATE scheduling_crew SET home_zone_id = ("
        "SELECT zone_id FROM scheduling_crew_home_zones "
        "WHERE scheduling_crew_home_zones.crew_id = scheduling_crew.id LIMIT 1)")
    op.drop_index("ix_scheduling_crew_home_zones_zone_id", table_name="scheduling_crew_home_zones")
    op.drop_table("scheduling_crew_home_zones")
