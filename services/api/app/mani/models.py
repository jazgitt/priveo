import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.mani.types import Embedding
from app.platform.db import Base, UtcDateTime, utcnow


@event.listens_for(Base.metadata, "before_create")
def _create_vector_extension(_target, connection, **_kw) -> None:
    """`create_all` (the tests, local development) needs the extension before the first
    vector column. The migration does the same on a real database."""
    if connection.dialect.name == "postgresql":
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


class ManiConversation(Base):
    """One chat between the Founder and Mani. Kept 90 days (D11)."""

    __tablename__ = "mani_conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow, index=True)


class ManiRun(Base):
    """One answer Mani works out: the model calls and tool rounds behind a reply."""

    __tablename__ = "mani_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('running', 'succeeded', 'failed', 'budget_exhausted', 'cancelled')",
            name="mani_runs_status_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mani_conversations.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="running")
    persona_version: Mapped[str] = mapped_column(String(24), default="")
    backend: Mapped[str] = mapped_column(String(24), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    tool_rounds: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class ManiMessage(Base):
    __tablename__ = "mani_messages"
    __table_args__ = (
        CheckConstraint("role in ('user', 'assistant')", name="mani_messages_role_check"),
        Index("ix_mani_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mani_conversations.id", ondelete="CASCADE"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mani_runs.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    # [{"title", "path", "requirement_id", "commit_id", "as_of", "kind"}] for the sources
    # and live tools behind an answer, with the data timestamp.
    citations: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class ManiSource(Base):
    """One indexed file or document. Re-indexed when its content hash changes."""

    __tablename__ = "mani_sources"
    __table_args__ = (
        CheckConstraint("status in ('active', 'deleted', 'failed')", name="mani_sources_status_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    path: Mapped[str] = mapped_column(String(500), unique=True)
    kind: Mapped[str] = mapped_column(String(24), default="doc")  # doc, code, config, data
    title: Mapped[str] = mapped_column(String(300), default="")
    commit_id: Mapped[str] = mapped_column(String(64), default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(12), default="active")
    error: Mapped[str] = mapped_column(Text, default="")
    # Each index records its embedding model and size, so a change can be re-indexed.
    embedding_model: Mapped[str] = mapped_column(String(120), default="")
    embedding_dimensions: Mapped[int] = mapped_column(Integer, default=0)
    indexed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class ManiChunk(Base):
    __tablename__ = "mani_chunks"
    __table_args__ = (UniqueConstraint("source_id", "ordinal", name="uq_mani_chunks_source_ordinal"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mani_sources.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str] = mapped_column(String(300), default="")
    text: Mapped[str] = mapped_column(Text)  # already scrubbed
    requirement_ids: Mapped[list] = mapped_column(JSON, default=list)
    embedding: Mapped[list[float] | None] = mapped_column(Embedding())
    # PostgreSQL only: a GIN index on to_tsvector('english', text) and an HNSW index on
    # embedding are created by the migration, not declared here.


class ManiMemoryFact(Base):
    """Something the Founder told Mani, kept until corrected or deleted. Attributable."""

    __tablename__ = "mani_memory_facts"
    __table_args__ = (
        CheckConstraint("status in ('confirmed', 'tentative')", name="mani_memory_status_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="confirmed")
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mani_messages.id", ondelete="SET NULL"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class ManiModelUsage(Base):
    """What one model call used. No prompt or answer text is stored (D10)."""

    __tablename__ = "mani_model_usage"
    __table_args__ = (
        CheckConstraint("kind in ('chat', 'embedding')", name="mani_usage_kind_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mani_runs.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(12))
    backend: Mapped[str] = mapped_column(String(24))
    model: Mapped[str] = mapped_column(String(120))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    # An estimate from token counts and the model's listed price. Local models cost 0.
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 8), default=Decimal(0))
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, index=True)
