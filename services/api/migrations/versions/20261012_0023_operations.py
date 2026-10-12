"""Operations decisions and linked next-day retries."""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("jobs") as b:
        b.add_column(sa.Column("source_job_id", sa.Uuid(), nullable=True))
        b.create_foreign_key("fk_job_source", "jobs", ["source_job_id"], ["id"])
        b.create_unique_constraint("uq_job_source", ["source_job_id"])
    op.create_table(
        "operations_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id"), nullable=False, unique=True),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(200), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("by_login_id", sa.Uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "INSERT INTO operations_decisions (id, job_id, action, reason, note, by_login_id, at) "
        "SELECT id, job_id, 'Skip', '', note, by_login_id, at FROM job_outcomes "
        "WHERE kind = 'skipped'"
    )


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM operations_decisions")):
        raise RuntimeError("Operations history exists; downgrade would lose resolution links.")
    op.drop_table("operations_decisions")
    with op.batch_alter_table("jobs") as b:
        b.drop_constraint("uq_job_source", type_="unique")
        b.drop_constraint("fk_job_source", type_="foreignkey")
        b.drop_column("source_job_id")
