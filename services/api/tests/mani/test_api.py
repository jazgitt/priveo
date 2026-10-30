"""The Founder-only API under /v1/admin/mani, apart from the message stream."""
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.identity.models import Login
from app.main import create_app
from app.mani.config import get_mani_settings
from app.mani.models import (
    ManiChunk,
    ManiConversation,
    ManiMemoryFact,
    ManiMessage,
    ManiModelUsage,
    ManiRun,
    ManiSource,
)
from app.platform import clock
from app.platform.db import utcnow
from tests.mani.test_access import add_admin, sign_in_as
from tests.test_api import auth, login

BASE = "/v1/admin/mani"


@pytest.fixture(autouse=True)
def fresh_settings():
    get_mani_settings.cache_clear()
    yield
    get_mani_settings.cache_clear()


@pytest.fixture
def founder(client):
    return auth(login(client, "admin")["access_token"])


@pytest.fixture
def founder_id(db):
    return db.scalars(select(Login.id).where(Login.login_id == "priveopapa")).one()


def make_conversation(db, login_id, title="", updated_at=None):
    c = ManiConversation(login_id=login_id, title=title)
    if updated_at is not None:
        c.created_at = c.updated_at = updated_at
    db.add(c)
    db.commit()
    return c


def add_usage(db, created_at, cost="0.01", prompt=10, completion=5, latency=100, ok=True, run_id=None):
    db.add(ManiModelUsage(kind="chat", backend="local", model="m", prompt_tokens=prompt,
                          completion_tokens=completion, latency_ms=latency, cost_usd=Decimal(cost),
                          ok=ok, created_at=created_at, run_id=run_id))
    db.commit()


# ---- Status -------------------------------------------------------------------------------


def test_status_reports_the_budget(client, db, founder, monkeypatch):
    monkeypatch.setenv("MANI_BUDGET_USD", "0.05")
    get_mani_settings.cache_clear()
    assert client.get(f"{BASE}/status", headers=founder).json()["budget_exhausted"] is False
    add_usage(db, utcnow(), "0.04")
    assert client.get(f"{BASE}/status", headers=founder).json()["budget_exhausted"] is False
    add_usage(db, utcnow(), "0.01")  # exactly the budget: used up
    assert client.get(f"{BASE}/status", headers=founder).json()["budget_exhausted"] is True


# ---- Conversations ------------------------------------------------------------------------


def test_create_list_get_and_delete_a_conversation(client, founder, db):
    r = client.post(f"{BASE}/conversations", headers=founder)
    assert r.status_code == 201
    created = r.json()
    assert created["title"] == "" and uuid.UUID(created["id"])

    listing = client.get(f"{BASE}/conversations", headers=founder)
    assert listing.status_code == 200 and [c["id"] for c in listing.json()["items"]] == [created["id"]]

    one = client.get(f"{BASE}/conversations/{created['id']}", headers=founder)
    assert one.status_code == 200 and one.json()["messages"] == []

    assert client.delete(f"{BASE}/conversations/{created['id']}", headers=founder).status_code == 204
    assert client.get(f"{BASE}/conversations/{created['id']}", headers=founder).status_code == 404
    assert client.get(f"{BASE}/conversations", headers=founder).json()["items"] == []


def test_create_also_accepts_the_portals_empty_json_body(client, founder):
    assert client.post(f"{BASE}/conversations", json={}, headers=founder).status_code == 201


def test_the_list_is_newest_first_and_only_the_founders(client, db, founder, founder_id):
    now = utcnow()
    old = make_conversation(db, founder_id, "old", now - timedelta(days=2))
    new = make_conversation(db, founder_id, "new", now - timedelta(hours=1))
    other_admin = add_admin(db) and db.scalars(select(Login.id).where(Login.login_id == "otheradmin")).one()
    make_conversation(db, other_admin, "not mine", now)
    items = client.get(f"{BASE}/conversations", headers=founder).json()["items"]
    assert [i["id"] for i in items] == [str(new.id), str(old.id)]


def test_a_conversation_shows_messages_oldest_first_with_citations(client, db, founder, founder_id):
    c = make_conversation(db, founder_id, "t")
    t0 = utcnow() - timedelta(minutes=5)
    db.add_all([
        ManiMessage(conversation_id=c.id, role="assistant", content="second", created_at=t0 + timedelta(minutes=1),
                    citations=[{"title": "Doc", "kind": "doc", "path": "docs/a.md", "requirement_id": "ADM-X-01",
                                "commit_id": "abc", "as_of": "2026-10-30T10:00:00+00:00"},
                               {"nonsense": True}]),  # an odd entry is skipped, not an error
        ManiMessage(conversation_id=c.id, role="user", content="first", created_at=t0),
    ])
    db.commit()
    body = client.get(f"{BASE}/conversations/{c.id}", headers=founder).json()
    assert [m["content"] for m in body["messages"]] == ["first", "second"]
    cites = body["messages"][1]["citations"]
    assert len(cites) == 1 and cites[0]["requirement_id"] == "ADM-X-01" and cites[0]["kind"] == "doc"


