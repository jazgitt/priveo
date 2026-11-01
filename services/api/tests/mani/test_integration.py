"""The whole path with nothing mocked but the model: the real route, the real agent, the real
tools, scrubber, budget and database. Only the chat model and the embedder are scripted."""
import json
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.models import Login
from app.mani.agent import ManiAgent
from app.mani.config import ManiSettings
from app.mani.contracts import ChatMessage, ToolCall
from app.mani.models import ManiConversation, ManiMessage, ManiModelUsage, ManiRun
from app.mani.retrieval import HybridRetriever
from app.mani.router import get_agent
from app.mani.scrub import PatternScrubber
from app.mani.tools import build_registry
from tests.mani.fakes import FakeEmbedder, FakeLLM
from tests.mani.test_api import BASE
from tests.mani.test_api_stream import frames
from tests.test_api import auth, login


@pytest.fixture
def founder(client):
    return auth(login(client, "admin")["access_token"])


def real_agent(llm, **settings):
    scrubber = PatternScrubber()
    return ManiAgent(settings=ManiSettings(**settings), llm=llm, retriever=HybridRetriever(FakeEmbedder()),
                     registry=build_registry(scrubber), scrubber=scrubber)


def use(client, agent):
    client.app.dependency_overrides[get_agent] = lambda: agent
    return agent


def new_conversation(client, founder):
    r = client.post(f"{BASE}/conversations", headers=founder)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def send(client, founder, conversation_id, text):
    return client.post(f"{BASE}/conversations/{conversation_id}/messages", json={"text": text},
                       headers=founder)


def test_a_question_goes_through_a_tool_to_a_cited_saved_answer(client, founder):
    llm = FakeLLM([
        ChatMessage("assistant", tool_calls=(ToolCall("c1", "operations_summary", {}),)),
        ChatMessage("assistant", "Sir ji, no jobs are scheduled today."),
    ])
    use(client, real_agent(llm))
    conversation_id = new_conversation(client, founder)

    response = send(client, founder, conversation_id, "How many jobs are scheduled today?")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = frames(response)
    kinds = [e["kind"] for e in events]
    assert kinds[0] == "run_started" and kinds[-1] == "done"
    assert kinds.index("tool_call") < kinds.index("tool_result") < kinds.index("answer")
    assert events[kinds.index("tool_call")]["data"]["name"] == "operations_summary"
    answer = events[kinds.index("answer")]["data"]
    assert answer["content"].startswith("Sir ji")
    assert [c["path"] for c in answer["citations"]] == ["operations_summary"]
    assert events[-1]["data"]["status"] == "succeeded"

    # The tool result went back to the model as data, and the model was offered only the tools the question needs.
    assert len(llm.calls) == 2
    offered = {spec.name for spec in llm.calls[0][1]}
    assert {"operations_summary", "search_sources"} <= offered and "remember_fact" not in offered
    assert any(m.role == "tool" for m in llm.calls[1][0])

    # What a reload shows: both messages, the citation, the title.
    detail = client.get(f"{BASE}/conversations/{conversation_id}", headers=founder).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["citations"][0]["kind"] == "tool"
    assert detail["title"].startswith("How many jobs")

    # Two model calls were recorded, and the usage page counts them.
    usage = client.get(f"{BASE}/usage", headers=founder).json()
    assert usage["failed_calls"] == 0 and usage["budget_exhausted"] is False
    assert sum(day["calls"] for day in usage["days"]) == 2


def test_an_answer_never_leaks_pii_even_if_the_model_does(client, founder):
    llm = FakeLLM([ChatMessage("assistant", "Call the customer on 9876543210 or mail asha@example.com.")])
    use(client, real_agent(llm))
    conversation_id = new_conversation(client, founder)

    events = frames(send(client, founder, conversation_id, "Give me a customer's contact details."))
    content = next(e["data"]["content"] for e in events if e["kind"] == "answer")
    assert "9876543210" not in content and "asha@example.com" not in content
    saved = client.get(f"{BASE}/conversations/{conversation_id}", headers=founder).json()
    assert "9876543210" not in json.dumps(saved) and "asha@example.com" not in json.dumps(saved)


def test_an_exhausted_budget_stops_the_model_and_says_so(client, founder, db):
    db.add(ManiModelUsage(kind="chat", backend="openrouter", model="m", cost_usd=Decimal("1.5")))
    db.commit()
    llm = FakeLLM([])  # any model call would raise
    use(client, real_agent(llm, budget_usd=1.0))
    conversation_id = new_conversation(client, founder)

    events = frames(send(client, founder, conversation_id, "Anything at all?"))
    kinds = [e["kind"] for e in events]
    assert "budget_exhausted" in kinds and kinds[-1] == "done"
    assert events[-1]["data"]["status"] == "budget_exhausted"
    assert llm.calls == []
    assert client.get(f"{BASE}/status", headers=founder).json()["budget_exhausted"] is True
    assert client.get(f"{BASE}/usage", headers=founder).json()["budget_exhausted"] is True


def test_memory_written_in_chat_shows_on_the_memory_route(client, founder):
    llm = FakeLLM([
        ChatMessage("assistant", tool_calls=(ToolCall("m1", "remember_fact",
                                                      {"text": "Trainees are always paired with a Member."}),)),
        ChatMessage("assistant", "Noted, Sir ji."),
    ])
    use(client, real_agent(llm))
    conversation_id = new_conversation(client, founder)
    send(client, founder, conversation_id, "Remember that trainees are always paired with a Member.")

    facts = client.get(f"{BASE}/memory", headers=founder).json()["items"]
    assert [f["text"] for f in facts] == ["Trainees are always paired with a Member."]
    # Deleting it from the memory route takes it out of what Mani is told next turn.
    assert client.delete(f"{BASE}/memory/{facts[0]['id']}", headers=founder).status_code == 204
    assert client.get(f"{BASE}/memory", headers=founder).json()["items"] == []


def test_a_failing_model_ends_the_stream_cleanly_and_keeps_the_question(client, founder, db):
    class Broken:
        backend, model = "local", "broken"

        def chat(self, *args, **kwargs):
            from app.mani.contracts import ModelError
            raise ModelError("The model did not answer.")

    use(client, real_agent(Broken()))
    conversation_id = new_conversation(client, founder)
    events = frames(send(client, founder, conversation_id, "Hello?"))
    kinds = [e["kind"] for e in events]
    assert "error" in kinds and kinds[-1] == "done" and events[-1]["data"]["status"] == "failed"
    with Session(db.get_bind()) as check:
        messages = check.scalars(select(ManiMessage).where(
            ManiMessage.conversation_id == ManiConversation.id)).all()
        assert [m.role for m in messages] == ["user"]
        assert check.scalars(select(ManiRun)).one().status == "failed"
        assert "Traceback" not in check.scalars(select(ManiRun)).one().error


def test_another_admin_cannot_use_the_stream(client, db):
    from app.identity.service import hash_password
    from app.platform.db import utcnow
    db.add(Login(role="admin", login_id="otheradmin", display_name="Other", active=True,
                 password_hash=hash_password("pw-other-admin1"), password_changed_at=utcnow()))
    db.commit()
    token = client.post("/v1/auth/login", json={"login_id": "otheradmin", "password": "pw-other-admin1"})
    other = auth(token.json()["access_token"])
    use(client, real_agent(FakeLLM([])))
    founder_headers = auth(login(client, "admin")["access_token"])
    conversation_id = new_conversation(client, founder_headers)
    assert send(client, other, conversation_id, "hi").status_code == 403
    assert client.get(f"{BASE}/conversations", headers=other).status_code == 403
