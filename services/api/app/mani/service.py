"""What the Founder-only routes do, apart from the web layer. Each function takes a
session and commits its own changes, like the rest of the API."""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.mani.config import ManiSettings
from app.mani.models import (
    ManiChunk,
    ManiConversation,
    ManiMemoryFact,
    ManiMessage,
    ManiModelUsage,
    ManiRun,
    ManiSource,
)
from app.mani.schemas import (
    CitationOut,
    ConversationDetailOut,
    ConversationOut,
    MemoryFactOut,
    MessageOut,
    SourceOut,
    SourcesOut,
    UsageDayOut,
    UsageOut,
)
from app.platform import clock
from app.platform.db import utcnow
from app.platform.errors import ApiError

USAGE_DAYS = 30
# A run still "running" after this long is a crash, not work in progress.
STALE_RUN = timedelta(minutes=10)


def _not_found(what: str) -> ApiError:
    return ApiError("not_found", f"There is no such {what}.", 404)


# ---- Budget and usage ---------------------------------------------------------------------


def _total_cost(db: Session) -> Decimal:
    return Decimal(str(db.scalar(select(func.coalesce(func.sum(ManiModelUsage.cost_usd), 0))) or 0))


def budget_exhausted(db: Session, settings: ManiSettings) -> bool:
    """D18: the total usage limit, with no time period, is used up."""
    return _total_cost(db) >= Decimal(str(settings.budget_usd))


def usage(db: Session, settings: ManiSettings, now: datetime) -> UsageOut:
    spent = float(_total_cost(db))
    failed = db.scalar(select(func.count()).select_from(ManiModelUsage).where(ManiModelUsage.ok.is_(False))) or 0
    average = db.scalar(select(func.avg(ManiModelUsage.latency_ms))) or 0

    # The last 30 India days, today last. A call at 20:00 UTC is 01:30 the next India day.
    today = now.astimezone(clock.IST).date()
    first = today - timedelta(days=USAGE_DAYS - 1)
    start = datetime.combine(first, datetime.min.time(), tzinfo=clock.IST)
    days: dict = {}
    costs: dict = {}
    for i in range(USAGE_DAYS):
        d = first + timedelta(days=i)
        days[d] = UsageDayOut(day=d.isoformat(), calls=0, prompt_tokens=0, completion_tokens=0, cost_usd=0.0)
        costs[d] = Decimal(0)
    rows = db.execute(select(ManiModelUsage.created_at, ManiModelUsage.prompt_tokens,
                             ManiModelUsage.completion_tokens, ManiModelUsage.cost_usd)
                      .where(ManiModelUsage.created_at >= start)).all()
    for created_at, prompt, completion, cost in rows:
        d = created_at.astimezone(clock.IST).date()
        if d not in days:  # a row after "now"
            continue
        days[d].calls += 1
        days[d].prompt_tokens += prompt or 0
        days[d].completion_tokens += completion or 0
        costs[d] += Decimal(str(cost or 0))
    for d, entry in days.items():
        entry.cost_usd = float(costs[d])
    return UsageOut(
        budget_usd=settings.budget_usd, spent_usd=spent,
        remaining_usd=max(settings.budget_usd - spent, 0.0),
        budget_exhausted=budget_exhausted(db, settings),
        failed_calls=failed, average_latency_ms=int(round(float(average))),
        days=list(days.values()))


# ---- Conversations ------------------------------------------------------------------------


def _conversation_out(c: ManiConversation) -> ConversationOut:
    return ConversationOut(id=c.id, title=c.title, created_at=c.created_at, updated_at=c.updated_at)


def own_conversation(db: Session, login_id: uuid.UUID, conversation_id: uuid.UUID) -> ManiConversation:
    """Someone else's conversation looks the same as a missing one."""
    c = db.get(ManiConversation, conversation_id)
    if c is None or c.login_id != login_id:
        raise _not_found("conversation")
    return c


def list_conversations(db: Session, login_id: uuid.UUID) -> list[ConversationOut]:
    rows = db.scalars(select(ManiConversation).where(ManiConversation.login_id == login_id)
                      .order_by(ManiConversation.updated_at.desc(), ManiConversation.created_at.desc())).all()
    return [_conversation_out(c) for c in rows]


def create_conversation(db: Session, login_id: uuid.UUID) -> ConversationOut:
    c = ManiConversation(login_id=login_id, title="")
    db.add(c)
    db.commit()
    return _conversation_out(c)


def conversation_detail(db: Session, login_id: uuid.UUID, conversation_id: uuid.UUID) -> ConversationDetailOut:
    c = own_conversation(db, login_id, conversation_id)
    rows = db.scalars(select(ManiMessage).where(ManiMessage.conversation_id == c.id)
                      .order_by(ManiMessage.created_at, ManiMessage.id)).all()
    messages = []
    for m in rows:
        citations = []
        for raw in m.citations or []:
            try:
                citations.append(CitationOut.model_validate(raw))
            except ValueError:  # an old or odd entry never breaks the page
                continue
        messages.append(MessageOut(id=m.id, role=m.role, content=m.content, citations=citations,
                                   created_at=m.created_at))
    return ConversationDetailOut(**_conversation_out(c).model_dump(), messages=messages)


