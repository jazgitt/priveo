"""Stand-ins for the model backend, used by every Mani test so none needs Ollama or a
network. A part's tests import these instead of writing their own."""
import hashlib
from collections.abc import Sequence
from decimal import Decimal

from app.mani.config import EMBEDDING_DIMENSIONS
from app.mani.contracts import (
    ChatMessage,
    ChatResult,
    EmbedResult,
    ScrubResult,
    ToolSpec,
    Usage,
)


class FakeEmbedder:
    """A deterministic 1024-value vector per text: the same text always gives the same
    vector, and different texts give different ones. It has no meaning, so tests of
    ranking must use text that shares words (see `word_overlap_vector`)."""

    model = "fake-embedding"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> EmbedResult:
        self.calls.append(list(texts))
        return EmbedResult([word_overlap_vector(t) for t in texts],
                           Usage(prompt_tokens=sum(len(t.split()) for t in texts)))


def word_overlap_vector(text: str) -> list[float]:
    """A bag of words hashed into 1024 buckets, length 1. Texts that share words are
    closer, so a similarity search over these vectors behaves sensibly in a test."""
    vec = [0.0] * EMBEDDING_DIMENSIONS
    for word in text.lower().split():
        bucket = int(hashlib.sha256(word.strip(".,:;?!\"'()").encode()).hexdigest(), 16)
        vec[bucket % EMBEDDING_DIMENSIONS] += 1.0
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


class FakeLLM:
    """Replies from a script: each call to `chat` pops the next ChatMessage. It records
    every call so a test can check what the agent sent."""

    backend = "local"
    model = "fake-chat"

    def __init__(self, replies: Sequence[ChatMessage]) -> None:
        self._replies = list(replies)
        self.calls: list[tuple[list[ChatMessage], list[ToolSpec]]] = []

    def chat(self, messages, tools=(), *, temperature: float = 0.0) -> ChatResult:
        self.calls.append((list(messages), list(tools)))
        if not self._replies:
            raise AssertionError("FakeLLM was called more often than the test scripted.")
        return ChatResult(self._replies.pop(0), Usage(prompt_tokens=10, completion_tokens=5,
                                                      cost_usd=Decimal(0)), self.model)


class PassthroughScrubber:
    """Scrubs nothing. For tests of a part that is not about scrubbing."""

    def scrub(self, text: str, *, source_path: str | None = None) -> ScrubResult:
        return ScrubResult(text)

    def scrub_data(self, value):
        return value
