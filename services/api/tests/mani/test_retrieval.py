"""Retrieval: vectors plus words on PostgreSQL, a keyword score elsewhere."""
from datetime import UTC, datetime

import pytest

from app.mani.contracts import ModelError, Retriever
from app.mani.models import ManiChunk, ManiSource
from app.mani.retrieval import HybridRetriever, RetrievalTrace
from tests.mani.fakes import FakeEmbedder, word_overlap_vector

AS_OF = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)

CHUNKS = {
    "docs/reqs/admin.md": ("Admin requirements", "doc", [
        ("Payments", "A payment that is over due for seven days makes the subscription inactive.", ["ADM-PAY-04"]),
        ("Crew", "Crew members wash cars every morning before the customer cut off.", ["CRW-SCH-01"]),
    ]),
    "docs/reqs/customer.md": ("Customer requirements", "doc", [
        ("Pause", "Customers pause their plan for a week and the billing cycle moves on.", ["PAUSE-03"]),
        ("Sign in", "Customers sign in with an emailed code and then a password.", ["AUTH-13"]),
    ]),
    "services/api/app/billing/service.py": ("service.py", "code", [
        ("def mark_overdue", "def mark_overdue(): subscription inactive after seven days over due", []),
    ]),
}


def add(db, path, title, kind, chunks, *, status="active", embedder_vector=word_overlap_vector):
    source = ManiSource(path=path, title=title, kind=kind, status=status, commit_id="abc123", indexed_at=AS_OF)
    db.add(source)
    db.flush()
    for i, (heading, text, ids) in enumerate(chunks):
        db.add(ManiChunk(source_id=source.id, ordinal=i, heading=heading, text=text, requirement_ids=ids,
                         embedding=embedder_vector(text)))
    db.commit()
    return source


@pytest.fixture
def indexed(db):
    for path, (title, kind, chunks) in CHUNKS.items():
        add(db, path, title, kind, chunks)
    return db


class Down(FakeEmbedder):
    def embed(self, texts):
        raise ModelError("backend is down")


def test_it_satisfies_the_retriever_interface():
    retriever: Retriever = HybridRetriever(FakeEmbedder())
    assert callable(retriever.search)


def test_the_best_chunk_comes_first_with_its_citation(indexed):
    found = HybridRetriever(FakeEmbedder()).search(indexed, "when is a subscription made inactive for over due payment")
    assert found[0].text.startswith("A payment that is over due") or "over due" in found[0].text
    top = found[0].citation
    assert top.commit_id == "abc123" and top.as_of is not None and top.kind in ("doc", "code")
    assert top.path and top.title
    assert found == sorted(found, key=lambda p: p.score, reverse=True)


def test_a_requirement_id_puts_its_chunk_first_and_is_cited(indexed):
    found = HybridRetriever(FakeEmbedder()).search(indexed, "what does AUTH-13 say about payments")
    assert found[0].citation.requirement_id == "AUTH-13"
    assert found[0].citation.path == "docs/reqs/customer.md"
    assert all(p.citation.requirement_id in (None, "AUTH-13") for p in found)


def test_an_unknown_requirement_id_changes_nothing(indexed):
    found = HybridRetriever(FakeEmbedder()).search(indexed, "ZZZ-99 crew wash cars")
    assert "wash cars" in found[0].text and found[0].citation.requirement_id is None


def test_inactive_sources_are_never_returned(indexed):
    old = ("Old", "A payment over due for seven days (old rule) AUTH-13", ["AUTH-13"])
    add(indexed, "docs/old.md", "Old", "doc", [old], status="deleted")
    add(indexed, "docs/bad.md", "Bad", "doc", [("Bad", "A payment over due for seven days (bad)", [])], status="failed")
    found = HybridRetriever(FakeEmbedder()).search(indexed, "payment over due for seven days AUTH-13", limit=20)
    assert found and all(p.citation.path not in ("docs/old.md", "docs/bad.md") for p in found)


def test_the_limit_is_respected_and_empty_queries_return_nothing(indexed):
    retriever = HybridRetriever(FakeEmbedder())
    assert len(retriever.search(indexed, "customers crew payment", limit=2)) <= 2
    assert retriever.search(indexed, "   ") == []
    assert retriever.search(indexed, "payment", limit=0) == []


def test_an_embedder_failure_falls_back_to_the_words(indexed):
    found = HybridRetriever(Down()).search(indexed, "crew wash cars every morning")
    assert found and "wash cars" in found[0].text


def test_a_database_with_nothing_indexed_returns_nothing(db):
    assert HybridRetriever(FakeEmbedder()).search(db, "anything at all") == []


