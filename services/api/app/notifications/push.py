import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger("priveo.push")


class PushSender(Protocol):
    def send(self, tokens: Sequence[str], title: str, body: str,
             data: dict[str, str]) -> None:
        """Sends one message to these device tokens. FCM replaces this fake in
        a later step (it needs the owner's Firebase account)."""
        ...


@dataclass(frozen=True)
class SentPush:
    tokens: tuple[str, ...]
    title: str
    body: str
    data: dict[str, str]


class LoggingPushSender:
    """Writes the push to the log and remembers it, so tests can look."""

    def __init__(self):
        self.sent: list[SentPush] = []

    def send(self, tokens, title, body, data):
        self.sent.append(SentPush(tuple(tokens), title, body, dict(data)))
        log.info("push to %d device(s): %s", len(tokens), title)
