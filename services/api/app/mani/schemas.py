"""The Founder-only API under /v1/admin/mani. These shapes and the route table below are
fixed in Wave 0 so the portal can be built before the routes exist. Every route needs the
Founder (`require_founder`); an admin who is not the Founder gets 403.

Routes (Wave 0 builds the first; the API step builds the rest):

    GET    /v1/admin/mani/status                          -> StatusOut
    GET    /v1/admin/mani/conversations                   -> ConversationListOut
    POST   /v1/admin/mani/conversations                   -> ConversationOut        (201)
    GET    /v1/admin/mani/conversations/{id}              -> ConversationDetailOut
    DELETE /v1/admin/mani/conversations/{id}              -> 204
    POST   /v1/admin/mani/conversations/{id}/messages     -> server-sent events
    GET    /v1/admin/mani/sources                         -> SourcesOut
    GET    /v1/admin/mani/memory                          -> MemoryListOut
    PATCH  /v1/admin/mani/memory/{id}                     -> MemoryFactOut
    DELETE /v1/admin/mani/memory/{id}                     -> 204
    GET    /v1/admin/mani/usage                           -> UsageOut

The messages route takes `SendMessageIn` and streams `text/event-stream`: one event per
`TurnEvent`, as `data: {"kind": "...", "data": {...}}` followed by a blank line (see
`contracts.TurnEvent` for the kinds). The stream ends after a `done` event.

Dates are ISO 8601 UTC. The portal shows them as dd-Mon-yy."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CitationOut(BaseModel):
    title: str
    kind: Literal["doc", "code", "config", "data", "tool"]
    path: str = ""
    requirement_id: str | None = None
    commit_id: str = ""
    as_of: datetime | None = None


class MessageOut(BaseModel):
    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    citations: list[CitationOut] = []
    created_at: datetime


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListOut(BaseModel):
    items: list[ConversationOut]


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class SendMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class SourceOut(BaseModel):
    path: str
    kind: str
    title: str
    status: Literal["active", "deleted", "failed"]
    indexed_at: datetime | None = None
    commit_id: str = ""
    chunks: int = 0


class SourcesOut(BaseModel):
    items: list[SourceOut]
    embedding_model: str = ""
    last_indexed_at: datetime | None = None


class MemoryFactOut(BaseModel):
    id: uuid.UUID
    text: str
    status: Literal["confirmed", "tentative"]
    created_at: datetime


class MemoryListOut(BaseModel):
    items: list[MemoryFactOut]


class MemoryPatchIn(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    status: Literal["confirmed", "tentative"] | None = None


class UsageDayOut(BaseModel):
    day: str  # YYYY-MM-DD, Asia/Kolkata
    calls: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class UsageOut(BaseModel):
    """Usage against the configured budget (D10, D18). Counts and cost only, never text."""

    budget_usd: float
    spent_usd: float
    remaining_usd: float
    budget_exhausted: bool
    failed_calls: int
    average_latency_ms: int
    days: list[UsageDayOut]


class StatusOut(BaseModel):
    founder: bool = True
    backend: str
    chat_model: str
    embedding_model: str
    budget_exhausted: bool = False
