"""Runs the question set through any object that satisfies the `Agent` protocol
(`app.mani.contracts`) against the built dataset, and scores the events.

    python -m tests.mani_eval.runner --list
    python -m tests.mani_eval.runner --agent reference --out /tmp/mani-eval.json

Run it from `services/api`. The real agent arrives in Wave 2; `--agent mani` says so."""
import argparse
import contextlib
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.identity.models import Login
from app.mani.contracts import Agent
from app.mani.models import ManiChunk, ManiSource
from app.mani.retrieval import RetrievalTrace
from tests.mani_eval.dataset import FIXED_NOW, DatasetReport, build_dataset, make_engine_at
from tests.mani_eval.expected import Expected, compute_all
from tests.mani_eval.questions import ACTIVE, SETS, Question
from tests.mani_eval.reference import ReferenceAgent
from tests.mani_eval.scoring import Outcome, Report, Score, read_events, score_question
from tests.mani_eval.stage import classify

AgentFactory = Callable[[dict[str, Expected], datetime], Agent]


LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def check_source_database(url: str) -> None:
    """The sources database must be a local PostgreSQL: vector search needs it, and the eval
    never reads a hosted database (Mani is local first)."""
    parsed = make_url(url)
    if not parsed.get_backend_name() == "postgresql":
        raise ValueError("--sources-postgres needs a PostgreSQL database: vector search runs there.")
    if parsed.host not in LOCAL_HOSTS:
        raise ValueError(f"--sources-postgres must be a local database, not {parsed.host}.")


class PostgresSourceRetriever:
    """Runs document search on an ingested PostgreSQL database, read only, whatever session the
    agent passes in. The agent's own session (the throwaway SQLite dataset) keeps the live data,
    conversations and usage; only the indexed sources come from here, so the vectors are used."""

    def __init__(self, inner, session_factory: Callable[[], Session]) -> None:
        self.inner = inner
        self.session = session_factory

    def search(self, db, query, *, limit=6, trace=None):
        with self.session() as source:
            return self.inner.search(source, query, limit=limit, trace=trace)


def open_source_database(url: str) -> Callable[[], Session]:
    """A session factory on the sources database, read only, after checking it is ready."""
    check_source_database(url)
    engine = create_engine(url, connect_args={"options": "-c default_transaction_read_only=on"})
    factory = lambda: Session(engine)  # noqa: E731
    with factory() as source:
        chunks = source.scalar(select(func.count()).select_from(ManiChunk))
        vectors = source.scalar(select(func.count(ManiChunk.embedding)))
    if not chunks or not vectors:
        engine.dispose()
        raise ValueError("The sources database has no embedded chunks. Run `python -m app.mani.ingest`.")
    return factory


class TracingRetriever:
    """Wraps the agent's retriever and keeps the trace of every search, so a failed question
    can be placed in the pipeline. Searches behave exactly as without it."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.traces: list[RetrievalTrace] = []

    def source_session(self, db: Session):
        """The session that holds the indexed chunks: the sources database when there is one."""
        factory = getattr(self.inner, "session", None)
        return factory() if factory else contextlib.nullcontext(db)

    def search(self, db, query, *, limit=6):
        trace = RetrievalTrace()
        passages = self.inner.search(db, query, limit=limit, trace=trace)
        self.traces.append(trace)
        return passages


class EvalMani:
    """The real agent (`app.mani.agent.build_agent`) with the harness's `prepare` hook. It
    needs the configured model backend, normally local Ollama. For a question with the
    precondition "budget_exhausted" it records usage up to the budget before the turn and
    removes it after, so the questions that follow still run."""

    def __init__(self, agent: Agent, settings) -> None:
        self.agent = agent
        self.settings = settings
        self.question: Question | None = None

    def prepare(self, question: Question) -> None:
        self.question = question

    def run_turn(self, db: Session, *, conversation_id, login_id, user_text):
        from decimal import Decimal

        from app.mani.models import ManiModelUsage

        row = None
        if self.question is not None and self.question.precondition == "budget_exhausted" \
                and user_text == self.question.prompt:
            row = ManiModelUsage(kind="chat", backend="eval", model="eval-budget",
                                 cost_usd=Decimal(str(self.settings.budget_usd)))
            db.add(row)
            db.commit()
        try:
            yield from self.agent.run_turn(db, conversation_id=conversation_id, login_id=login_id,
                                           user_text=user_text)
        finally:
            if row is not None:
                db.delete(row)
                db.commit()


def load_real_agent(expected: dict[str, Expected], now: datetime) -> Agent:
    """Builds the real Mani agent with the clock fixed to the dataset's day."""
    from app.mani.agent import build_agent
    from app.mani.config import get_mani_settings

    settings = get_mani_settings()
    agent = build_agent(settings, clock=lambda: now)
    agent.retriever = TracingRetriever(agent.retriever)
    return EvalMani(agent, settings)


