"""Places a failed documentation question in the pipeline: was the fact indexed, did a search
find it, did the ranking keep it, and did the model still get it wrong.

A question lists the facts its answer rests on (`Question.gold`, regexes). A chunk that matches
one is a gold chunk. The checks run in pipeline order and the first one that fails is the stage:

    not-indexed    no active chunk holds the fact: ingestion or chunking
    not-retrieved  neither the vector search nor the word search listed a gold chunk: embeddings
    dropped        a search listed it but the fusion, weights, limit or floor left it out: ranking
    model-wrong    a gold chunk was returned and the answer still failed: model or grader

A whole question gets the earliest stage any of its facts reached.

When the question's required phrases are given, they decide whether retrieval worked: if the
returned passages together state every phrase, the facts reached the model (a fact that also lives
in another chunk is fine), and a failed answer is the model's. If a phrase is missing, the gold
checks say where the pipeline lost it, and "dropped" is the label when every gold chunk was returned
but another chunk the answer needs was not."""
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.mani.models import ManiChunk, ManiSource
from app.mani.retrieval import RetrievalTrace
from tests.mani_eval.scoring import has

STAGES = ("not-indexed", "not-retrieved", "dropped", "model-wrong")


@dataclass
class FactResult:
    pattern: str
    stage: str  # one of STAGES, or "retrieved" when the fact reached the model's context
    gold_chunks: int = 0
    vector_rank: int | None = None  # best rank of a gold chunk in each list; None when absent
    lexical_rank: int | None = None
    hybrid_rank: int | None = None  # position after fusion and boost, over all chunks
    returned: bool = False


@dataclass
class StageResult:
    stage: str
    facts: list[FactResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"stage": self.stage, "facts": [vars(f) for f in self.facts]}


def gold_chunk_ids(db: Session, pattern: str) -> list[Any]:
    """The active chunks whose heading and text match the pattern."""
    regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    rows = db.execute(
        select(ManiChunk.id, ManiChunk.heading, ManiChunk.text)
        .join(ManiSource, ManiSource.id == ManiChunk.source_id)
        .where(ManiSource.status == "active")).all()
    return [chunk_id for chunk_id, heading, text in rows
            if regex.search(f"{heading or ''}\n{text or ''}")]


def _best(ranks: dict[Any, int], ids: set) -> int | None:
    found = [rank for chunk_id, rank in ranks.items() if chunk_id in ids]
    return min(found) if found else None


def check_fact(db: Session, pattern: str, traces: Sequence[RetrievalTrace]) -> FactResult:
    """Where one fact stands after the searches in `traces`."""
    gold = set(gold_chunk_ids(db, pattern))
    result = FactResult(pattern, "not-indexed", gold_chunks=len(gold))
    if not gold:
        return result
    ordered = [sorted(t.fused, key=t.fused.get, reverse=True) for t in traces]
    hybrid = [i + 1 for order in ordered for i, chunk_id in enumerate(order) if chunk_id in gold]
    result.hybrid_rank = min(hybrid) if hybrid else None
    vector = [r for r in (_best(t.vector, gold) for t in traces) if r]
    lexical = [r for r in (_best(t.lexical, gold) for t in traces) if r]
    result.vector_rank = min(vector) if vector else None
    result.lexical_rank = min(lexical) if lexical else None
    result.returned = any(chunk_id in gold for t in traces for chunk_id in t.returned)
    if result.returned:
        result.stage = "retrieved"
    elif any(chunk_id in gold for t in traces for chunk_id in t.fused):
        result.stage = "dropped"
    else:
        result.stage = "not-retrieved"
    return result


def returned_text(db: Session, traces: Sequence[RetrievalTrace]) -> str:
    """The heading and text of every chunk the searches returned."""
    ids = {chunk_id for t in traces for chunk_id in t.returned}
    if not ids:
        return ""
    rows = db.execute(select(ManiChunk.heading, ManiChunk.text).where(ManiChunk.id.in_(ids))).all()
    return "\n".join(f"{heading or ''}\n{text or ''}" for heading, text in rows)


def missing_phrases(db: Session, phrases: Sequence[str], traces: Sequence[RetrievalTrace]) -> list[str]:
    """The required phrases that no returned passage states."""
    text = returned_text(db, traces)
    return [p for p in phrases if not has(p, text)]


def classify(db: Session, patterns: Sequence[str], traces: Sequence[RetrievalTrace], *,
             answer_passed: bool = False, phrases: Sequence[str] = ()) -> StageResult:
    """The stage of a question. `answer_passed` True gives "retrieved" at worst: nothing failed."""
    facts = [check_fact(db, p, traces) for p in patterns]
    done = "retrieved" if answer_passed else "model-wrong"
    if phrases and not missing_phrases(db, phrases, traces):
        return StageResult("retrieved" if answer_passed else "model-wrong", facts)
    for stage in STAGES[:3]:
        if any(f.stage == stage for f in facts):
            return StageResult(stage, facts)
    if phrases:  # every gold chunk came back, but a phrase the answer needs did not
        return StageResult("dropped", facts)
    return StageResult(done, facts)
