"""Checks the search alone, with no chat model, on the documentation questions that name their
facts (`Question.gold`). It runs the real hybrid retriever against an ingested PostgreSQL
database, read only, so the embeddings are used. (The full evaluation copies the sources into
SQLite, where search falls back to keywords and the embeddings are never tried.)

    python -m tests.mani_eval.retrieval_check --database-url postgresql+psycopg://... [--only 9,11]

Needs the embedding model from the Mani settings (normally local Ollama). Prints, per fact, the
best rank of a gold chunk in the vector list, the word list and after fusion, and the stage."""
import argparse
import sys
from collections.abc import Sequence

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.mani.agent import SEARCH_LIMIT
from app.mani.config import get_mani_settings
from app.mani.llm import build_embedder
from app.mani.retrieval import HybridRetriever, RetrievalTrace
from tests.mani_eval.questions import SETS, Question
from tests.mani_eval.stage import StageResult, classify


def check_question(db: Session, retriever: HybridRetriever, question: Question) -> StageResult:
    trace = RetrievalTrace()
    retriever.search(db, question.prompt, limit=SEARCH_LIMIT, trace=trace)
    # No answer is produced here, so a question whose phrases all reach the results is "retrieved",
    # not blamed on the model.
    return classify(db, question.gold, [trace], answer_passed=True, phrases=question.params["phrases_all"])


def summarize(results: dict[int, StageResult], limit: int = SEARCH_LIMIT) -> dict[str, float]:
    """Share of facts whose best gold chunk is in the top 1, 3 and `limit` after fusion, and
    the mean reciprocal rank (a fact never ranked counts 0)."""
    ranks = [f.hybrid_rank for r in results.values() for f in r.facts]
    total = len(ranks) or 1
    return {**{f"hit@{k}": sum(1 for r in ranks if r and r <= k) / total for k in (1, 3, limit)},
            "mrr": sum(1 / r for r in ranks if r) / total}


def render(results: dict[int, StageResult]) -> str:
    def show(rank):
        return "-" if rank is None else str(rank)

    lines = ["Retrieval check (rank 1 is best; '-' means not in that list)", ""]
    for qid, result in results.items():
        lines.append(f"Q{qid}: {result.stage}")
        for f in result.facts:
            lines.append(f"    {f.pattern[:50]!r}: gold chunks {f.gold_chunks}, vector {show(f.vector_rank)}, "
                         f"words {show(f.lexical_rank)}, fused {show(f.hybrid_rank)}, "
                         f"returned {'yes' if f.returned else 'no'} -> {f.stage}")
    lines += ["", ", ".join(f"{k} {v:.2f}" for k, v in summarize(results).items())]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, prog="python -m tests.mani_eval.retrieval_check")
    parser.add_argument("--database-url", required=True, help="an ingested PostgreSQL database (read only)")
    parser.add_argument("--set", dest="sets", metavar="NAMES", help="parts of the question set: A1, A2, B, C, D")
    parser.add_argument("--only", metavar="IDS", help="question numbers, for example 9,11")
    args = parser.parse_args(argv)
    names = [n.strip().upper() for n in args.sets.split(",")] if args.sets else list(SETS)
    if any(n not in SETS for n in names):
        parser.error(f"--set takes {', '.join(SETS)}")
    chosen = [q for n in names for q in SETS[n] if q.gold]
    if args.only:
        wanted = {int(n) for n in args.only.split(",")}
        chosen = [q for q in chosen if q.id in wanted]
    engine = create_engine(args.database_url)
    try:
        retriever = HybridRetriever(build_embedder(get_mani_settings()))
        with Session(engine) as db:
            if db.get_bind().dialect.name != "postgresql":
                print("Give a PostgreSQL database: vector search needs it.", file=sys.stderr)
                return 2
            results = {q.id: check_question(db, retriever, q) for q in chosen}
    finally:
        engine.dispose()
    print(render(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