def run_in_progress(db: Session, conversation_id: uuid.UUID, now: datetime) -> bool:
    return (db.scalar(select(func.count()).select_from(ManiRun).where(
        ManiRun.conversation_id == conversation_id, ManiRun.status == "running",
        ManiRun.started_at >= now - STALE_RUN)) or 0) > 0


def delete_conversation_rows(db: Session, ids: list[uuid.UUID]) -> None:
    """Removes conversations with their messages and runs. Usage rows are counts, not
    content, so they stay with run_id cleared. Done by hand so it does not depend on the
    database enforcing foreign-key actions. Does not commit."""
    if not ids:
        return
    run_ids = select(ManiRun.id).where(ManiRun.conversation_id.in_(ids))
    message_ids = select(ManiMessage.id).where(ManiMessage.conversation_id.in_(ids))
    db.execute(update(ManiModelUsage).where(ManiModelUsage.run_id.in_(run_ids)).values(run_id=None))
    db.execute(update(ManiMemoryFact).where(ManiMemoryFact.source_message_id.in_(message_ids))
               .values(source_message_id=None))
    db.execute(update(ManiMessage).where(ManiMessage.conversation_id.in_(ids)).values(run_id=None))
    db.execute(delete(ManiMessage).where(ManiMessage.conversation_id.in_(ids)))
    db.execute(delete(ManiRun).where(ManiRun.conversation_id.in_(ids)))
    db.execute(delete(ManiConversation).where(ManiConversation.id.in_(ids)))


def delete_conversation(db: Session, login_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
    c = own_conversation(db, login_id, conversation_id)
    delete_conversation_rows(db, [c.id])
    db.commit()


def finish_turn(db: Session, conversation_id: uuid.UUID, since: datetime, status: str,
                message: str = "") -> None:
    """After a stream: close a run the agent left "running" (a disconnect or a crash) and
    mark the conversation as just used."""
    db.execute(update(ManiRun).where(
        ManiRun.conversation_id == conversation_id, ManiRun.status == "running",
        ManiRun.started_at >= since).values(status=status, error=message, finished_at=utcnow()))
    db.execute(update(ManiConversation).where(ManiConversation.id == conversation_id)
               .values(updated_at=utcnow()))
    db.commit()


# ---- Sources ------------------------------------------------------------------------------


def sources(db: Session) -> SourcesOut:
    counts = dict(db.execute(select(ManiChunk.source_id, func.count()).group_by(ManiChunk.source_id)).all())
    rows = db.scalars(select(ManiSource).order_by(ManiSource.path)).all()
    items = [SourceOut(path=s.path, kind=s.kind, title=s.title, status=s.status, indexed_at=s.indexed_at,
                       commit_id=s.commit_id, chunks=counts.get(s.id, 0)) for s in rows]
    active = [s for s in rows if s.status == "active" and s.indexed_at is not None]
    latest = max(active, key=lambda s: s.indexed_at, default=None)
    return SourcesOut(items=items, embedding_model=latest.embedding_model if latest else "",
                      last_indexed_at=latest.indexed_at if latest else None)


# ---- Memory -------------------------------------------------------------------------------


def _memory_out(f: ManiMemoryFact) -> MemoryFactOut:
    return MemoryFactOut(id=f.id, text=f.text, status=f.status, created_at=f.created_at)


def _fact(db: Session, fact_id: uuid.UUID) -> ManiMemoryFact:
    f = db.get(ManiMemoryFact, fact_id)
    if f is None or f.deleted_at is not None:
        raise _not_found("memory")
    return f


def memory(db: Session) -> list[MemoryFactOut]:
    rows = db.scalars(select(ManiMemoryFact).where(ManiMemoryFact.deleted_at.is_(None))
                      .order_by(ManiMemoryFact.created_at.desc(), ManiMemoryFact.id)).all()
    return [_memory_out(f) for f in rows]


def patch_memory(db: Session, fact_id: uuid.UUID, text: str | None, status: str | None) -> MemoryFactOut:
    f = _fact(db, fact_id)
    if text is not None:
        if not text.strip():
            raise ApiError("invalid", "The text cannot be empty.", 422)
        f.text = text.strip()
    if status is not None:
        f.status = status
    db.commit()
    return _memory_out(f)


def delete_memory(db: Session, fact_id: uuid.UUID) -> None:
    """Soft delete: the row stays, marked, and is no longer listed or used."""
    _fact(db, fact_id).deleted_at = utcnow()
    db.commit()
