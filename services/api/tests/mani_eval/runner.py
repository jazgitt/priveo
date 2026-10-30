"""Runs the question set through any object that satisfies the `Agent` protocol
(`app.mani.contracts`) against the built dataset, and scores the events.

    python -m tests.mani_eval.runner --list
    python -m tests.mani_eval.runner --agent reference --out /tmp/mani-eval.json

Run it from `services/api`. The real agent arrives in Wave 2; `--agent mani` says so."""
import argparse
import sys
import tempfile
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.models import Login
from app.mani.contracts import Agent
from tests.mani_eval.dataset import FIXED_NOW, DatasetReport, build_dataset, make_engine_at
from tests.mani_eval.expected import Expected, compute_all
from tests.mani_eval.questions import QUESTIONS, Question
from tests.mani_eval.reference import ReferenceAgent
from tests.mani_eval.scoring import Outcome, Report, Score, read_events, score_question

AgentFactory = Callable[[dict[str, Expected], datetime], Agent]


def load_real_agent(expected: dict[str, Expected], now: datetime) -> Agent:
    """The hook for the real agent. Wave 2 wires `app.mani` in here."""
    raise NotImplementedError(
        "The real Mani agent is not implemented yet: it arrives in Wave 2. Run with "
        "--agent reference to check the harness, or call run_questions() with your own agent.")


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
    try:
        for text in question.setup:
            list(agent.run_turn(db, conversation_id=conversation_id, login_id=login_id,
                                user_text=text))
        outcome = read_events(agent.run_turn(
            db, conversation_id=conversation_id, login_id=login_id, user_text=question.prompt))
    except Exception as error:  # a crashing agent is a failed answer, not a crashed run
        outcome.errors.append(f"{type(error).__name__}: {error}")
    return score_question(question, outcome, expected, dataset)


def run_questions(agent: Agent, db: Session, *, now: datetime = FIXED_NOW,
                  questions: Sequence[Question] = QUESTIONS,
                  expected: dict[str, Expected] | None = None,
                  dataset: DatasetReport | None = None) -> Report:
    """Score `agent` on `questions`. The database must already hold the dataset."""
    expected = expected or compute_all(db, now)
    login_id = db.scalar(select(Login.id).where(Login.login_id == "priveopapa"))
    scores = [run_question(agent, db, q, login_id=login_id, expected=expected, dataset=dataset)
              for q in questions]
    return Report(scores)


def describe_expected(question: Question, expected: dict[str, Expected]) -> str:
    if question.expected_key:
        return expected[question.expected_key].statement
    if question.needs_seed:
        return "(needs a seed addition; not scored)"
    checks = {k: v for k, v in question.params.items() if k != "forbid"}
    return f"[{question.check}] {checks}" if checks else f"[{question.check}]"


def list_questions(expected: dict[str, Expected]) -> str:
    lines = []
    for q in QUESTIONS:
        lines.append(f"Q{q.id} [{q.area}, {q.type}] {q.prompt}")
        lines.append(f"    expected: {describe_expected(q, expected)}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, prog="python -m tests.mani_eval.runner")
    parser.add_argument("--list", action="store_true", help="print questions and expected answers")
    parser.add_argument("--agent", choices=sorted(AGENTS), help="run the question set")
    parser.add_argument("--out", type=Path, help="save the JSON report here")
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
                    print(list_questions(expected))
                    return 0
                try:
                    agent = AGENTS[args.agent](expected, FIXED_NOW)
                except NotImplementedError as error:
                    print(error, file=sys.stderr)
                    return 2
                report = run_questions(agent, db, expected=expected, dataset=dataset)
                print(report.to_text())
                if args.out:
                    report.save(args.out)
                    print(f"\nSaved {args.out}")
                return 0 if report.factual_met else 1
        finally:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
