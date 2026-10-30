"""POST /v1/admin/mani/conversations/{id}/messages: the server-sent event stream, with a
scripted agent in place of the real one."""
import json
import sys
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.models import Login
from app.mani.contracts import TurnEvent
from app.mani.models import ManiConversation, ManiMessage, ManiRun
from app.mani.router import get_agent, stream_turn
from app.platform.db import get_db, utcnow
from tests.mani.test_api import BASE, make_conversation
from tests.test_api import auth, login


@pytest.fixture
def founder(client):
    return auth(login(client, "admin")["access_token"])


@pytest.fixture
def founder_id(db, client):
    return db.scalars(select(Login.id).where(Login.login_id == "priveopapa")).one()


class ScriptedAgent:
    """Runs `script(db, **kwargs)`, a generator function of TurnEvents. Records its calls."""

    def __init__(self, script):
        self.script = script
        self.calls = []

    def run_turn(self, db, **kwargs):
        self.calls.append(kwargs)
        return self.script(db, **kwargs)


def use_agent(client, script):
    agent = ScriptedAgent(script)
    client.app.dependency_overrides[get_agent] = lambda: agent
    return agent


def frames(response):
    """The events of a response body, checking the framing: `data: {json}` + blank line."""
    body = response.text
    assert body.endswith("\n\n")
    out = []
    for block in body[:-2].split("\n\n"):
        assert block.startswith("data: ") and "\n" not in block
        out.append(json.loads(block[len("data: "):]))
    return out


def happy(db, *, conversation_id, login_id, user_text):
    """What the real agent does: save the question, a run and the answer."""
    run = ManiRun(conversation_id=conversation_id, status="running")
    db.add(run)
    db.flush()
    db.add(ManiMessage(conversation_id=conversation_id, run_id=run.id, role="user", content=user_text))
    yield TurnEvent("run_started", {"run_id": run.id})  # a UUID: the stream must serialise it
    yield TurnEvent("tool_call", {"name": "get_x", "arguments": {"a": 1}})
    yield TurnEvent("tool_result", {"name": "get_x", "summary": "one row"})
    answer = ManiMessage(conversation_id=conversation_id, run_id=run.id, role="assistant", content="Done.")
    db.add(answer)
    db.flush()
    yield TurnEvent("answer", {"message_id": answer.id, "content": "Done.", "citations": []})
    run.status = "succeeded"
    yield TurnEvent("done", {"run_id": run.id, "status": "succeeded"})
    yield TurnEvent("answer", {"content": "never sent"})  # after done: ignored


def send(client, founder, conversation_id, text="How are we doing?"):
    return client.post(f"{BASE}/conversations/{conversation_id}/messages", json={"text": text}, headers=founder)


def test_events_are_framed_and_end_after_done(client, db, founder, founder_id):
    c = make_conversation(db, founder_id)
    agent = use_agent(client, happy)
    r = send(client, founder, c.id)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["cache-control"] == "no-cache"
    events = frames(r)
    assert [e["kind"] for e in events] == ["run_started", "tool_call", "tool_result", "answer", "done"]
    assert uuid.UUID(events[0]["data"]["run_id"])
    assert events[1]["data"] == {"name": "get_x", "arguments": {"a": 1}}
    assert events[4]["data"]["status"] == "succeeded"
    assert agent.calls[0]["user_text"] == "How are we doing?"
    assert agent.calls[0]["conversation_id"] == c.id and agent.calls[0]["login_id"] == founder_id


def test_what_the_agent_did_is_committed(client, db, founder, founder_id):
    """The agent only adds and flushes. The API commits, so a reload after `done` sees it."""
    c = make_conversation(db, founder_id, updated_at=utcnow() - timedelta(days=3))
    use_agent(client, happy)
    send(client, founder, c.id)
    detail = client.get(f"{BASE}/conversations/{c.id}", headers=founder).json()
    assert [(m["role"], m["content"]) for m in detail["messages"]] == [
        ("user", "How are we doing?"), ("assistant", "Done.")]
    db.expire_all()
    assert db.scalars(select(ManiRun)).one().status == "succeeded"
    assert db.get(ManiConversation, c.id).updated_at > utcnow() - timedelta(minutes=1)  # used just now


def test_the_stream_has_its_own_session_and_frees_the_request_connection(client, db, founder, founder_id, engine):
    """Finding: a yield dependency (`get_db`) stays open until the response ends, so a
    stream tied to it would hold a connection, idle in a transaction, for the whole answer.
    The route closes the request session first and the stream opens its own."""
    c = make_conversation(db, founder_id)
    request_sessions, seen = [], {}

    def recording_get_db():
        with Session(engine, expire_on_commit=False) as session:
            request_sessions.append(session)
            yield session

    client.app.dependency_overrides[get_db] = recording_get_db

    def script(agent_db, **kw):
        seen["same_as_request"] = any(agent_db is s for s in request_sessions)
        seen["request_in_transaction"] = [s.in_transaction() for s in request_sessions]
        yield TurnEvent("run_started", {"run_id": "r"})
        agent_db.add(ManiMessage(conversation_id=kw["conversation_id"], role="user", content="after a yield"))
        yield TurnEvent("done", {"run_id": "r", "status": "succeeded"})  # the session is still usable

    use_agent(client, script)
    assert send(client, founder, c.id).status_code == 200
    assert seen == {"same_as_request": False, "request_in_transaction": [False]}
    db.expire_all()
    assert [m.content for m in db.scalars(select(ManiMessage))] == ["after a yield"]