AGENTS: dict[str, AgentFactory] = {"reference": ReferenceAgent, "mani": load_real_agent}


def run_question(agent: Agent, db: Session, question: Question, *, login_id: uuid.UUID,
                 expected: dict[str, Expected], dataset: DatasetReport | None) -> Score:
    if question.needs_seed:
        return score_question(question, Outcome(), expected, dataset)
    prepare = getattr(agent, "prepare", None)  # an optional hook, for example to set a budget
    if callable(prepare):
        prepare(question)
    conversation_id = uuid.uuid4()
    outcome = Outcome()
    tracer = getattr(getattr(agent, "agent", None), "retriever", None)
    if isinstance(tracer, TracingRetriever):
        tracer.traces.clear()
    try:
        for text in question.setup:
            list(agent.run_turn(db, conversation_id=conversation_id, login_id=login_id,
                                user_text=text))
        outcome = read_events(agent.run_turn(
            db, conversation_id=conversation_id, login_id=login_id, user_text=question.prompt))
    except Exception as error:  # a crashing agent is a failed answer, not a crashed run
        outcome.errors.append(f"{type(error).__name__}: {error}")
    score = score_question(question, outcome, expected, dataset)
    tracer = getattr(getattr(agent, "agent", None), "retriever", None)
    if question.gold and isinstance(tracer, TracingRetriever):
        with tracer.source_session(db) as source:
            result = classify(source, question.gold, tracer.traces, answer_passed=score.passed,
                              phrases=question.params.get("phrases_all", ()))
        score.stage, score.stage_detail = (result.stage if not score.passed else ""), result.to_dict()
    return score


def run_questions(agent: Agent, db: Session, *, now: datetime = FIXED_NOW,
                  questions: Sequence[Question] = ACTIVE,
                  expected: dict[str, Expected] | None = None,
                  dataset: DatasetReport | None = None) -> Report:
    """Score `agent` on `questions`. The database must already hold the dataset."""
    expected = expected or compute_all(db, now)
    login_id = db.scalar(select(Login.id).where(Login.login_id == "priveopapa"))
    scores = []
    for position, q in enumerate(questions, 1):
        started = time.monotonic()
        score = run_question(agent, db, q, login_id=login_id, expected=expected, dataset=dataset)
        scores.append(score)
        result = "skipped" if score.skipped else "pass" if score.passed else "FAIL"
        print(f"[{position}/{len(questions)}] Q{q.id} {result} ({time.monotonic() - started:.0f}s)",
              file=sys.stderr, flush=True)
    return Report(scores)


def copy_sources(url: str, db: Session) -> tuple[int, int]:
    """Copy the indexed sources and chunks of an ingested database into the eval database,
    so the documentation questions have something to search. Reads only from `url`."""
    source_engine = create_engine(url)
    try:
        with Session(source_engine) as source:
            sources = list(source.scalars(select(ManiSource)))
            chunks = list(source.scalars(select(ManiChunk)))
            for row in sources:
                db.add(ManiSource(**{c.name: getattr(row, c.name) for c in ManiSource.__table__.columns}))
            db.flush()
            for row in chunks:
                db.add(ManiChunk(**{c.name: getattr(row, c.name) for c in ManiChunk.__table__.columns}))
            db.commit()
            return len(sources), len(chunks)
    finally:
        source_engine.dispose()


def describe_expected(question: Question, expected: dict[str, Expected]) -> str:
    if question.expected_key:
        return expected[question.expected_key].statement
    if question.needs_seed:
        return "(needs a seed addition; not scored)"
    checks = {k: v for k, v in question.params.items() if k != "forbid"}
    return f"[{question.check}] {checks}" if checks else f"[{question.check}]"


