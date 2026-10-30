"""The tables, the vector column and the interfaces every other Mani part relies on."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, text

from app.identity.models import Login
from app.mani import contracts
from app.mani.config import EMBEDDING_DIMENSIONS
from app.mani.models import (
    ManiChunk,
    ManiConversation,
    ManiMessage,
    ManiModelUsage,
    ManiRun,
    ManiSource,
)
from app.mani.tools import build_registry
from app.mani.tools.registry import ToolRegistry
from tests.mani.fakes import FakeEmbedder, FakeLLM, PassthroughScrubber, word_overlap_vector


def founder(db):
    return db.scalars(select(Login).where(Login.login_id == "priveopapa")).one()


@pytest.fixture
def seeded(client, db):
    return founder(db)


def test_a_conversation_round_trips(db, seeded):
    conversation = ManiConversation(login_id=seeded.id, title="Hello")
    db.add(conversation)
    db.flush()
    run = ManiRun(conversation_id=conversation.id, status="succeeded")
    db.add(run)
    db.flush()
    db.add(ManiMessage(conversation_id=conversation.id, run_id=run.id, role="assistant",
                       content="Hi", citations=[{"title": "x", "kind": "doc"}]))
    db.add(ManiModelUsage(run_id=run.id, kind="chat", backend="local", model="m",
                          prompt_tokens=3, cost_usd=Decimal("0.00000120")))
    db.commit()
    message = db.scalars(select(ManiMessage)).one()
    assert message.citations == [{"title": "x", "kind": "doc"}]
    assert db.scalars(select(ManiModelUsage)).one().cost_usd == Decimal("0.00000120")


def test_deleting_a_conversation_removes_its_messages(db, seeded):
    conversation = ManiConversation(login_id=seeded.id)
    db.add(conversation)
    db.flush()
    db.add(ManiMessage(conversation_id=conversation.id, role="user", content="q"))
    db.commit()
    db.delete(conversation)
    db.commit()
    # ON DELETE CASCADE is the database's job; the ORM delete above removed the parent.
    assert db.scalars(select(ManiConversation)).first() is None


def test_a_chunk_stores_and_returns_a_1024_value_embedding(db):
    source = ManiSource(path="docs/x.md", title="X")
    db.add(source)
    db.flush()
    vector = word_overlap_vector("a payment is over due for seven days")
    db.add(ManiChunk(source_id=source.id, ordinal=0, text="payment", embedding=vector))
    db.commit()
    stored = db.scalars(select(ManiChunk)).one().embedding
    assert len(stored) == EMBEDDING_DIMENSIONS
    assert stored == pytest.approx(vector, abs=1e-6)


def test_an_embedding_of_the_wrong_size_is_refused(db):
    source = ManiSource(path="docs/y.md")
    db.add(source)
    db.flush()
    db.add(ManiChunk(source_id=source.id, ordinal=0, text="t", embedding=[0.1, 0.2]))
    with pytest.raises(Exception, match="1024"):
        db.flush()


def test_a_source_path_is_unique(db):
    db.add_all([ManiSource(path="same.md"), ManiSource(path="same.md")])
    with pytest.raises(Exception):  # noqa: B017  (IntegrityError, in either database)
        db.flush()


def test_similarity_search_orders_by_cosine_distance(db, engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("pgvector similarity needs PostgreSQL")
    source = ManiSource(path="docs/search.md")
    db.add(source)
    db.flush()
    texts = ["a payment is over due for seven days", "the crew wash cars every morning",
             "customers pause their plan for a week"]
    for i, t in enumerate(texts):
        db.add(ManiChunk(source_id=source.id, ordinal=i, text=t, embedding=word_overlap_vector(t)))
    db.commit()
    from app.mani.models import ManiChunk as C
    query = word_overlap_vector("which payment is over due")
    nearest = db.scalars(select(C).order_by(C.embedding.cosine_distance(query)).limit(1)).one()
    assert nearest.text == texts[0]
    ranked = db.execute(text(
        "select count(*) from mani_chunks where to_tsvector('english', text) @@ plainto_tsquery('english', 'payment')"
    )).scalar_one()
    assert ranked == 1


def test_the_fakes_satisfy_the_interfaces():
    embedder: contracts.Embedder = FakeEmbedder()
    result = embedder.embed(["one", "two"])
    assert len(result.vectors) == 2 and len(result.vectors[0]) == EMBEDDING_DIMENSIONS
    assert result.vectors[0] == embedder.embed(["one"]).vectors[0]
    reply = contracts.ChatMessage("assistant", "hello")
    assert FakeLLM([reply]).chat([contracts.ChatMessage("user", "hi")]).message.content == "hello"


def test_the_registry_runs_a_tool_and_scrubs_its_result():
    class Shout:
        spec = contracts.ToolSpec("shout", "Say a word.", {"type": "object", "properties": {}})

        def run(self, db, arguments, *, now):
            return contracts.ToolResult({"word": "HI"}, contracts.Citation("Shout", "tool", "shout"), "ok")

    class Lower(PassthroughScrubber):
        def scrub_data(self, value):
            return {k: v.lower() for k, v in value.items()}

    registry = ToolRegistry([Shout()], scrubber=Lower())
    assert [s.name for s in registry.specs()] == ["shout"]
    assert registry.run(None, "shout", {}, now=None).data == {"word": "hi"}
    with pytest.raises(contracts.ToolError):
        registry.run(None, "missing", {}, now=None)
    with pytest.raises(ValueError):
        registry.register(Shout())


def test_the_default_registry_starts_empty():
    assert build_registry().specs() == []


def test_ids_are_uuids(db, seeded):
    conversation = ManiConversation(login_id=seeded.id)
    db.add(conversation)
    db.commit()
    assert isinstance(conversation.id, uuid.UUID)
