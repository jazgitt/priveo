"""Plan extensions and the Manager's attendance and hours log (CRW-MGR-02, 04, 05).

Revision ID: 0021
Revises: 0019
"""
import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan_extensions",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("vehicle_id", sa.Uuid, sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("job_id", sa.Uuid, sa.ForeignKey("jobs.id"), nullable=False, unique=True),
        sa.Column("on_date", sa.Date, nullable=False),
        sa.Column("by_login_id", sa.Uuid, sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_plan_extensions_vehicle_id", "plan_extensions", ["vehicle_id"])
    op.create_table(
        "crew_manager_changes",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("society_id", sa.Uuid, sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("crew_id", sa.Uuid, sa.ForeignKey("scheduling_crew.id"), nullable=False),
        sa.Column("by_login_id", sa.Uuid, sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("on_date", sa.Date, nullable=False),
        sa.Column("detail", sa.Text, nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_crew_manager_changes_society_id", "crew_manager_changes",
                    ["society_id"])
    op.create_index("ix_crew_manager_changes_crew_id", "crew_manager_changes", ["crew_id"])


def downgrade() -> None:
    op.drop_table("crew_manager_changes")
    op.drop_table("plan_extensions")
