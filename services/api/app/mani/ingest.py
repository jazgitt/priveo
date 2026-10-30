"""Reads the files on the source list, scrubs them, cuts them into chunks and stores one
embedding per chunk. Run it from the command line: `python -m app.mani.ingest [--root PATH]`.

Only scrubbed text is ever stored or sent to the embedder (decision D8). A file whose raw
content has not changed, under the same embedding model and size, is skipped. One bad file
marks that file failed and the run goes on."""
import argparse
import hashlib
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.mani.contracts import Embedder, Scrubber
from app.mani.models import ManiChunk, ManiSource
from app.mani.sources import SourceFile, discover
from app.platform.db import utcnow

MAX_FILE_BYTES = 1_000_000
CHUNK_CHARS = 1200  # a chunk is cut at this size, on a paragraph or line where it can be
OVERLAP_CHARS = 150  # the tail of a chunk repeated at the start of the next one in a section
EMBED_BATCH = 32

# A requirement ID such as AUTH-13, ADM-CNC-10, CRW-ACC-07 or BU-2. The skip list holds
# common look-alikes (UTF-8, SHA-256).
REQUIREMENT_ID = re.compile(r"\b[A-Z]{2,6}(?:-[A-Z]{2,6})?-\d{1,3}\b")
_NOT_REQUIREMENTS = {"UTF", "SHA", "MD", "AES", "HS", "RS", "ES", "TLS", "SSL", "ISO", "RFC", "HTTP",
                     "IPV", "SQL", "PBKDF", "X", "CVE", "SHA3", "PDF", "ECS"}

_MD_HEADING = re.compile(r"^(#{1,4})\s+(.*\S)")
_DEFINITION = re.compile(
    r"^(?:async\s+def|def|class|abstract\s+class|enum|mixin|extension|typedef|function"
    r"|export\s+(?:default\s+)?(?:async\s+)?(?:function|const|class|type|interface))\s+([\w$<>]+)")
# A top-level JSON key, or an API path key one level down (the OpenAPI contract).
_JSON_KEY = re.compile(r'^(?: {0,2}"([^"]+)"|    "(/[^"]*)")\s*:')


def requirement_ids(text: str) -> list[str]:
    """The requirement IDs in a text, in order of first appearance, without repeats."""
    seen: dict[str, None] = {}
    for match in REQUIREMENT_ID.finditer(text):
        value = match.group(0)
        if value.split("-")[0] not in _NOT_REQUIREMENTS:
            seen.setdefault(value)
    return list(seen)


# ---- Chunking -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    heading: str
    text: str


def _split_long(unit: str, cap: int) -> list[str]:
    """Cut a block longer than `cap` on line breaks, and a line longer than `cap` by size."""
    pieces: list[str] = []
    current = ""
    for line in unit.split("\n"):
        while len(line) > cap:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(line[:cap])
            line = line[cap:]
        if current and len(current) + 1 + len(line) > cap:
            pieces.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        pieces.append(current)
    return pieces


def _pack(units: Sequence[tuple[str, str]], cap: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS, *,
          split_on_heading: bool = True) -> list[Chunk]:
    """Join (heading, block) units into chunks of about `cap` characters. With `split_on_heading`
    (Markdown) a new heading starts a new chunk; without it (code) small definitions share a
    chunk, which is labelled with its first heading. When a section runs on, the next chunk
    starts with a short tail of the previous one, so a sentence cut at the boundary is still found."""
    sep = "\n\n" if split_on_heading else "\n"
    chunks: list[Chunk] = []
    heading, body, fresh = "", "", False  # `fresh`: the body holds more than the overlap tail

    def flush() -> None:
        if fresh and body.strip():
            chunks.append(Chunk(heading, body.strip()))

    for unit_heading, block in units:
        for piece in (_split_long(block, cap) if len(block) > cap else [block]):
            if split_on_heading and unit_heading != heading:
                flush()
                heading, body = unit_heading, ""
            elif fresh and len(body) + 2 + len(piece) > cap:
                flush()
                tail = body[-overlap:] if overlap else ""
                body = tail[tail.find("\n") + 1:] if "\n" in tail else tail
                fresh = False
            if not fresh and not split_on_heading:
                heading = unit_heading
            body = f"{body}{sep}{piece}" if body else piece
            fresh = True
    flush()
    return chunks


def _blocks(text: str) -> list[str]:
    return [b.strip("\n") for b in re.split(r"\n\s*\n", text) if b.strip()]


def chunk_markdown(text: str) -> list[Chunk]:
    """By heading, then by paragraph. A fenced code block stays together where it fits."""
    units: list[tuple[str, str]] = []
    heading = ""
    paragraph: list[str] = []
    in_fence = False

    def end_paragraph() -> None:
        if paragraph and "".join(paragraph).strip():
            units.append((heading, "\n".join(paragraph)))
        paragraph.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        found = None if in_fence else _MD_HEADING.match(line)
        if found:
            end_paragraph()
            heading = found.group(2)[:300]
            paragraph.append(line)
        elif not in_fence and not line.strip():
            end_paragraph()
        else:
            paragraph.append(line)
    end_paragraph()
    return _pack(units)


