"""Crew work on jobs: checklist progress, outcomes, reassignments, photos, uploads.

The visits and jobs tables are the scheduling module's (0006).

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_checklist_progress",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("item_key", sa.String(40), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_by", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.UniqueConstraint("job_id", "item_key"),
    )
    op.create_index("ix_job_checklist_progress_job_id", "job_checklist_progress", ["job_id"])
    op.create_table(
        "job_outcomes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), nullable=False, unique=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("reason_key", sa.String(40)),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("upload_id", sa.Uuid()),
        sa.Column("by_login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "job_reassignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("from_crew_id", sa.Uuid(), sa.ForeignKey("scheduling_crew.id")),
        sa.Column("to_crew_id", sa.Uuid(), sa.ForeignKey("scheduling_crew.id"),
                  nullable=False),
        sa.Column("by_login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_reassignments_job_id", "job_reassignments", ["job_id"])
    op.create_table(
        "job_timings",
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "crew_photos",
        sa.Column("login_id", sa.Uuid(), sa.ForeignKey("logins.id"), primary_key=True),
        sa.Column("upload_id", sa.Uuid(), nullable=False),
    )
    op.create_table(
        "media_uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id")),
        sa.Column("purpose", sa.String(10), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("stage", sa.String(8)),
        sa.Column("content_type", sa.String(60), nullable=False),
        sa.Column("declared_size_bytes", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(200), nullable=False, unique=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_media_uploads_owner_login_id", "media_uploads", ["owner_login_id"])
    op.create_index("ix_media_uploads_job_id", "media_uploads", ["job_id"])


def downgrade() -> None:
    for table in ("media_uploads", "crew_photos", "job_timings", "job_reassignments",
                  "job_outcomes",
                  "job_checklist_progress"):
        op.drop_table(table)
