"""Scheduling: crew for the scheduler, schedules, visits, jobs and the change log.

Revision ID: 0006
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
# The slice was asked to name '20261010_0004_onboarding_confirmed'. The chain
# on this branch calls that revision "0004". Re-chain when the branches merge.
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduling_crew",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False,
                  unique=True),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("role", sa.String(8), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("paired_member_id", sa.Uuid(), sa.ForeignKey("scheduling_crew.id")),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_scheduling_crew_society_id", "scheduling_crew", ["society_id"])
    op.create_table(
        "scheduling_crew_exceptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("crew_id", sa.Uuid(), sa.ForeignKey("scheduling_crew.id"), nullable=False),
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("from_minute", sa.Integer()),
        sa.UniqueConstraint("crew_id", "on_date"),
    )
    op.create_index("ix_scheduling_crew_exceptions_crew_id", "scheduling_crew_exceptions",
                    ["crew_id"])
    op.create_table(
        "schedules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("society_id", sa.Uuid(), sa.ForeignKey("societies.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True)),
        sa.Column("frozen_by", sa.Uuid(), sa.ForeignKey("logins.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("society_id", "start_date"),
    )
    op.create_index("ix_schedules_society_id", "schedules", ["society_id"])
    op.create_table(
        "visits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("schedule_id", sa.Uuid(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.UniqueConstraint("schedule_id", "vehicle_id", "date"),
    )
    op.create_index("ix_visits_schedule_id", "visits", ["schedule_id"])
    op.create_index("ix_visits_vehicle_id", "visits", ["vehicle_id"])
    op.create_index("ix_visits_date", "visits", ["date"])
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("visit_id", sa.Uuid(), sa.ForeignKey("visits.id"), nullable=False),
        sa.Column("service", sa.String(24), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("crew_id", sa.Uuid(), sa.ForeignKey("scheduling_crew.id")),
        sa.Column("start_minute", sa.Integer()),
        sa.Column("finish_by_minute", sa.Integer()),
        sa.Column("addon_request_id", sa.Uuid(), sa.ForeignKey("addon_requests.id")),
        sa.Column("manual", sa.Boolean(), nullable=False),
        sa.Column("late", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
    )
    op.create_index("ix_jobs_visit_id", "jobs", ["visit_id"])
    op.create_index("ix_jobs_crew_id", "jobs", ["crew_id"])
    op.create_table(
        "scheduling_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("schedule_id", sa.Uuid(), sa.ForeignKey("schedules.id"), nullable=False),
        sa.Column("admin_login_id", sa.Uuid(), sa.ForeignKey("logins.id")),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scheduling_events_schedule_id", "scheduling_events", ["schedule_id"])


def downgrade() -> None:
    op.drop_table("scheduling_events")
    op.drop_table("jobs")
    op.drop_table("visits")
    op.drop_table("schedules")
    op.drop_table("scheduling_crew_exceptions")
    op.drop_table("scheduling_crew")
