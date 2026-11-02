"""Mani Walk: proposals, approvals, executions and the action audit (records only).

Revision ID: 0043
Revises: 0042
"""
import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

STATES = ("draft", "awaiting_approval", "approved", "executing", "succeeded", "failed",
          "rejected", "cancelled", "expired", "invalidated")


def _uuid():
    return sa.Uuid()


def _ts():
    return sa.DateTime(timezone=True)


def upgrade():
    op.create_table(
        "mani_proposals",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("conversation_id", _uuid(), sa.ForeignKey("mani_conversations.id", ondelete="SET NULL")),
        sa.Column("run_id", _uuid(), sa.ForeignKey("mani_runs.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("params_hash", sa.String(64), nullable=False),
        sa.Column("preview", sa.JSON(), nullable=False),
        sa.Column("record_versions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("expires_at", _ts()),
        sa.Column("created_by", _uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.Column("updated_at", _ts(), nullable=False),
        sa.CheckConstraint("status in (" + ", ".join(f"'{s}'" for s in STATES) + ")",
                           name="mani_proposals_status_check"),
    )
    op.create_index("ix_mani_proposals_conversation_id", "mani_proposals", ["conversation_id"])
    op.create_index("ix_mani_proposals_updated_at", "mani_proposals", ["updated_at"])
    op.create_index("ix_mani_proposals_status_expires", "mani_proposals", ["status", "expires_at"])

    op.create_table(
        "mani_approvals",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("proposal_id", _uuid(),
                  sa.ForeignKey("mani_proposals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("login_id", _uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("params_hash", sa.String(64), nullable=False),
        sa.Column("approved_at", _ts(), nullable=False),
    )

    op.create_table(
        "mani_executions",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("proposal_id", _uuid(),
                  sa.ForeignKey("mani_proposals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("started_at", _ts(), nullable=False),
        sa.Column("finished_at", _ts()),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("idempotency_key", name="uq_mani_executions_idempotency_key"),
    )

    op.create_table(
        "mani_audit",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("proposal_id", _uuid(), sa.ForeignKey("mani_proposals.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("actor_id", _uuid(), sa.ForeignKey("logins.id")),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=False, server_default=""),
        sa.Column("to_status", sa.String(20), nullable=False, server_default=""),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", _ts(), nullable=False),
    )
    op.create_index("ix_mani_audit_proposal_created", "mani_audit", ["proposal_id", "created_at"])
    op.create_index("ix_mani_audit_created_at", "mani_audit", ["created_at"])


def downgrade():
    for table in ("mani_audit", "mani_executions", "mani_approvals", "mani_proposals"):
        op.drop_table(table)