def list_questions(expected: dict[str, Expected], questions: Sequence[Question] = ACTIVE) -> str:
    lines = []
    for q in questions:
        lines.append(f"Q{q.id} [{q.area}, {q.type}] {q.prompt}")
        lines.append(f"    expected: {describe_expected(q, expected)}")
    return "\n".join(lines)


def _set_names(value: str) -> list[str]:
    names = [n.strip().upper() for n in value.split(",") if n.strip()]
    unknown = [n for n in names if n not in SETS]
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown set {', '.join(unknown)}; choose from {', '.join(SETS)}")
    return names


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, prog="python -m tests.mani_eval.runner")
    parser.add_argument("--list", action="store_true", help="print questions and expected answers")
    parser.add_argument("--agent", choices=sorted(AGENTS), help="run the question set")
    parser.add_argument("--out", type=Path, help="save the JSON report here")
    parser.add_argument("--set", dest="sets", metavar="NAMES", type=_set_names,
                        help="run only these parts of the question set, for example A1 or A1,B (A1 and A2 are "
                             "questions 1-10 and 11-20, B 21-30, C 31-40, D 41-50)")
    parser.add_argument("--only", metavar="IDS",
                        help="run only these question numbers, for example 9,11,36")
    parser.add_argument("--sources-from", metavar="DATABASE_URL",
                        help="copy the indexed sources from an ingested database (read only); search "
                             "then falls back to keywords, so use --sources-postgres for a real run")
    parser.add_argument("--sources-postgres", metavar="DATABASE_URL",
                        help="search the sources on this local, ingested PostgreSQL database (read "
                             "only), so vector search is used")
    parser.add_argument("--conversations", action="store_true",
                        help="run the scripted multi-turn conversations (conversations.py) instead of the "
                             "question set; --only then takes conversation numbers")
    args = parser.parse_args(argv)
    if not args.list and not args.agent:
        parser.error("give --list or --agent")
    with tempfile.TemporaryDirectory() as folder:
        engine = make_engine_at(Path(folder) / "mani-eval.sqlite3")
        try:
            with Session(engine) as db:
                dataset = build_dataset(db, FIXED_NOW)
                expected = compute_all(db, FIXED_NOW)
                if args.list:
                    print(dataset.describe())
                    print()
                    shown = tuple(q for n in args.sets for q in SETS[n]) if args.sets else ACTIVE
                    print(list_questions(expected, shown))
                    return 0
                if args.sources_from:
                    sources, chunks = copy_sources(args.sources_from, db)
                    print(f"Copied {sources} sources and {chunks} chunks.", file=sys.stderr, flush=True)
                try:
                    agent = AGENTS[args.agent](expected, FIXED_NOW)
                except NotImplementedError as error:
                    print(error, file=sys.stderr)
                    return 2
                if args.sources_postgres:
                    tracer = getattr(getattr(agent, "agent", None), "retriever", None)
                    if not isinstance(tracer, TracingRetriever):
                        parser.error("--sources-postgres works with --agent mani only")
                    try:
                        tracer.inner = PostgresSourceRetriever(
                            tracer.inner, open_source_database(args.sources_postgres))
                    except ValueError as error:
                        print(error, file=sys.stderr)
                        return 2
                    print("Searching the sources on PostgreSQL (read only).", file=sys.stderr, flush=True)
                if args.conversations:
                    from tests.mani_eval import conversations as convo

                    picked = convo.CONVERSATIONS
                    if args.only:
                        wanted = {int(n) for n in args.only.split(",")}
                        picked = tuple(c for c in picked if c.id in wanted)
                    result = convo.run_conversations(agent, db, conversations=picked, expected=expected,
                                                     dataset=dataset, progress=convo.stderr_progress)
                    print(result.to_text())
                    if args.out:
                        result.save(args.out)
                        print(f"\nSaved {args.out}")
                    return 0 if result.all_passed else 1
                chosen = tuple(q for name in args.sets for q in SETS[name]) if args.sets else ACTIVE
                if args.only:
                    wanted = {int(n) for n in args.only.split(",")}
                    chosen = tuple(q for q in chosen if q.id in wanted)
                report = run_questions(agent, db, questions=chosen, expected=expected, dataset=dataset)
                print(report.to_text())
                if args.out:
                    report.save(args.out)
                    print(f"\nSaved {args.out}")
                return 0 if report.factual_met else 1
        finally:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