def test_an_agent_exception_ends_with_error_then_done(client, db, founder, founder_id):
    c = make_conversation(db, founder_id)

    def broken(agent_db, *, conversation_id, **kw):
        run = ManiRun(conversation_id=conversation_id, status="running")
        agent_db.add(run)
        agent_db.commit()  # the real agent commits a run before it calls the model
        yield TurnEvent("run_started", {"run_id": run.id})
        raise RuntimeError("secret detail: sk-12345")

    use_agent(client, broken)
    r = send(client, founder, c.id)
    assert r.status_code == 200
    events = frames(r)
    assert [e["kind"] for e in events] == ["run_started", "error", "done"]
    assert "sk-12345" not in r.text and "RuntimeError" not in r.text and "Traceback" not in r.text
    assert events[2]["data"]["status"] == "failed" and events[2]["data"]["run_id"] == events[0]["data"]["run_id"]
    db.expire_all()
    run = db.scalars(select(ManiRun)).one()
    assert run.status == "failed" and run.finished_at is not None  # not left "running"
    # ...so the next message is not refused with 409.
    use_agent(client, happy)
    assert send(client, founder, c.id).status_code == 200


def test_an_agent_that_stops_early_still_ends_with_done(client, db, founder, founder_id):
    c = make_conversation(db, founder_id)
    use_agent(client, lambda agent_db, **kw: iter([TurnEvent("run_started", {"run_id": "r"})]))
    assert [e["kind"] for e in frames(send(client, founder, c.id))] == ["run_started", "error", "done"]


def test_a_client_disconnect_closes_the_run(client, db, founder_id):
    """A closed generator is what a dropped connection leaves behind."""
    c = make_conversation(db, founder_id)
    closed = {}

    def script(agent_db, *, conversation_id, **kw):
        run = ManiRun(conversation_id=conversation_id, status="running")
        agent_db.add(run)
        agent_db.commit()
        try:
            yield TurnEvent("run_started", {"run_id": run.id})
            yield TurnEvent("tool_call", {"name": "slow"})
        finally:
            closed["agent"] = True

    started = utcnow() - timedelta(seconds=1)
    stream = stream_turn(db.get_bind(), ScriptedAgent(script), c.id, founder_id, "hi", started)
    assert next(stream).startswith("data: ")
    stream.close()
    assert closed == {"agent": True}
    db.expire_all()
    run = db.scalars(select(ManiRun)).one()
    assert run.status == "cancelled" and run.finished_at is not None


def test_a_message_while_a_run_is_in_progress_is_refused(client, db, founder, founder_id):
    c = make_conversation(db, founder_id)
    other = make_conversation(db, founder_id)
    run = ManiRun(conversation_id=c.id, status="running")
    db.add(run)
    db.commit()
    agent = use_agent(client, happy)
    r = send(client, founder, c.id)
    assert r.status_code == 409 and r.json()["code"] == "conflict" and agent.calls == []
    assert send(client, founder, other.id).status_code == 200  # another conversation is fine
    run.started_at = utcnow() - timedelta(hours=2)  # a crashed run does not block for ever
    db.commit()
    assert send(client, founder, c.id).status_code == 200


def test_bad_requests(client, db, founder, founder_id):
    c = make_conversation(db, founder_id)
    use_agent(client, happy)
    assert send(client, founder, uuid.uuid4()).status_code == 404
    assert send(client, founder, c.id, text="").status_code == 422
    assert send(client, founder, c.id, text="x" * 4001).status_code == 422
    assert client.post(f"{BASE}/conversations/{c.id}/messages", headers=founder).status_code == 422
    assert client.post(f"{BASE}/conversations/{c.id}/messages", json={"text": "hi"}).status_code == 401


def test_someone_elses_conversation_is_404_for_a_message(client, db, founder):
    from tests.mani.test_access import add_admin

    add_admin(db)
    other = db.scalars(select(Login.id).where(Login.login_id == "otheradmin")).one()
    c = make_conversation(db, other)
    agent = use_agent(client, happy)
    assert send(client, founder, c.id).status_code == 404 and agent.calls == []


def test_a_missing_agent_is_a_plain_503(client, db, founder, founder_id, monkeypatch):
    c = make_conversation(db, founder_id)
    monkeypatch.setitem(sys.modules, "app.mani.agent", None)  # the import fails
    r = send(client, founder, c.id)
    assert r.status_code == 503 and r.json()["message"] == "Mani is not ready"
    assert not r.headers["content-type"].startswith("text/event-stream")


def test_other_roles_cannot_stream(client, db, founder_id):
    c = make_conversation(db, founder_id)
    agent = use_agent(client, happy)
    for role in ("customer", "crew"):
        r = send(client, auth(login(client, role)["access_token"]), c.id)
        assert r.status_code == 403
    assert agent.calls == []