def test_ranking_uses_vectors_and_words_together(db, engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("pgvector and full-text search need PostgreSQL")
    add(db, "a.md", "A", "doc", [("A", "invoice reminders go out gently", [])])
    for path, (title, kind, chunks) in CHUNKS.items():
        add(db, path, title, kind, chunks)
    found = HybridRetriever(FakeEmbedder()).search(db, "invoice reminders")
    assert found[0].citation.path == "a.md"  # first by meaning and by words
    # A chunk with no embedding is still found by its words.
    source = ManiSource(path="b.md", title="B", kind="doc", status="active", indexed_at=AS_OF)
    db.add(source)
    db.flush()
    db.add(ManiChunk(source_id=source.id, ordinal=0, text="zebra stripes are unique", requirement_ids=[]))
    db.commit()
    found = HybridRetriever(FakeEmbedder()).search(db, "zebra")
    assert "b.md" in [p.citation.path for p in found]


def test_vector_order_on_postgresql_even_with_no_shared_words(db, engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("pgvector needs PostgreSQL")
    for path, (title, kind, chunks) in CHUNKS.items():
        add(db, path, title, kind, chunks)

    class Fixed(FakeEmbedder):
        """Answers every query with the vector of one chunk, as a model that understood the
        question would, though the question shares no word with it."""

        def embed(self, texts):
            from app.mani.contracts import EmbedResult, Usage
            return EmbedResult([word_overlap_vector("Customers pause their plan for a week and the billing "
                                                    "cycle moves on.")] * len(texts), Usage())

    found = HybridRetriever(Fixed()).search(db, "holiday suspension question")
    assert found[0].citation.requirement_id is None and "pause their plan" in found[0].text


def test_requirement_id_boost_on_postgresql(db, engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("the boost query is checked on PostgreSQL as well as SQLite")
    for path, (title, kind, chunks) in CHUNKS.items():
        add(db, path, title, kind, chunks)
    found = HybridRetriever(FakeEmbedder()).search(db, "crew wash cars every morning ADM-PAY-04")
    assert found[0].citation.requirement_id == "ADM-PAY-04"
    assert any("wash cars" in p.text for p in found)


def test_a_passage_far_weaker_than_the_best_is_left_out(db):
    if db.get_bind().dialect.name == "postgresql":
        pytest.skip("rank fusion keeps scores close; the floor is checked on word scores")
    add(db, "docs/a.md", "A", "doc", [("Billing", "invoice invoice invoice reminders reminders", [])])
    add(db, "docs/b.md", "B", "doc", [("Notes", " ".join(["filler"] * 200) + " invoice", [])])
    found = HybridRetriever(FakeEmbedder()).search(db, "invoice reminders")
    assert [p.citation.path for p in found] == ["docs/a.md"]


def test_a_named_requirement_id_does_not_push_out_the_passages_around_it(db):
    add(db, "docs/a.md", "A", "doc", [("Pay", "payment rules AUTH-13 over due", ["AUTH-13"])])
    add(db, "docs/b.md", "B", "doc", [("Pay", "payment over due reminders", [])])
    found = HybridRetriever(FakeEmbedder()).search(db, "payment over due AUTH-13")
    assert [p.citation.path for p in found] == ["docs/a.md", "docs/b.md"]


def test_a_trace_records_the_search_and_changes_nothing(indexed):
    retriever = HybridRetriever(FakeEmbedder())
    query = "when is a subscription made inactive for over due payment"
    plain = retriever.search(indexed, query)
    trace = RetrievalTrace()
    traced = retriever.search(indexed, query, trace=trace)
    assert [p.text for p in traced] == [p.text for p in plain]
    assert trace.query == query and trace.top and trace.returned
    assert set(trace.returned) <= set(trace.top) <= set(trace.fused)


def test_one_source_supplies_at_most_two_passages(db):
    add(db, "docs/long.md", "Long", "doc",
        [(f"Part {i}", f"inactive subscription rule number {i} for over due payment", []) for i in range(5)])
    add(db, "docs/other.md", "Other", "doc", [("Other", "an over due payment makes a subscription inactive", [])])
    found = HybridRetriever(FakeEmbedder()).search(db, "over due payment inactive subscription", limit=6)
    paths = [p.citation.path for p in found]
    assert paths.count("docs/long.md") <= 2 and "docs/other.md" in paths


def test_a_question_that_asks_two_things_is_split_and_a_short_half_is_not():
    from app.mani.retrieval import _parts
    assert _parts("Which scheduled jobs does the API expose, and where do they run?") == [
        "Which scheduled jobs does the API expose", "where do they run"]
    assert _parts("Which security findings are open, and which is High?") == []  # "High" alone is too thin
    assert _parts("What is the latest migration?") == []


def test_a_document_named_in_the_question_supplies_more_passages(db):
    add(db, "docs/system-component-diagram.md", "Diagram", "doc",
        [(f"Part {i}", f"component diagram part {i} shows the system", []) for i in range(6)])
    add(db, "docs/other-notes.md", "Notes", "doc",
        [(f"Part {i}", f"component diagram notes {i} shows the system", []) for i in range(6)])
    found = HybridRetriever(FakeEmbedder()).search(db, "what does the system component diagram show", limit=8)
    paths = [p.citation.path for p in found]
    assert paths.count("docs/system-component-diagram.md") == 4 and paths.count("docs/other-notes.md") == 2
