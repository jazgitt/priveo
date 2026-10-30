"""Mani Bond: conversations, runs, messages, sources, chunks, memory and model usage.

Chunks hold a vector(1024) on PostgreSQL (pgvector) and a JSON text on SQLite. The
similarity and text-search indexes are PostgreSQL only.

Revision ID: 0042
Revises: 0041
"""
import sqlalchemy as sa
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

DIMENSIONS = 1024


def _uuid():
    return sa.Uuid()


def _ts():
    return sa.DateTime(timezone=True)


def upgrade():
    pg = op.get_bind().dialect.name == "postgresql"
    if pg:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        from pgvector.sqlalchemy import Vector
        embedding = Vector(DIMENSIONS)
    else:
        embedding = sa.Text()

    op.create_table(
        "mani_conversations",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("login_id", _uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False, server_default=""),
        sa.Column("created_at", _ts(), nullable=False),
        sa.Column("updated_at", _ts(), nullable=False),
    )
    op.create_index("ix_mani_conversations_login_id", "mani_conversations", ["login_id"])
    op.create_index("ix_mani_conversations_updated_at", "mani_conversations", ["updated_at"])

    op.create_table(
        "mani_runs",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("conversation_id", _uuid(),
                  sa.ForeignKey("mani_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="running"),
        sa.Column("persona_version", sa.String(24), nullable=False, server_default=""),
        sa.Column("backend", sa.String(24), nullable=False, server_default=""),
        sa.Column("model", sa.String(120), nullable=False, server_default=""),
        sa.Column("tool_rounds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", _ts(), nullable=False),
        sa.Column("finished_at", _ts()),
        sa.CheckConstraint(
            "status in ('running', 'succeeded', 'failed', 'budget_exhausted', 'cancelled')",
            name="mani_runs_status_check"),
    )
    op.create_index("ix_mani_runs_conversation_id", "mani_runs", ["conversation_id"])

    op.create_table(
        "mani_messages",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("conversation_id", _uuid(),
                  sa.ForeignKey("mani_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", _uuid(), sa.ForeignKey("mani_runs.id", ondelete="SET NULL")),
        sa.Column("role", sa.String(12), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.CheckConstraint("role in ('user', 'assistant')", name="mani_messages_role_check"),
    )
    op.create_index("ix_mani_messages_conversation_created", "mani_messages",
                    ["conversation_id", "created_at"])

    op.create_table(
        "mani_sources",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("path", sa.String(500), nullable=False, unique=True),
        sa.Column("kind", sa.String(24), nullable=False, server_default="doc"),
        sa.Column("title", sa.String(300), nullable=False, server_default=""),
        sa.Column("commit_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(12), nullable=False, server_default="active"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("embedding_model", sa.String(120), nullable=False, server_default=""),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("indexed_at", _ts()),
        sa.CheckConstraint("status in ('active', 'deleted', 'failed')", name="mani_sources_status_check"),
    )

    op.create_table(
        "mani_chunks",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("source_id", _uuid(),
                  sa.ForeignKey("mani_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(300), nullable=False, server_default=""),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("requirement_ids", sa.JSON(), nullable=False),
        sa.Column("embedding", embedding),
        sa.UniqueConstraint("source_id", "ordinal", name="uq_mani_chunks_source_ordinal"),
    )
    op.create_index("ix_mani_chunks_source_id", "mani_chunks", ["source_id"])
    if pg:
        op.execute("CREATE INDEX ix_mani_chunks_text_search ON mani_chunks "
                   "USING gin (to_tsvector('english', text))")
        op.execute("CREATE INDEX ix_mani_chunks_embedding ON mani_chunks "
                   "USING hnsw (embedding vector_cosine_ops)")

    op.create_table(
        "mani_memory_facts",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="confirmed"),
        sa.Column("source_message_id", _uuid(), sa.ForeignKey("mani_messages.id", ondelete="SET NULL")),
        sa.Column("created_by", _uuid(), sa.ForeignKey("logins.id"), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.Column("deleted_at", _ts()),
        sa.CheckConstraint("status in ('confirmed', 'tentative')", name="mani_memory_status_check"),
    )

    op.create_table(
        "mani_model_usage",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("run_id", _uuid(), sa.ForeignKey("mani_runs.id", ondelete="SET NULL")),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("backend", sa.String(24), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(14, 8), nullable=False, server_default="0"),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", _ts(), nullable=False),
        sa.CheckConstraint("kind in ('chat', 'embedding')", name="mani_usage_kind_check"),
    )
    op.create_index("ix_mani_model_usage_created_at", "mani_model_usage", ["created_at"])


def downgrade():
    for table in ("mani_model_usage", "mani_memory_facts", "mani_chunks", "mani_sources",
                  "mani_messages", "mani_runs", "mani_conversations"):
        op.drop_table(table)
    # The extension is left in place: other tables may come to use it.
