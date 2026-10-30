"""What the Founder asked Mani to remember. Every fact says who told it and in which message,
and can be listed and forgotten. Forgetting is a soft delete (`deleted_at`): the model never
sees the fact again, but the row stays for an audit."""
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mani.models import ManiMemoryFact

PROMPT_FACTS = 30  # the newest confirmed facts shown to the model each turn


def remember(db: Session, login_id: uuid.UUID, text: str,
             source_message_id: uuid.UUID | None) -> ManiMemoryFact:
    text = " ".join(text.split())
    if not text:
        raise ValueError("There is nothing to remember.")
    for fact in list_facts(db):  # the same words again are not stored twice
        if fact.text.casefold() == text.casefold():
            return fact
    fact = ManiMemoryFact(text=text, status="confirmed", source_message_id=source_message_id,
                          created_by=login_id)
    db.add(fact)
    db.flush()
    return fact


def list_facts(db: Session, *, limit: int | None = None, confirmed_only: bool = False) -> list[ManiMemoryFact]:
    """Facts not forgotten, newest first."""
    query = select(ManiMemoryFact).where(ManiMemoryFact.deleted_at.is_(None))
    if confirmed_only:
        query = query.where(ManiMemoryFact.status == "confirmed")
    query = query.order_by(ManiMemoryFact.created_at.desc(), ManiMemoryFact.id)
    if limit:
        query = query.limit(limit)
    return list(db.scalars(query))


def forget(db: Session, fact_id: uuid.UUID) -> bool:
    fact = db.get(ManiMemoryFact, fact_id)
    if fact is None or fact.deleted_at is not None:
        return False
    fact.deleted_at = datetime.now(UTC)
    db.flush()
    return True


def search_forget(db: Session, phrase: str) -> list[ManiMemoryFact]:
    """Live facts that match `phrase`: the whole phrase, else every word of it (words of
    three letters or more), ignoring case. The caller decides what to delete."""
    phrase = " ".join(phrase.split()).casefold()
    if not phrase:
        return []
    facts = list_facts(db)
    whole = [f for f in facts if phrase in f.text.casefold()]
    if whole:
        return whole
    words = [w for w in re.findall(r"\w+", phrase) if len(w) >= 3]
    return [f for f in facts if words and all(w in f.text.casefold() for w in words)]
