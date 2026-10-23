"""Crew job queue: a sequence per crew member per day, and an unlock flag.

S-13, C-01, C-02, C-04, B-06. Backfills the sequence of every job that has a
crew member from its visit date, crew and start time.

Revision ID: 0036
Revises: 0035
"""
import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("sequence", sa.Integer, nullable=True))
    op.add_column(
        "jobs",
        sa.Column("queue_unlocked", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT j.id, j.crew_id, v.date FROM jobs j JOIN visits v ON v.id = j.visit_id "
        "WHERE j.crew_id IS NOT NULL AND j.status <> 'Skipped' "
        "ORDER BY v.date, j.crew_id, (j.start_minute IS NULL), j.start_minute, j.id"
    )).all()
    counter: dict = {}
    for job_id, crew_id, day in rows:
        key = (crew_id, day)
        counter[key] = counter.get(key, 0) + 1
        bind.execute(sa.text("UPDATE jobs SET sequence = :s WHERE id = :i"),
                     {"s": counter[key], "i": job_id})


def downgrade():
    op.drop_column("jobs", "queue_unlocked")
    op.drop_column("jobs", "sequence")
