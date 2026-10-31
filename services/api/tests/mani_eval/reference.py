"""A reference agent that answers every question correctly from the expected values.

It exists to prove the harness: it must score 100%, and a copy that is changed to answer
wrongly must be caught. It is not Mani and calls no model."""
import re
from collections.abc import Iterator
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.mani.contracts import Citation, TurnEvent
from tests.mani_eval.expected import Expected
from tests.mani_eval.questions import Question

AGENT_DOCS = Path(__file__).resolve().parents[4] / "docs" / "agent"
REVIEW_FILES = tuple(AGENT_DOCS / f"mani-question-set-review-{part}.md" for part in ("A1", "A2", "B", "C", "D"))
GOLDEN_TYPES = ("code", "architecture", "business", "run")


@cache
def golden_answers() -> dict[int, str]:
    """The golden answer of each question, read from the five review files (markdown marks removed)."""
    answers = {}
    for line in "\n".join(f.read_text(encoding="utf-8") for f in REVIEW_FILES).splitlines():
        cells = re.split(r"(?<!\\)\|", line)
        if len(cells) == 8 and cells[1].strip().isdigit():
            answers[int(cells[1])] = cells[3].strip().replace("\\|", "|").replace("`", "")
    return answers


class ReferenceAgent:
    """Answers the question last given to `prepare` with its golden answer."""

    def __init__(self, expected: dict[str, Expected], now: datetime) -> None:
        self.expected = expected
        self.now = now
        self.question: Question | None = None
        self.calls: list[str] = []

    def prepare(self, question: Question) -> None:
        self.question = question

    # ---- The Agent protocol -----------------------------------------------------------------

    def run_turn(self, db: Session, *, conversation_id: Any, login_id: Any,
                 user_text: str) -> Iterator[TurnEvent]:
        question = self.question
        assert question is not None, "call prepare(question) first"
        self.calls.append(user_text)
        yield TurnEvent("run_started", {"run_id": "reference"})
        yield self._answer(self.text_for(question), self._citations(question))
        yield TurnEvent("done", {"run_id": "reference", "status": "completed"})

    # ---- Answers ----------------------------------------------------------------------------

    def _answer(self, text: str, citations: list[Citation]) -> TurnEvent:
        return TurnEvent("answer", {"message_id": "reference", "content": text,
                                    "citations": citations})

    def _citations(self, question: Question) -> list[Citation]:
        return [Citation("Priveo repository snapshot", "doc", "docs/", as_of=self.now)]

    def text_for(self, question: Question) -> str:
        return golden_answers()[question.id]
