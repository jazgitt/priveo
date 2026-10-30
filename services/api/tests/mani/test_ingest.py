"""The indexer: idempotent, scrubbed before it embeds, one bad file does not stop the run."""
from datetime import UTC, datetime

import pytest
from app.mani.contracts import EmbedResult, ModelError, ScrubResult, Usage
from app.mani.ingest import (
    IngestReport,
    chunk_code,
    chunk_markdown,
    ingest,
    requirement_ids,
)
from app.mani.models import ManiChunk, ManiSource
from sqlalchemy import func, select

from tests.mani.fakes import FakeEmbedder, PassthroughScrubber

SECRET = "hunter2-planted-secret"
NOW = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)


class RedactingScrubber:
    def __init__(self) -> None:
        self.paths: list[str | None] = []

    def scrub(self, text, *, source_path=None):
        self.paths.append(source_path)
        return ScrubResult(text.replace(SECRET, "[REDACTED]"), {"secret": text.count(SECRET)})

    def scrub_data(self, value):
        return value


class FailingFor(FakeEmbedder):
    """Raises when a text holds the marker, so one source fails."""

    def embed(self, texts):
        if any("EXPLODE" in t for t in texts):
            raise ModelError("embedding backend is down")
        return super().embed(texts)


class OtherModel(FakeEmbedder):
    model = "another-embedding"


@pytest.fixture
def repo(tmp_path):
    files = {
        "README.md": "# Priveo\n\nA car care service.\n\n## Billing\n\nAn Over due payment (PAY-12) for 7 days makes "
                     "a subscription Inactive. See ADM-CNC-10 and AUTH-13. Not UTF-8 or SHA-256 either.\n",
        "docs/reqs/crew.md": "# Crew\n\n| CRW-ACC-07 | Crew sign in by mobile | Owner |\n",
        "services/api/app/billing/service.py": "def mark_overdue():\n    return 1\n\n\ndef other():\n    return 2\n",
    }
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    return tmp_path


def run(db, repo, embedder=None, scrubber=None, **kw):
    return ingest(db, repo, embedder or FakeEmbedder(), scrubber or PassthroughScrubber(), **kw)


def sources(db):
    return {s.path: s for s in db.scalars(select(ManiSource))}


def test_a_first_run_adds_every_source_with_chunks(db, repo):
    report = run(db, repo, commit_id="abc123", now=NOW)
    assert (report.added, report.updated, report.unchanged, report.deleted, report.failed) == (3, 0, 0, 0, 0)
    assert report.chunks == db.scalar(select(func.count()).select_from(ManiChunk)) > 0
    assert report.tokens > 0
    row = sources(db)["README.md"]
    assert (row.status, row.commit_id, row.embedding_model, row.embedding_dimensions) == (
        "active", "abc123", "fake-embedding", 1024)
    assert row.title == "Priveo" and row.kind == "doc"
    assert row.indexed_at.replace(tzinfo=None) == NOW.replace(tzinfo=None)
    assert len(row.content_hash) == 64


def test_a_second_run_changes_nothing(db, repo):
    run(db, repo, commit_id="abc")
    ids = {c.id for c in db.scalars(select(ManiChunk))}
    embedder = FakeEmbedder()
    report = run(db, repo, embedder, commit_id="abc")
    assert report == IngestReport(unchanged=3)
    assert embedder.calls == []
    assert {c.id for c in db.scalars(select(ManiChunk))} == ids


def test_a_changed_file_is_reindexed_and_others_are_not(db, repo):
    run(db, repo)
    (repo / "docs/reqs/crew.md").write_text("# Crew\n\n| CRW-ACC-08 | Crew change password | Owner |\n")
    embedder = FakeEmbedder()
    report = run(db, repo, embedder)
    assert (report.updated, report.unchanged, report.added) == (1, 2, 0)
    chunks = db.scalars(select(ManiChunk).join(ManiSource).where(ManiSource.path == "docs/reqs/crew.md")).all()
    assert [c.requirement_ids for c in chunks] == [["CRW-ACC-08"]]
    assert len(embedder.calls) == 1


