"""Creating proposals and moving them through their states. Every move writes an audit row.
Nothing here commits: the caller owns the transaction, as in `delete_conversation_rows`."""
import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.mani.actions import states
from app.mani.actions.models import ManiApproval, ManiAudit, ManiExecution, ManiProposal


class ActionError(Exception):
    """Base for the refusals below."""


class IllegalTransition(ActionError):
    pass


class ProposalExpired(ActionError):
    pass


class ParamsMismatch(ActionError):
    """The parameters are not the ones that were previewed and hashed."""


def compute_params_hash(action: str, params: dict[str, Any]) -> str:
    """Stable across key order and processes: sha256 of the action and canonical JSON."""
    body = json.dumps({"action": action, "params": params}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


def write_audit(db: Session, proposal: ManiProposal, event: str, *, actor_id: uuid.UUID | None,
                now: datetime, from_status: str = "", to_status: str = "", ok: bool = True,
                detail: dict | None = None) -> ManiAudit:
    row = ManiAudit(proposal_id=proposal.id, action=proposal.action, actor_id=actor_id, event=event,
                    from_status=from_status, to_status=to_status, ok=ok, detail=detail or {},
                    created_at=now)
    db.add(row)
    return row


def create_proposal(db: Session, *, login_id: uuid.UUID, action: str, params: dict[str, Any],
                    preview: dict[str, Any], record_versions: dict[str, str], now: datetime,
                    conversation_id: uuid.UUID | None = None,
                    run_id: uuid.UUID | None = None) -> ManiProposal:
    """A new proposal in `draft`, expiring after the approval window. Not yet shown for approval."""
    proposal = ManiProposal(
        id=uuid.uuid4(), conversation_id=conversation_id, run_id=run_id, action=action,
        params=params, params_hash=compute_params_hash(action, params), preview=preview,
        record_versions=record_versions, status=states.DRAFT, expires_at=now + states.APPROVAL_WINDOW,
        created_by=login_id, created_at=now, updated_at=now)
    db.add(proposal)
    db.flush()
    write_audit(db, proposal, "created", actor_id=login_id, now=now, to_status=states.DRAFT)
    db.flush()
    return proposal


def check_params(proposal: ManiProposal, params_hash: str) -> None:
    """The hash an approval carries must be the stored one, and the stored parameters must
    still produce it (guards a proposal edited in place instead of replaced)."""
    if params_hash != proposal.params_hash:
        raise ParamsMismatch("The approval is for different parameters.")
    if compute_params_hash(proposal.action, proposal.params) != proposal.params_hash:
        raise ParamsMismatch("The stored parameters changed after the proposal was made.")


def is_expired(proposal: ManiProposal, now: datetime) -> bool:
    return proposal.expires_at is not None and now >= proposal.expires_at


def transition(db: Session, proposal: ManiProposal, to: str, *, actor_id: uuid.UUID | None,
               now: datetime, detail: dict | None = None) -> ManiProposal:
    """Moves a proposal to `to` if the table allows it, and records it."""
    current = proposal.status
    if to not in states.TRANSITIONS.get(current, frozenset()):
        raise IllegalTransition(f"A proposal cannot go from {current} to {to}.")
    if to in states.NEEDS_LIVE:
        if is_expired(proposal, now):
            raise ProposalExpired("The approval window has passed.")
        check_params(proposal, proposal.params_hash)
    proposal.status = to
    proposal.updated_at = now
    write_audit(db, proposal, "status", actor_id=actor_id, now=now, from_status=current,
                to_status=to, ok=to != states.FAILED, detail=detail)
    db.flush()
    return proposal


def expire_overdue(db: Session, now: datetime) -> int:
    """Moves every unfinished proposal past its expiry to `expired` (no actor: the system).
    Safe to run again. Does not commit."""
    rows = db.scalars(select(ManiProposal).where(
        ManiProposal.status.in_(states.EXPIRABLE), ManiProposal.expires_at <= now)).all()
    for proposal in rows:
        transition(db, proposal, states.EXPIRED, actor_id=None, now=now)
    return len(rows)


def delete_old_actions(db: Session, cutoff: datetime) -> tuple[int, int]:
    """Deletes audit rows older than `cutoff`, and finished proposals last changed before it
    (with their approvals and executions). Returns (audit rows, proposals). Unfinished
    proposals are never removed. Does not commit."""
    audit = db.execute(delete(ManiAudit).where(ManiAudit.created_at < cutoff)).rowcount or 0
    ids = list(db.scalars(select(ManiProposal.id).where(
        ManiProposal.status.in_(states.TERMINAL), ManiProposal.updated_at < cutoff)))
    if ids:
        db.execute(delete(ManiApproval).where(ManiApproval.proposal_id.in_(ids)))
        db.execute(delete(ManiExecution).where(ManiExecution.proposal_id.in_(ids)))
        db.execute(delete(ManiAudit).where(ManiAudit.proposal_id.in_(ids)))
        db.execute(delete(ManiProposal).where(ManiProposal.id.in_(ids)))
    return audit, len(ids)
