"""Hand placements are locked by default (item 15).

A locked hand placement keeps its crew, day and time through a run. An
unlocked one may be moved. Existing hand placements are backfilled as locked,
so no run moves them.

Revision ID: 0053
Revises: 0052
"""
import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("hand_locked", sa.Boolean(), nullable=False,
                                   server_default=sa.false()))
    jobs = sa.table("jobs", sa.column("manual", sa.Boolean()), sa.column("hand_locked", sa.Boolean()))
    op.execute(jobs.update().where(jobs.c.manual.is_(True)).values(hand_locked=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("hand_locked")
