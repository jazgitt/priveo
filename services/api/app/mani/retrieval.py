"""Finds the passages that answer a question (architecture section 7).

On PostgreSQL two searches run, by meaning (pgvector cosine distance) and by words
(full-text rank), and their results are merged with reciprocal rank fusion. A requirement ID in
the question (AUTH-13) puts the chunks that name it first. SQLite has no vectors, so the API
tests there get a plain keyword score. Only chunks of active sources are searched."""
import re
from collections import defaultdict

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import Session

from app.mani.contracts import Citation, Embedder, ModelError, Passage
from app.mani.ingest import REQUIREMENT_ID, requirement_ids
from app.mani.models import ManiChunk, ManiSource

RRF_K = 60  # the usual constant: a rank-1 hit is worth 1/61, rank-10 1/70
ID_BOOST = 1.0  # far above any fused score (at most about 0.033), so a named ID sorts first
_STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how", "i", "if",
         "in", "is", "it", "me", "my", "of", "on", "or", "so", "the", "to", "we", "what", "when", "where",
         "which", "who", "why", "will", "with", "you", "our", "us", "that", "this", "there", "than", "then"}
_WORD = re.compile(r"[A-Za-z0-9]+")


def _terms(query: str) -> list[str]:
    """The words of a question that carry meaning, lower case, without repeats."""
    words = [w.lower() for w in _WORD.findall(REQUIREMENT_ID.sub(" ", query))]
    return list(dict.fromkeys(w for w in words if len(w) > 1 and w not in _STOP))


class HybridRetriever:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    def search(self, db: Session, query: str, *, limit: int = 6) -> list[Passage]:
        if not query.strip() or limit <= 0:
            return []
        wanted = requirement_ids(query)
        if db.get_bind().dialect.name == "postgresql":
            scores = self._postgres_scores(db, query, wanted, limit)
        else:
            scores = self._keyword_scores(db, query, wanted)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
        if not ranked:
            return []
        rows = db.execute(
            select(ManiChunk, ManiSource).join(ManiSource, ManiSource.id == ManiChunk.source_id)
            .where(ManiChunk.id.in_([chunk_id for chunk_id, _ in ranked]))).all()
        by_id = {chunk.id: (chunk, source) for chunk, source in rows}
        passages = []
        for chunk_id, score in ranked:
            chunk, source = by_id[chunk_id]
            match = next((r for r in wanted if r in (chunk.requirement_ids or [])), None)
            passages.append(Passage(chunk.text, Citation(
                title=source.title, kind=source.kind, path=source.path, requirement_id=match,
                commit_id=source.commit_id, as_of=source.indexed_at), score))
        return passages

    # ---- PostgreSQL: vectors, full text, fusion --------------------------------------------

    def _postgres_scores(self, db: Session, query: str, wanted: list[str], limit: int) -> dict:
        k = max(limit * 4, 20)
        active = (ManiSource.status == "active")
        base = select(ManiChunk.id).join(ManiSource, ManiSource.id == ManiChunk.source_id).where(active)
        lists: list[list] = []

        try:
            vector = self._embedder.embed([query]).vectors[0]
        except ModelError:
            vector = None  # the words still work without the model
        if vector is not None:
            lists.append(list(db.scalars(
                base.where(ManiChunk.embedding.is_not(None))
                .order_by(ManiChunk.embedding.cosine_distance(vector)).limit(k))))

        terms = _terms(query)
        if terms:
            document = func.to_tsvector("english", ManiChunk.text)
            # Any word may match (OR), so a long question still finds a chunk with a few of them.
            tsquery = func.to_tsquery("english", " | ".join(terms))
            lists.append(list(db.scalars(
                base.where(document.op("@@")(tsquery))
                .order_by(func.ts_rank(document, tsquery).desc()).limit(k))))

        scores: dict = defaultdict(float)
        for ranking in lists:
            for rank, chunk_id in enumerate(ranking, start=1):
                scores[chunk_id] += 1.0 / (RRF_K + rank)
        for chunk_id in self._chunks_naming(db, wanted, base, k):
            scores[chunk_id] += ID_BOOST
        return scores

    @staticmethod
    def _chunks_naming(db: Session, wanted: list[str], base, k: int) -> list:
        if not wanted:
            return []
        stored = cast(ManiChunk.requirement_ids, Text)  # '["AUTH-13", "AUTH-14"]'
        named = or_(*[stored.like(f'%"{r}"%') for r in wanted])
        return list(db.scalars(base.where(named).limit(k)))

    # ---- SQLite and anything without vectors ------------------------------------------------

    def _keyword_scores(self, db: Session, query: str, wanted: list[str]) -> dict:
        terms = _terms(query)
        rows = db.execute(
            select(ManiChunk.id, ManiChunk.text, ManiChunk.heading, ManiChunk.requirement_ids)
            .join(ManiSource, ManiSource.id == ManiChunk.source_id)
            .where(ManiSource.status == "active")).all()
        scores: dict = {}
        for chunk_id, text, heading, ids in rows:
            lowered, head = text.lower(), (heading or "").lower()
            words = _WORD.findall(lowered)
            hits = sum(min(words.count(t), 3) + (2 if t in head else 0) for t in terms)
            score = hits / (len(words) ** 0.5 + 1) if hits else 0.0
            if wanted and any(r in (ids or []) for r in wanted):
                score += ID_BOOST
            if score > 0:
                scores[chunk_id] = score
        return scores
