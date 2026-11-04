"""Scheduled jobs: the on/off switch and the run record (ADM-OPS-05 to ADM-OPS-09).

`cron_jobs` holds one switch per job, seeded with the owner's defaults of
05-Nov-26. The old setting `schedule.auto_enabled` becomes the switch of
`automatic-planning` and is removed. `cron_runs` records each call of a job.

Revision ID: 0050
Revises: 0049
"""
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None

DEFAULTS = {
    "complaints-overdue": True,
    "payments-daily": True,
    "freeze-due": False,
    "automatic-planning": False,
    "renewal-reminders": False,
    "checkin-notify": False,
    "mani-retention": False,
}


def upgrade() -> None:
    cron_jobs = op.create_table(
        "cron_jobs",
        sa.Column("job", sa.String(40), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_by_login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "cron_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job", sa.String(40), nullable=False),
        sa.Column("trigger", sa.String(10), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(300), nullable=False, server_default=""),
    )
    op.create_index("cron_runs_job_started", "cron_runs", ["job", "started_at"])

    conn = op.get_bind()
    old = conn.execute(
        sa.text("SELECT value FROM system_settings WHERE key = 'schedule.auto_enabled'")).scalar()
    defaults = dict(DEFAULTS)
    if old is not None and str(old).strip() == "1":
        defaults["automatic-planning"] = True  # keep what the admin had chosen
    now = datetime.now(UTC)
    op.bulk_insert(cron_jobs, [
        {"job": job, "enabled": enabled, "updated_by_login_id": None, "updated_at": now}
        for job, enabled in defaults.items()
    ])
    conn.execute(sa.text("DELETE FROM system_settings WHERE key = 'schedule.auto_enabled'"))


def downgrade() -> None:
    conn = op.get_bind()
    on = conn.execute(
        sa.text("SELECT enabled FROM cron_jobs WHERE job = 'automatic-planning'")).scalar()
    conn.execute(sa.text(
        "INSERT INTO system_settings (key, value, updated_at) VALUES ('schedule.auto_enabled', :v, :t)"
    ), {"v": "1" if on else "0", "t": datetime.now(UTC)})
    op.drop_index("cron_runs_job_started", table_name="cron_runs")
    op.drop_table("cron_runs")
    op.drop_table("cron_jobs")