def test_deleting_removes_messages_and_runs_but_keeps_usage(client, db, founder, founder_id):
    c = make_conversation(db, founder_id)
    run = ManiRun(conversation_id=c.id, status="succeeded")
    db.add(run)
    db.commit()
    msg = ManiMessage(conversation_id=c.id, run_id=run.id, role="user", content="hi")
    db.add(msg)
    db.commit()
    fact = ManiMemoryFact(text="x", created_by=founder_id, source_message_id=msg.id)
    db.add(fact)
    db.commit()
    add_usage(db, utcnow(), run_id=run.id)
    assert client.delete(f"{BASE}/conversations/{c.id}", headers=founder).status_code == 204
    db.expire_all()
    assert db.scalars(select(ManiMessage)).all() == [] and db.scalars(select(ManiRun)).all() == []
    usage = db.scalars(select(ManiModelUsage)).all()
    assert len(usage) == 1 and usage[0].run_id is None
    assert db.get(ManiMemoryFact, fact.id).source_message_id is None  # the fact stays


def test_unknown_and_foreign_conversations_are_404(client, db, founder):
    password = add_admin(db)
    other_id = db.scalars(select(Login.id).where(Login.login_id == "otheradmin")).one()
    theirs = make_conversation(db, other_id, "private")
    for cid in (uuid.uuid4(), theirs.id):
        assert client.get(f"{BASE}/conversations/{cid}", headers=founder).status_code == 404
        assert client.delete(f"{BASE}/conversations/{cid}", headers=founder).status_code == 404
    assert db.get(ManiConversation, theirs.id) is not None
    assert password


# ---- Sources ------------------------------------------------------------------------------


def test_sources_list_chunk_counts_and_the_active_index(client, db, founder):
    t1, t2 = datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 10, 5, tzinfo=UTC)
    a = ManiSource(path="docs/a.md", title="A", status="active", indexed_at=t1, embedding_model="old-model")
    b = ManiSource(path="docs/b.md", title="B", status="active", indexed_at=t2, embedding_model="new-model")
    gone = ManiSource(path="docs/c.md", title="C", status="deleted", indexed_at=datetime(2026, 10, 9, tzinfo=UTC),
                      embedding_model="deleted-model")
    db.add_all([a, b, gone])
    db.commit()
    db.add_all([ManiChunk(source_id=a.id, ordinal=0, text="x"), ManiChunk(source_id=a.id, ordinal=1, text="y"),
                ManiChunk(source_id=b.id, ordinal=0, text="z")])
    db.commit()
    body = client.get(f"{BASE}/sources", headers=founder).json()
    assert {i["path"]: i["chunks"] for i in body["items"]} == {"docs/a.md": 2, "docs/b.md": 1, "docs/c.md": 0}
    assert body["embedding_model"] == "new-model" and body["last_indexed_at"].startswith("2026-10-05")


def test_sources_with_nothing_indexed(client, founder):
    body = client.get(f"{BASE}/sources", headers=founder).json()
    assert body == {"items": [], "embedding_model": "", "last_indexed_at": None}


# ---- Memory -------------------------------------------------------------------------------


def test_memory_list_patch_and_soft_delete(client, db, founder, founder_id):
    keep = ManiMemoryFact(text="Prefers short answers", status="tentative", created_by=founder_id)
    gone = ManiMemoryFact(text="Old", created_by=founder_id, deleted_at=utcnow())
    db.add_all([keep, gone])
    db.commit()
    assert [f["text"] for f in client.get(f"{BASE}/memory", headers=founder).json()["items"]] == [
        "Prefers short answers"]

    r = client.patch(f"{BASE}/memory/{keep.id}", json={"status": "confirmed"}, headers=founder)
    assert r.status_code == 200 and r.json()["status"] == "confirmed" and r.json()["text"] == "Prefers short answers"
    r = client.patch(f"{BASE}/memory/{keep.id}", json={"text": "  Likes tables  "}, headers=founder)
    assert r.json()["text"] == "Likes tables"
    assert client.patch(f"{BASE}/memory/{keep.id}", json={"text": "   "}, headers=founder).status_code == 422
    assert client.patch(f"{BASE}/memory/{keep.id}", json={"status": "bad"}, headers=founder).status_code == 422

    assert client.delete(f"{BASE}/memory/{keep.id}", headers=founder).status_code == 204
    assert client.get(f"{BASE}/memory", headers=founder).json()["items"] == []
    db.expire_all()
    assert db.get(ManiMemoryFact, keep.id).deleted_at is not None  # the row is kept
    for method in ("patch", "delete"):  # a deleted or unknown fact is 404
        for fid in (keep.id, uuid.uuid4()):
            kwargs = {"json": {"status": "confirmed"}} if method == "patch" else {}
            assert getattr(client, method)(f"{BASE}/memory/{fid}", headers=founder, **kwargs).status_code == 404


# ---- Usage --------------------------------------------------------------------------------


