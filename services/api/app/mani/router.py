import dataclasses
import json
import logging
import uuid
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.changes.rules import Clock, get_now
from app.identity.service import User
from app.mani import service
from app.mani.access import require_founder
from app.mani.config import ManiSettings, get_mani_settings
from app.mani.contracts import Agent, TurnEvent
from app.mani.schemas import (
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    MemoryFactOut,
    MemoryListOut,
    MemoryPatchIn,
    SendMessageIn,
    SourcesOut,
    StatusOut,
    UsageOut,
)
from app.platform.db import get_db, utcnow
from app.platform.errors import ApiError

log = logging.getLogger("priveo.mani")

admin = APIRouter(prefix="/v1/admin/mani", tags=["mani"])


def get_agent() -> Agent:
    """The agent that answers a message. It is built when first needed, so the API still
    starts (and every other route works) while the agent is missing or misconfigured."""
    try:
        from app.mani.agent import build_agent

        return build_agent()
    except Exception:
        log.exception("Mani's agent could not be built")
        raise ApiError("not_ready", "Mani is not ready", 503) from None


@admin.get("/status", response_model=StatusOut)
def mani_status(_founder: User = Depends(require_founder),
                settings: ManiSettings = Depends(get_mani_settings),
                db: Session = Depends(get_db)) -> StatusOut:
    """Who may use Mani and which model backend is configured. The key is never shown."""
    return StatusOut(backend=settings.backend, chat_model=settings.chat_model,
                     embedding_model=settings.embedding_model,
                     budget_exhausted=service.budget_exhausted(db, settings))


# ---- Conversations ------------------------------------------------------------------------


@admin.get("/conversations", response_model=ConversationListOut)
def list_conversations(founder: User = Depends(require_founder),
                       db: Session = Depends(get_db)) -> ConversationListOut:
    return ConversationListOut(items=service.list_conversations(db, founder.id))


@admin.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(founder: User = Depends(require_founder),
                        db: Session = Depends(get_db)) -> ConversationOut:
    """An empty conversation. The agent titles it from the first message."""
    return service.create_conversation(db, founder.id)


@admin.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: uuid.UUID, founder: User = Depends(require_founder),
                     db: Session = Depends(get_db)) -> ConversationDetailOut:
    return service.conversation_detail(db, founder.id, conversation_id)


@admin.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: uuid.UUID, founder: User = Depends(require_founder),
                        db: Session = Depends(get_db)) -> Response:
    service.delete_conversation(db, founder.id, conversation_id)
    return Response(status_code=204)


# ---- The stream ---------------------------------------------------------------------------


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return str(value)


def frame(kind: str, data: dict) -> str:
    """One server-sent event: `data: {...}` and a blank line."""
    return "data: " + json.dumps({"kind": kind, "data": data}, default=_json_default) + "\n\n"


def stream_turn(bind, agent: Agent, conversation_id: uuid.UUID, login_id: uuid.UUID, text: str,
                started: datetime) -> Iterator[str]:
    """Runs one turn and yields its events.

    The stream gets its own session. A request's session (from `get_db`) belongs to the
    request: tying a long stream to it would hold a database connection open, idle, for
    the whole answer, and the framework decides when it closes. Here the session lives
    exactly as long as the stream. Work is committed before the `answer` and `done` events
    go out, so a client that reads either event and then reloads sees the saved messages.
    A disconnect, an agent exception or an agent that stops early still ends with the run
    closed in the database; an exception also sends `error` then `done`."""
    run_id = ""
    with Session(bind, expire_on_commit=False) as db:
        events = None
        outcome, message = "failed", "The answer stopped early."
        try:
            events = iter(agent.run_turn(db, conversation_id=conversation_id, login_id=login_id,
                                         user_text=text))
            for event in events:
                data = event.data if isinstance(event, TurnEvent) else {}
                if event.kind == "run_started":
                    run_id = str(data.get("run_id", ""))
                if event.kind in ("answer", "done", "budget_exhausted"):
                    db.commit()
                yield frame(event.kind, data)
                if event.kind == "done":
                    outcome = "closed"
                    return
            db.commit()
            yield frame("error", {"message": "Mani stopped before finishing. Please try again."})
            yield frame("done", {"run_id": run_id, "status": "failed"})
        except GeneratorExit:  # the client went away
            outcome, message = "cancelled", "The client disconnected."
            raise
        except Exception:
            log.exception("Mani's turn failed")
            db.rollback()
            yield frame("error", {"message": "Mani could not finish this answer. Please try again."})
            yield frame("done", {"run_id": run_id, "status": "failed"})
        finally:
            close = getattr(events, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    log.exception("Closing the agent's events failed")
            try:
                db.rollback()
                # A run the agent finished is left alone: only "running" ones are closed.
                service.finish_turn(db, conversation_id, started,
                                    "cancelled" if outcome == "cancelled" else "failed",
                                    "" if outcome == "closed" else message)
            except Exception:
                log.exception("Closing Mani's run failed")


@admin.post("/conversations/{conversation_id}/messages",
            responses={200: {"description": "Server-sent events, one per turn event.",
                             "content": {"text/event-stream": {"schema": {"type": "string"}}}}})
def send_message(conversation_id: uuid.UUID, body: SendMessageIn,
                 founder: User = Depends(require_founder), db: Session = Depends(get_db),
                 agent: Agent = Depends(get_agent)) -> StreamingResponse:
    """Sends a message and streams what Mani does: `data: {"kind", "data"}` per event,
    ending after `done`. One answer at a time in a conversation (409 otherwise)."""
    started = utcnow()
    service.own_conversation(db, founder.id, conversation_id)
    if service.run_in_progress(db, conversation_id, started):
        raise ApiError("conflict", "Mani is still answering. Wait for it to finish.", 409)
    bind = db.get_bind()
    db.close()  # free this request's connection before a long stream
    return StreamingResponse(
        stream_turn(bind, agent, conversation_id, founder.id, body.text, started),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---- Sources, memory, usage ---------------------------------------------------------------


@admin.get("/sources", response_model=SourcesOut)
def list_sources(_founder: User = Depends(require_founder), db: Session = Depends(get_db)) -> SourcesOut:
    return service.sources(db)


@admin.get("/memory", response_model=MemoryListOut)
def list_memory(_founder: User = Depends(require_founder), db: Session = Depends(get_db)) -> MemoryListOut:
    return MemoryListOut(items=service.memory(db))


@admin.patch("/memory/{fact_id}", response_model=MemoryFactOut)
def patch_memory(fact_id: uuid.UUID, body: MemoryPatchIn, _founder: User = Depends(require_founder),
                 db: Session = Depends(get_db)) -> MemoryFactOut:
    return service.patch_memory(db, fact_id, body.text, body.status)


@admin.delete("/memory/{fact_id}", status_code=204)
def delete_memory(fact_id: uuid.UUID, _founder: User = Depends(require_founder),
                  db: Session = Depends(get_db)) -> Response:
    service.delete_memory(db, fact_id)
    return Response(status_code=204)


@admin.get("/usage", response_model=UsageOut)
def get_usage(_founder: User = Depends(require_founder), db: Session = Depends(get_db),
              settings: ManiSettings = Depends(get_mani_settings),
              now: Clock = Depends(get_now)) -> UsageOut:
    """Counts and cost only, never text."""
    return service.usage(db, settings, now())
