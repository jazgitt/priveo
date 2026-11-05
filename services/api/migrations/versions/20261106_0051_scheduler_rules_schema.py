"""Schema for the scheduler rules v1.2 (SCHS-01). Tables and columns only.

Everything is new, unused, and nullable or defaulted, so a site on version 1
behaves as before. Later stories fill and read these.

Revision ID: 0051
Revises: 0050
"""
import sqlalchemy as sa
from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "society_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("society_id", "key"),
    )
    op.create_index("ix_society_settings_society_id", "society_settings", ["society_id"])

    op.create_table(
        "break_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("crew_id", sa.Uuid(), sa.ForeignKey("scheduling_crew.id"), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=True),
        sa.Column("end_minute", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_break_rules_society_id", "break_rules", ["society_id"])

    op.create_table(
        "interior_entitlements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subscription_id", sa.Uuid(), sa.ForeignKey("subscriptions.id"), nullable=True),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("service_week_start", sa.Date(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("completed_on", sa.Date(), nullable=True),
        sa.Column("waived_reason", sa.String(160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vehicle_id", "service_week_start", "seq"),
    )
    op.create_index("ix_interior_entitlements_subscription_id", "interior_entitlements",
                    ["subscription_id"])
    op.create_index("ix_interior_entitlements_vehicle_id", "interior_entitlements", ["vehicle_id"])
    op.create_index("ix_interior_entitlements_service_week_start", "interior_entitlements",
                    ["service_week_start"])

    op.create_table(
        "schedule_run_config",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("schedule_id", sa.Uuid(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("values", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schedule_run_config_schedule_id", "schedule_run_config", ["schedule_id"])

    op.create_table(
        "schedule_findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("schedule_id", sa.Uuid(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schedule_findings_schedule_id", "schedule_findings", ["schedule_id"])

    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("service_week_start", sa.Date(), nullable=True))
        batch.add_column(sa.Column("cross_zone_reason", sa.String(120), nullable=True))
        batch.add_column(sa.Column("reason_code", sa.String(40), nullable=True))
    with op.batch_alter_table("scheduling_crew") as batch:
        batch.add_column(sa.Column("reporting_minute", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("first_job_minute", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("home_zone_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_scheduling_crew_home_zone", "zones", ["home_zone_id"], ["id"])
    with op.batch_alter_table("cnc_reasons") as batch:
        batch.add_column(sa.Column("defers", sa.Boolean(), nullable=False,
                                   server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("cnc_reasons") as batch:
        batch.drop_column("defers")
    with op.batch_alter_table("scheduling_crew") as batch:
        batch.drop_constraint("fk_scheduling_crew_home_zone", type_="foreignkey")
        batch.drop_column("home_zone_id")
        batch.drop_column("first_job_minute")
        batch.drop_column("reporting_minute")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("reason_code")
        batch.drop_column("cross_zone_reason")
        batch.drop_column("service_week_start")
    op.drop_table("schedule_findings")
    op.drop_table("schedule_run_config")
    op.drop_table("interior_entitlements")
    op.drop_table("break_rules")
    op.drop_table("society_settings")
