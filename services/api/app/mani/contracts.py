"""The interfaces between Mani's parts, fixed in Wave 0 so the parts can be built apart.

A part owns its own module and depends only on the types here. Do not change a type in
this file from inside one part: raise it with the person merging, because every other part
reads it. Nothing here imports a database model or a web framework."""
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Protocol

from sqlalchemy.orm import Session

# ---- Models -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Usage:
    """What one model call used. Never holds prompt or answer text."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cost_usd: Decimal = Decimal(0)  # an estimate; 0 for a local model


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # a JSON Schema object


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    # Provider data that must go back with the call (Gemini's "thought signature"). Kept as received.
    extra: dict[str, Any] | None = None


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()  # on an assistant message
    tool_call_id: str | None = None  # on a tool message
    name: str | None = None  # on a tool message: the tool's name


@dataclass(frozen=True)
class ChatResult:
    message: ChatMessage  # role "assistant"
    usage: Usage
    model: str
    finish_reason: str = "stop"


@dataclass(frozen=True)
class EmbedResult:
    vectors: list[list[float]]  # one per input, each of `Embedder.dimensions` values
    usage: Usage


class ModelError(Exception):
    """The model backend failed, timed out, or is not allowed. Never retried silently,
    and never switched to another backend (architecture 8.1)."""


class LLMClient(Protocol):
    backend: str  # "local" or "openrouter"
    model: str

    def chat(self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec] = (), *,
             temperature: float = 0.0) -> ChatResult: ...


class Embedder(Protocol):
    model: str
    dimensions: int  # always EMBEDDING_DIMENSIONS (1024)

    def embed(self, texts: Sequence[str]) -> EmbedResult: ...


# ---- Scrub --------------------------------------------------------------------------------


@dataclass(frozen=True)
class ScrubResult:
    text: str
    redactions: dict[str, int] = field(default_factory=dict)  # kind -> count


class Scrubber(Protocol):
    """Removes secrets and PII (decisions D8, D14). Runs before indexing and on every tool
    result, so nothing sensitive reaches a model. Customer names and crew data stay."""

    def scrub(self, text: str, *, source_path: str | None = None) -> ScrubResult: ...

    def scrub_data(self, value: Any) -> Any:
        """The same for a JSON-like structure (dicts, lists, strings). Keys are kept."""
        ...


# ---- Knowledge ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Citation:
    """Where an answer's evidence came from: an indexed source or a live tool."""

    title: str
    kind: Literal["doc", "code", "config", "data", "tool"]
    path: str = ""  # the file for a source, the tool name for a tool
    requirement_id: str | None = None
    commit_id: str = ""
    as_of: datetime | None = None  # when the source was indexed or the data was read


@dataclass(frozen=True)
class Passage:
    text: str  # already scrubbed
    citation: Citation
    score: float = 0.0


class Retriever(Protocol):
    def search(self, db: Session, query: str, *, limit: int = 6) -> list[Passage]: ...


# ---- Live tools ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolResult:
    data: Any  # JSON-serialisable and already scrubbed; totals are computed in code
    citation: Citation
    summary: str = ""  # one plain sentence, including limits ("no costs are recorded")


class ToolError(Exception):
    """A tool refused bad input. The message goes back to the model."""


class Tool(Protocol):
    spec: ToolSpec

    def run(self, db: Session, arguments: dict[str, Any], *, now: datetime) -> ToolResult:
        """Read only. Never writes to a business table. `now` is timezone-aware UTC; day
        boundaries are Asia/Kolkata."""
        ...


# ---- One conversation turn ----------------------------------------------------------------


@dataclass(frozen=True)
class TurnEvent:
    """What the agent reports while it works on one user message. The API sends each
    event to the portal as it happens. `kind` is one of:

    run_started      data: {"run_id"}
    tool_call        data: {"name", "arguments"}
    tool_result      data: {"name", "summary"}
    answer           data: {"message_id", "content", "citations": [...]}
    budget_exhausted data: {"spent_usd", "budget_usd"}   (no model call was made)
    error            data: {"message"}
    done             data: {"run_id", "status"}
    """

    kind: str
    data: dict[str, Any] = field(default_factory=dict)


class Agent(Protocol):
    def run_turn(self, db: Session, *, conversation_id: Any, login_id: Any,
                 user_text: str) -> Iterator[TurnEvent]: ...
