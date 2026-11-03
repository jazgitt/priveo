"""Retention (D11): chats are kept 90 days, the action audit 3 months; open proposals time out."""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mani.actions.service import delete_old_actions, expire_overdue
from app.mani.models import ManiConversation
from app.mani.service import delete_conversation_rows


def delete_old_conversations(db: Session, now: datetime, days: int) -> int:
    """Deletes conversations (with their messages and runs) not updated for more than
    `days` days, and returns how many. Model usage rows are counts, not content, so they
    stay. Safe to run again."""
    cutoff = now - timedelta(days=days)
    ids = list(db.scalars(select(ManiConversation.id).where(ManiConversation.updated_at < cutoff)))
    delete_conversation_rows(db, ids)
    db.commit()
    return len(ids)


def sweep_actions(db: Session, now: datetime, audit_days: int) -> dict[str, int]:
    """Times out proposals past their expiry, then deletes audit rows and finished proposals
    older than `audit_days`. Safe to run again."""
    expired = expire_overdue(db, now)
    audit, proposals = delete_old_actions(db, now - timedelta(days=audit_days))
    db.commit()
    return {"proposals_expired": expired, "audit_deleted": audit, "proposals_deleted": proposals}