def test_usage_numbers_and_india_days(client, db, founder, monkeypatch):
    monkeypatch.setenv("MANI_BUDGET_USD", "1.0")
    get_mani_settings.cache_clear()
    now = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)  # 17:30 on 31-Oct in India
    monkeypatch.setattr(clock, "now_ist", lambda: now.astimezone(clock.IST))
    # 20:00 UTC on 30-Oct is 01:30 on 31-Oct in India. 18:29 UTC is still 23:59 on 30-Oct.
    add_usage(db, datetime(2026, 10, 30, 20, 0, tzinfo=UTC), "0.25", prompt=100, completion=50, latency=200)
    add_usage(db, datetime(2026, 10, 30, 18, 29, tzinfo=UTC), "0.10", prompt=10, completion=5, latency=400, ok=False)
    add_usage(db, datetime(2026, 10, 2, 18, 29, tzinfo=UTC), "0.05")  # 23:59 on 02-Oct: the oldest shown day
    add_usage(db, datetime(2026, 10, 1, 18, 29, tzinfo=UTC), "0.50")  # 01-Oct: outside the 30 days, still spent
    body = client.get(f"{BASE}/usage", headers=founder).json()

    assert body["budget_usd"] == 1.0 and body["spent_usd"] == pytest.approx(0.90)
    assert body["remaining_usd"] == pytest.approx(0.10) and body["budget_exhausted"] is False
    assert body["failed_calls"] == 1 and body["average_latency_ms"] == 200  # (200+400+100+100)/4
    days = {d["day"]: d for d in body["days"]}
    assert len(body["days"]) == 30 and body["days"][0]["day"] == "2026-10-02"
    assert body["days"][-1]["day"] == "2026-10-31"
    assert days["2026-10-31"]["calls"] == 1 and days["2026-10-31"]["cost_usd"] == pytest.approx(0.25)
    assert days["2026-10-31"]["prompt_tokens"] == 100 and days["2026-10-31"]["completion_tokens"] == 50
    assert days["2026-10-30"]["calls"] == 1 and days["2026-10-30"]["cost_usd"] == pytest.approx(0.10)
    assert days["2026-10-02"]["calls"] == 1 and days["2026-10-15"]["calls"] == 0
    assert set(body) == {"budget_usd", "spent_usd", "remaining_usd", "budget_exhausted", "failed_calls",
                         "average_latency_ms", "days"}  # counts and cost only


def test_usage_when_the_budget_is_used_up(client, db, founder, monkeypatch):
    monkeypatch.setenv("MANI_BUDGET_USD", "0.5")
    get_mani_settings.cache_clear()
    add_usage(db, utcnow(), "0.7")
    body = client.get(f"{BASE}/usage", headers=founder).json()
    assert body["budget_exhausted"] is True and body["remaining_usd"] == 0


def test_usage_with_no_calls(client, founder):
    body = client.get(f"{BASE}/usage", headers=founder).json()
    assert body["spent_usd"] == 0 and body["average_latency_ms"] == 0 and len(body["days"]) == 30


# ---- Access on every route ----------------------------------------------------------------


def mani_routes():
    """Every Mani route, read from the OpenAPI document so a route added later is covered."""
    out = []
    for path, item in create_app().openapi()["paths"].items():
        if path.startswith(BASE):
            out += [(m.upper(), path) for m in item if m.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}]
    return sorted(out)


ROUTES = mani_routes()


def concrete(path):
    return re.sub(r"\{[^}]+\}", lambda _: str(uuid.uuid4()), path)


def test_the_route_table_is_complete():
    assert len(ROUTES) >= 11
    assert ("POST", f"{BASE}/conversations/{{conversation_id}}/messages") in ROUTES


@pytest.mark.parametrize(("method", "path"), ROUTES, ids=[f"{m} {p}" for m, p in ROUTES])
def test_every_route_refuses_everyone_but_the_founder(client, db, method, path):
    url = concrete(path)
    body = {"json": {"text": "hi"}} if method in {"POST", "PATCH"} else {}
    assert client.request(method, url, **body).status_code == 401
    for role in ("customer", "crew"):
        r = client.request(method, url, headers=auth(login(client, role)["access_token"]), **body)
        assert r.status_code == 403, f"{role} {method} {path}"
    password = add_admin(db)
    r = client.request(method, url, headers=sign_in_as(client, "otheradmin", password), **body)
    assert r.status_code == 403 and r.json()["code"] == "forbidden", f"other admin {method} {path}"


def test_a_cookie_change_needs_the_csrf_header(client, founder_id):
    from fastapi.testclient import TestClient

    web = TestClient(client.app, base_url="https://testserver")
    from app import webauth

    if not any(getattr(r, "path", "") == "/v1/web/login" for r in client.app.routes):
        webauth.register(client.app)
    assert web.post("/v1/web/login", json={"login_id": "priveopapa", "password": "pw-admin1"}).status_code == 200
    missing = web.post(f"{BASE}/conversations")
    assert missing.status_code == 403 and missing.json()["code"] == "csrf_failed"
    ok = web.post(f"{BASE}/conversations", headers={"X-CSRF-Token": web.cookies.get("priveo_csrf")})
    assert ok.status_code == 201
    assert web.get(f"{BASE}/conversations").status_code == 200  # reads need no header
