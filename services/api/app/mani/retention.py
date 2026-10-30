"""Conversation retention (D11): chats are kept 90 days, then deleted."""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

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
