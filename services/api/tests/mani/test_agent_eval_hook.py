"""The `--agent mani` hook of the evaluation runner: the budget precondition."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.identity.models import Login
from app.mani.agent import ManiAgent, RecordingEmbedder
from app.mani.config import ManiSettings
from app.mani.contracts import ChatMessage
from app.mani.models import ManiModelUsage
from app.mani.retrieval import HybridRetriever
from app.mani.tools.registry import ToolRegistry
from tests.mani.fakes import FakeEmbedder, FakeLLM, PassthroughScrubber
from tests.mani_eval.questions import BY_ID
from tests.mani_eval.runner import EvalMani


def test_the_budget_question_runs_with_the_budget_used_up_and_restores_it(db):
    login = Login(role="admin", login_id="priveopapa", display_name="F", password_hash="x")
    db.add(login)
    db.commit()
    cfg = ManiSettings(_env_file=None, budget_usd=1.0)
    llm = FakeLLM([ChatMessage("assistant", "Fine.")])
    real = ManiAgent(settings=cfg, llm=llm, retriever=HybridRetriever(RecordingEmbedder(FakeEmbedder())),
                     registry=ToolRegistry(), scrubber=PassthroughScrubber(),
                     clock=lambda: datetime(2026, 10, 30, tzinfo=UTC))
    agent = EvalMani(real, cfg)
    question = BY_ID[47]
    agent.prepare(question)
    events = list(agent.run_turn(db, conversation_id=uuid.uuid4(), login_id=login.id,
                                 user_text=question.prompt))
    assert "budget_exhausted" in [e.kind for e in events] and llm.calls == []
    assert db.scalar(select(func.count()).select_from(ManiModelUsage)) == 0  # restored for the next question
    # Any other question runs normally.
    agent.prepare(BY_ID[48])
    other = list(agent.run_turn(db, conversation_id=uuid.uuid4(), login_id=login.id,
                                user_text=BY_ID[48].prompt))
    assert "answer" in [e.kind for e in other]
