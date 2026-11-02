import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.mani.actions.states import STATES
from app.platform.db import Base, UtcDateTime, utcnow

_STATE_LIST = ", ".join(f"'{s}'" for s in STATES)


class ManiProposal(Base):
    """What Mani proposes to change, exactly. Kept apart from chat messages. The conversation
    and run links are cleared, not cascaded, when a chat is deleted: the proposal belongs to the
    audit trail, which has its own retention."""

    __tablename__ = "mani_proposals"
    __table_args__ = (
        CheckConstraint(f"status in ({_STATE_LIST})", name="mani_proposals_status_check"),
        Index("ix_mani_proposals_status_expires", "status", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mani_conversations.id", ondelete="SET NULL"), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mani_runs.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    # sha256 of the action and params. An approval binds to this and nothing else.
    params_hash: Mapped[str] = mapped_column(String(64))
    # The typed preview shown to the Founder: affected records, before and after, side effects.
    preview: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"<table>:<id>": "<updated_at or version>"} rechecked immediately before execution.
    record_versions: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow, index=True)


class ManiApproval(Base):
    """The Founder's approval of one proposal. The code itself is never stored here."""

    __tablename__ = "mani_approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mani_proposals.id", ondelete="CASCADE"), unique=True)
    login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"))
    session_id: Mapped[str] = mapped_column(String(64), default="")
    params_hash: Mapped[str] = mapped_column(String(64))
    approved_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)


class ManiExecution(Base):
    """One run of an approved proposal. The unique key makes a repeat a no-op."""

    __tablename__ = "mani_executions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_mani_executions_idempotency_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mani_proposals.id", ondelete="CASCADE"), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    outcome: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")


class ManiAudit(Base):
    """One line per state change of a proposal: who, what, when. Kept 3 months (D11)."""

    __tablename__ = "mani_audit"
    __table_args__ = (Index("ix_mani_audit_proposal_created", "proposal_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mani_proposals.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))  # None: the system (expiry)
    event: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str] = mapped_column(String(20), default="")
    to_status: Mapped[str] = mapped_column(String(20), default="")
    # Content-free facts only (ids, counts, error class). Never a code or a prompt.
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, index=True)