def test_a_deleted_file_is_marked_and_its_chunks_removed(db, repo):
    run(db, repo)
    (repo / "docs/reqs/crew.md").unlink()
    report = run(db, repo)
    assert (report.deleted, report.unchanged) == (1, 2)
    row = sources(db)["docs/reqs/crew.md"]
    assert row.status == "deleted"
    assert db.scalar(select(func.count()).select_from(ManiChunk).where(ManiChunk.source_id == row.id)) == 0
    assert run(db, repo) == IngestReport(unchanged=2)  # a deleted source is not reported again


def test_a_file_that_comes_back_is_indexed_again(db, repo):
    run(db, repo)
    body = (repo / "docs/reqs/crew.md").read_text()
    (repo / "docs/reqs/crew.md").unlink()
    run(db, repo)
    (repo / "docs/reqs/crew.md").write_text(body)
    report = run(db, repo)
    assert report.updated == 1
    assert sources(db)["docs/reqs/crew.md"].status == "active"


def test_one_failing_source_does_not_stop_the_rest(db, repo):
    (repo / "services/api/app/billing/service.py").write_text("def explode():\n    return 'EXPLODE'\n")
    report = run(db, repo, FailingFor())
    assert (report.added, report.failed) == (2, 1)
    bad = sources(db)["services/api/app/billing/service.py"]
    assert bad.status == "failed" and "embedding backend is down" in bad.error
    assert sources(db)["README.md"].status == "active"
    # Fixing the file indexes it on the next run.
    (repo / "services/api/app/billing/service.py").write_text("def fine():\n    return 1\n")
    report = run(db, repo)
    assert (report.updated, report.unchanged, report.failed) == (1, 2, 0)
    assert sources(db)["services/api/app/billing/service.py"].status == "active"


def test_a_failure_keeps_the_old_chunks_but_the_source_is_not_active(db, repo):
    run(db, repo)
    (repo / "docs/reqs/crew.md").write_text("# Crew\n\nEXPLODE\n")
    report = run(db, repo, FailingFor())
    assert report.failed == 1
    row = sources(db)["docs/reqs/crew.md"]
    assert row.status == "failed"
    assert db.scalar(select(func.count()).select_from(ManiChunk).where(ManiChunk.source_id == row.id)) == 1


def test_a_large_or_binary_file_fails_with_a_reason(db, repo):
    (repo / "docs/reqs/big.md").write_text("x" * 1_000_001)
    (repo / "docs/reqs/bin.md").write_bytes(b"abc\0def")
    (repo / "docs/reqs/latin.md").write_bytes(b"caf\xe9")
    report = run(db, repo)
    assert (report.added, report.failed) == (3, 3)
    found = sources(db)
    assert "limit" in found["docs/reqs/big.md"].error
    assert "binary" in found["docs/reqs/bin.md"].error
    assert "UTF-8" in found["docs/reqs/latin.md"].error


def test_only_scrubbed_text_is_stored_and_embedded(db, repo):
    (repo / "README.md").write_text(f"# Priveo\n\nThe password is {SECRET} and that is all.\n")
    embedder, scrubber = FakeEmbedder(), RedactingScrubber()
    run(db, repo, embedder, scrubber)
    assert "README.md" in scrubber.paths
    assert all(SECRET not in t for call in embedder.calls for t in call)
    assert any("[REDACTED]" in t for call in embedder.calls for t in call)
    stored = " ".join(c.text for c in db.scalars(select(ManiChunk)))
    assert SECRET not in stored and "[REDACTED]" in stored
    assert all(SECRET not in (s.title + s.error) for s in db.scalars(select(ManiSource)))


def test_the_hash_is_of_the_raw_file_so_a_scrub_change_is_not_a_content_change(db, repo):
    (repo / "README.md").write_text(f"# Priveo\n\n{SECRET}\n")
    run(db, repo, scrubber=RedactingScrubber())
    assert run(db, repo, scrubber=RedactingScrubber()).unchanged == 3


