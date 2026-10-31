"""The stage classifier, on hand-made traces."""
from app.mani.retrieval import RetrievalTrace
from tests.mani.test_retrieval import add
from tests.mani_eval.stage import classify

FACT = r"seven days"


def indexed(db):
    add(db, "docs/a.md", "A", "doc", [("Pay", "Over due for seven days makes it inactive.", [])])
    from sqlalchemy import select

    from app.mani.models import ManiChunk
    return db.scalar(select(ManiChunk.id))


def trace(**kwargs):
    return RetrievalTrace(**kwargs)


def test_a_fact_nobody_indexed_is_an_ingestion_failure(db):
    assert classify(db, [FACT], [trace()]).stage == "not-indexed"


def test_a_fact_no_search_listed_is_not_retrieved(db):
    indexed(db)
    assert classify(db, [FACT], [trace(top=[], returned=[])]).stage == "not-retrieved"


def test_a_fact_listed_but_left_out_is_dropped(db):
    chunk = indexed(db)
    result = classify(db, [FACT], [trace(lexical={chunk: 3}, fused={chunk: 0.01})])
    assert result.stage == "dropped"
    assert result.facts[0].lexical_rank == 3 and result.facts[0].hybrid_rank == 1


def test_a_returned_fact_in_a_failed_answer_is_the_models_fault(db):
    chunk = indexed(db)
    found = trace(vector={chunk: 1}, fused={chunk: 0.02}, top=[chunk], returned=[chunk])
    assert classify(db, [FACT], [found]).stage == "model-wrong"
    assert classify(db, [FACT], [found], answer_passed=True).stage == "retrieved"


def test_the_earliest_failing_fact_names_the_question(db):
    chunk = indexed(db)
    found = trace(vector={chunk: 1}, fused={chunk: 0.02}, top=[chunk], returned=[chunk])
    assert classify(db, [FACT, r"no such fact"], [found]).stage == "not-indexed"


# ---- The Postgres-backed search used by the full evaluation ------------------------------------


def test_the_sources_database_must_be_a_local_postgres():
    import pytest

    from tests.mani_eval.runner import check_source_database

    check_source_database("postgresql+psycopg://u:p@localhost:5432/priveo_mani")
    check_source_database("postgresql://u:p@127.0.0.1/priveo_mani")
    with pytest.raises(ValueError, match="local"):
        check_source_database("postgresql://u:p@db.example.supabase.co:5432/postgres")
    with pytest.raises(ValueError, match="PostgreSQL"):
        check_source_database("sqlite:///x.db")


def test_the_source_retriever_searches_its_own_session_not_the_agents(db):
    from sqlalchemy.orm import Session

    from tests.mani_eval.runner import PostgresSourceRetriever, TracingRetriever

    seen = []

    class Inner:
        def search(self, session, query, *, limit=6, trace=None):
            seen.append(session)
            return []

    own = Session(db.get_bind())
    retriever = PostgresSourceRetriever(Inner(), lambda: own)
    tracer = TracingRetriever(retriever)
    tracer.search(db, "anything")
    assert seen == [own] and seen[0] is not db and len(tracer.traces) == 1
    with tracer.source_session(db) as source:
        assert source is own
    with TracingRetriever(Inner()).source_session(db) as source:
        assert source is db


def test_phrases_in_other_chunks_count_as_retrieved(db):
    chunk = indexed(db)
    found = trace(fused={chunk: 0.02}, top=[chunk], returned=[chunk])
    # The gold pattern matches nothing, but the returned text states the phrase.
    assert classify(db, [r"no such fact"], [found], phrases=[r"seven days"]).stage == "model-wrong"
    assert classify(db, [r"no such fact"], [found], answer_passed=True, phrases=[r"seven days"]).stage == "retrieved"


def test_a_missing_phrase_with_every_gold_chunk_returned_is_dropped(db):
    chunk = indexed(db)
    found = trace(fused={chunk: 0.02}, top=[chunk], returned=[chunk])
    assert classify(db, [FACT], [found], phrases=[r"seven days", r"CP-SAT"]).stage == "dropped"
    # And a phrase that no returned chunk has, with an unretrieved gold chunk, keeps the gold stage.
    assert classify(db, [FACT], [trace()], phrases=[r"seven days"]).stage == "not-retrieved"