def chunk_code(text: str, *, json_like: bool = False) -> list[Chunk]:
    """By definition (or JSON key) and blank-line block, packed up to the cap. Each chunk is
    labelled with the first definition it holds, or the last one seen before it."""
    pattern = _JSON_KEY if json_like else _DEFINITION
    units: list[tuple[str, str]] = []
    heading = ""
    for number, block in enumerate(_blocks(text)):
        current: list[str] = [""] if number else []  # a blank line between blocks, as in the file
        for line in block.split("\n"):
            found = pattern.match(line)
            if found and len(current) > (1 if number else 0):
                units.append((heading, "\n".join(current)))
                current = []
            if found:
                heading = (next(g for g in found.groups() if g) if json_like else line.strip())[:300]
            current.append(line)
        units.append((heading, "\n".join(current)))
    return _pack(units, split_on_heading=False)


def chunk_text(source: SourceFile, text: str) -> list[Chunk]:
    path = source.path.lower()
    if path.endswith((".md", ".txt")):
        return chunk_markdown(text)
    return chunk_code(text, json_like=path.endswith((".json", ".arb")))


# ---- Ingestion ------------------------------------------------------------------------------


@dataclass
class IngestReport:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    deleted: int = 0
    failed: int = 0
    chunks: int = 0
    tokens: int = 0


def _read(root: Path, source: SourceFile) -> tuple[bytes, str]:
    path = root / source.path
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError(f"The file is {size} bytes, over the {MAX_FILE_BYTES} byte limit.")
    raw = path.read_bytes()
    if b"\0" in raw:
        raise ValueError("The file is binary.")
    try:
        return raw, raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("The file is not UTF-8 text.") from exc


def _embed(embedder: Embedder, texts: list[str]) -> tuple[list[list[float]], int]:
    vectors: list[list[float]] = []
    tokens = 0
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start:start + EMBED_BATCH]
        result = embedder.embed(batch)
        if len(result.vectors) != len(batch):
            raise ValueError("The embedder returned the wrong number of vectors.")
        vectors.extend(result.vectors)
        tokens += result.usage.prompt_tokens
    return vectors, tokens


def _mark_failed(db: Session, source: SourceFile, error: str) -> None:
    db.rollback()
    row = db.scalar(select(ManiSource).where(ManiSource.path == source.path))
    if row is None:
        row = ManiSource(path=source.path)
        db.add(row)
    row.kind, row.title, row.status, row.error = source.kind, source.title[:300], "failed", error[:2000]
    db.commit()


def ingest(db: Session, root: Path, embedder: Embedder, scrubber: Scrubber, *,
           commit_id: str | None = None, now: datetime | None = None) -> IngestReport:
    root = Path(root)
    report = IngestReport()
    stamp = now or utcnow()
    commit = commit_id or ""
    files = discover(root)
    existing = {row.path: row for row in db.scalars(select(ManiSource))}

    for source in files:
        row = existing.get(source.path)
        try:
            raw, text = _read(root, source)
            digest = hashlib.sha256(raw).hexdigest()
            if (row is not None and row.status == "active" and row.content_hash == digest
                    and row.embedding_model == embedder.model
                    and row.embedding_dimensions == embedder.dimensions):
                if commit and row.commit_id != commit:
                    row.commit_id = commit  # the same content, now seen at a newer commit
                    db.commit()
                report.unchanged += 1
                continue

            # Scrub first. Everything after this point sees only the scrubbed text.
            clean = scrubber.scrub(text, source_path=source.path).text
            chunks = chunk_text(source, clean)
            vectors, tokens = _embed(
                embedder, [f"{c.heading}\n{c.text}" if c.heading else c.text for c in chunks])

            if row is None:
                row = ManiSource(path=source.path)
                db.add(row)
                db.flush()
            db.execute(delete(ManiChunk).where(ManiChunk.source_id == row.id),
                       execution_options={"synchronize_session": False})
            for ordinal, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                db.add(ManiChunk(source_id=row.id, ordinal=ordinal, heading=chunk.heading, text=chunk.text,
                                 requirement_ids=requirement_ids(chunk.text), embedding=vector))
            row.kind, row.title = source.kind, source.title[:300]
            row.commit_id, row.content_hash, row.status, row.error = commit, digest, "active", ""
            row.embedding_model, row.embedding_dimensions = embedder.model, embedder.dimensions
            row.indexed_at = stamp
            db.commit()
        except Exception as exc:  # one bad file must not stop the run
            _mark_failed(db, source, f"{type(exc).__name__}: {exc}")
            report.failed += 1
            continue
        if source.path in existing:
            report.updated += 1
        else:
            report.added += 1
            existing[source.path] = row
        report.chunks += len(chunks)
        report.tokens += tokens

    present = {s.path for s in files}
    for path, row in existing.items():
        if path not in present and row.status != "deleted":
            db.execute(delete(ManiChunk).where(ManiChunk.source_id == row.id),
                       execution_options={"synchronize_session": False})
            row.status, row.error = "deleted", ""
            report.deleted += 1
    db.commit()
    return report


# ---- Command line ---------------------------------------------------------------------------


def _head_commit(root: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                             check=True, timeout=30, text=True)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index the Mani source list.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4],
                        help="The repository root (default: this checkout).")
    args = parser.parse_args(argv)
    # These two are built by other parts; import them late so this module loads without them.
    try:
        from app.mani.llm import build_embedder
        from app.mani.scrub import PatternScrubber
    except ImportError as exc:
        print(f"Cannot run the indexer: {exc}. It needs app.mani.llm.build_embedder and "
              "app.mani.scrub.PatternScrubber.", file=sys.stderr)
        return 2
    from app.mani.config import get_mani_settings
    from app.platform.db import get_engine

    root = args.root.resolve()
    with Session(get_engine(), expire_on_commit=False) as db:
        report = ingest(db, root, build_embedder(get_mani_settings()), PatternScrubber(),
                        commit_id=_head_commit(root))
    print(report)
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