def test_a_new_embedding_model_reembeds_everything(db, repo):
    run(db, repo)
    embedder = OtherModel()
    report = run(db, repo, embedder)
    assert (report.updated, report.unchanged) == (3, 0)
    assert len(embedder.calls) >= 3
    assert {s.embedding_model for s in sources(db).values()} == {"another-embedding"}


def test_changed_dimensions_force_a_reindex(db, repo):
    run(db, repo)
    for row in sources(db).values():
        row.embedding_dimensions = 768
    db.commit()
    assert run(db, repo).updated == 3


def test_a_new_commit_updates_the_citation_without_reindexing(db, repo):
    run(db, repo, commit_id="one")
    embedder = FakeEmbedder()
    report = run(db, repo, embedder, commit_id="two")
    assert report.unchanged == 3 and embedder.calls == []
    assert {s.commit_id for s in sources(db).values()} == {"two"}


def test_requirement_ids_are_extracted_per_chunk(db, repo):
    run(db, repo)
    readme = db.scalars(select(ManiChunk).join(ManiSource).where(ManiSource.path == "README.md")).all()
    found = {i for c in readme for i in c.requirement_ids}
    assert found == {"PAY-12", "ADM-CNC-10", "AUTH-13"}


def test_requirement_id_pattern():
    assert requirement_ids("AUTH-13, ADM-CNC-10 and CRW-ACC-07; BU-2 again BU-2 ADD-15") == [
        "AUTH-13", "ADM-CNC-10", "CRW-ACC-07", "BU-2", "ADD-15"]
    assert requirement_ids("UTF-8, SHA-256, ISO-8601 and utf-8") == []


def test_embedding_goes_out_in_batches_of_32(db, repo):
    body = "\n\n".join(f"Paragraph {i} " + "word " * 220 for i in range(70))
    (repo / "docs/reqs/long.md").write_text("# Long\n\n" + body)
    embedder = FakeEmbedder()
    run(db, repo, embedder)
    sizes = [len(c) for c in embedder.calls]
    assert max(sizes) == 32 and sizes.count(32) >= 2


def test_a_wrong_vector_count_fails_that_source(db, repo):
    class Short(FakeEmbedder):
        def embed(self, texts):
            return EmbedResult([], Usage())

    report = run(db, repo, Short())
    assert report.failed == 3 and report.added == 0
    assert all(s.status == "failed" for s in sources(db).values())


# ---- Chunking -------------------------------------------------------------------------------


def test_markdown_chunks_follow_headings_and_stay_under_the_cap():
    text = "# Top\n\nintro\n\n## Rules\n\n" + "\n\n".join(f"Rule {i}. " + "word " * 60 for i in range(12)) + \
        "\n\n## Last\n\nshort"
    chunks = chunk_markdown(text)
    assert [c.heading for c in chunks][0] == "Top" and chunks[-1].heading == "Last"
    rules = [c for c in chunks if c.heading == "Rules"]
    assert len(rules) > 1
    assert all(len(c.text) <= 1200 + 150 + 2 for c in chunks)
    # The tail of one chunk starts the next, so nothing is cut cleanly in two.
    assert rules[0].text[-40:].strip().split()[-1] in rules[1].text


def test_code_chunks_hold_whole_definitions_and_cut_a_long_line():
    code = "def a():\n    pass\n\n\nclass B:\n    def m(self):\n        pass\n"
    chunks = chunk_code(code)
    assert len(chunks) == 1 and chunks[0].heading == "def a():" and "class B:" in chunks[0].text
    big = "def one():\n" + "    x = 1\n" * 90 + "\ndef two():\n" + "    y = 2\n" * 90 + "\nz = '" + "q" * 3000 + "'\n"
    chunks = chunk_code(big)
    assert chunks[0].heading == "def one():" and any(c.heading.startswith("def two") for c in chunks)
    assert all(len(c.text) <= 1200 + 152 for c in chunks)


def test_json_chunks_are_labelled_by_key():
    body = ",\n".join(f'  "key{i}": {{\n    "v": "{"x" * 200}"\n  }}' for i in range(12))
    chunks = chunk_code("{\n" + body + "\n}\n", json_like=True)
    assert len(chunks) > 1 and all(c.heading.startswith("key") for c in chunks[1:])
