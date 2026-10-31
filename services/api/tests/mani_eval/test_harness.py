"""The harness itself: a right agent scores 100%, and the scorers catch the wrong answers."""
import json
import re
from dataclasses import replace

import pytest

from app.mani.contracts import TurnEvent
from tests.mani_eval import runner
from tests.mani_eval.dataset import FIXED_NOW, FIXTURE_ADMIN_PASSWORD
from tests.mani_eval.expected import Num
from tests.mani_eval.questions import QUESTIONS, WRITE_TOOL, migration_head
from tests.mani_eval.reference import REVIEW_FILES, ReferenceAgent
from tests.mani_eval.scoring import Outcome, extract_numbers, number_present

BY_ID = {q.id: q for q in QUESTIONS}


class Mutated:
    """The reference agent with its final events changed by `change(question, events)`."""

    def __init__(self, expected, change):
        self.inner = ReferenceAgent(expected, FIXED_NOW)
        self.change = change

    def prepare(self, question):
        self.inner.prepare(question)

    def run_turn(self, db, *, conversation_id, login_id, user_text):
        events = list(self.inner.run_turn(db, conversation_id=conversation_id, login_id=login_id,
                                          user_text=user_text))
        return iter(self.change(self.inner.question, events))


def run(world, agent, ids):
    questions = [BY_ID[i] for i in ids]
    return runner.run_questions(agent, world["db"], expected=world["expected"],
                                dataset=world["dataset"], questions=questions)


def with_answer(events, content, *, keep_citations=True):
    out = []
    for e in events:
        if e.kind == "answer":
            data = dict(e.data, content=content)
            if not keep_citations:
                data["citations"] = []
            e = TurnEvent("answer", data)
        out.append(e)
    return out


def append_answer(events, extra):
    answer = next(e for e in events if e.kind == "answer")
    return with_answer(events, answer.data["content"] + " " + extra)


def failed_names(report, qid):
    return {c.name for s in report.scores if s.question_id == qid for c in s.failed_checks}


# ---- The question set --------------------------------------------------------------------------


def test_golden_set_is_fifty_questions_in_four_groups():
    assert [q.id for q in QUESTIONS] == list(range(1, 51))
    groups = {"code": range(1, 21), "architecture": range(21, 31), "business": range(31, 41),
              "run": range(41, 51)}
    for q in QUESTIONS:
        assert q.id in groups[q.type], q.id
        assert q.check == "phrases" and q.needs_citation and q.gold, q.id
        assert q.params["phrases_all"], q.id


def test_question_text_matches_the_review_file():
    rows = {}
    for line in "\n".join(f.read_text(encoding="utf-8") for f in REVIEW_FILES).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells[0].isdigit():
            rows[int(cells[0])] = cells[1]
    assert sorted(rows) == list(range(1, 51))
    for q in QUESTIONS:
        assert rows[q.id] == q.text, q.id


# ---- A right agent -----------------------------------------------------------------------------


def test_reference_agent_scores_full_marks(eval_world):
    report = runner.run_questions(ReferenceAgent(eval_world["expected"], FIXED_NOW),
                                  eval_world["db"], expected=eval_world["expected"],
                                  dataset=eval_world["dataset"])
    assert report.failures == [], report.to_text()
    assert report.overall_percent == report.factual_percent == 100.0
    assert report.factual_met and report.skipped == [] and len(report.scored) == 47


def test_report_text_and_json(eval_world, tmp_path):
    report = runner.run_questions(ReferenceAgent(eval_world["expected"], FIXED_NOW),
                                  eval_world["db"], expected=eval_world["expected"],
                                  dataset=eval_world["dataset"])
    text = report.to_text()
    assert "Factual correctness" in text and "By area:" in text
    assert "Code implementation: 17/17" in text and "How to run Priveo: 10/10" in text
    out = tmp_path / "nested" / "report.json"
    report.save(out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["factual_target_met"] is True and data["scored"] == 47
    assert set(data["by_area"]) == {"Code implementation", "Tech stack and architecture",
                                    "Business requirements", "How to run Priveo"}


# ---- Wrong agents are caught ---------------------------------------------------------------


def test_a_wrong_answer_is_caught(eval_world):
    agent = Mutated(eval_world["expected"], lambda q, ev: with_answer(
        ev, "It uses a plain keyword score and no fixed constants."))
    report = run(eval_world, agent, [1, 31, 41])
    assert [s.passed for s in report.scores] == [False, False, False]
    assert report.factual_percent == 0.0 and not report.factual_met


def test_one_missing_fact_fails_the_question(eval_world):
    # Q8 needs both the 5 attempts and the 15 minutes.
    agent = Mutated(eval_world["expected"], lambda q, ev: with_answer(
        ev, "The customer is blocked after 5 wrong passwords."))
    report = run(eval_world, agent, [8])
    assert not report.scores[0].passed
    assert any(n.startswith("mentions:") for n in failed_names(report, 8))


def test_leaks_are_caught(eval_world):
    dataset = eval_world["dataset"]
    leaks = {
        1: f"Call the customer on {dataset.customer_mobiles[0]}.",
        22: f"Email {dataset.customer_emails[0]} for details.",
        33: f"The admin password is {FIXTURE_ADMIN_PASSWORD}.",
        5: "Use token eyJhbGciOiJIUzI1NiJ9abcdef to sign in.",
        26: "Ring +91 98765 43210 now.".replace(" ", ""),
    }
    agent = Mutated(eval_world["expected"], lambda q, ev: append_answer(ev, leaks[q.id]))
    report = run(eval_world, agent, list(leaks))
    for qid in leaks:
        assert "no_leak" in failed_names(report, qid), qid
    # The answers were otherwise right: only the leak fails them.
    assert failed_names(report, 1) == {"no_leak"}


def test_missing_citation_is_caught(eval_world):
    agent = Mutated(eval_world["expected"], lambda q, ev: with_answer(
        ev, next(e for e in ev if e.kind == "answer").data["content"], keep_citations=False))
    report = run(eval_world, agent, [1, 9, 34, 22])
    assert all("citation_present" in failed_names(report, s.question_id) for s in report.scores)


def test_write_tool_call_is_caught(eval_world):
    def change(question, events):
        call = TurnEvent("tool_call", {"name": "update_payment_status", "arguments": {}})
        return [events[0], call, *events[1:]]

    report = run(eval_world, Mutated(eval_world["expected"], change), [34, 1])
    assert "no_write_tool" in failed_names(report, 34)
    assert "no_write_tool" in failed_names(report, 1)


def test_read_tools_that_start_like_a_write_verb_are_not_flagged():
    for name in ("payments_summary", "addons_summary", "setup_report", "payroll_summary"):
        assert not re.match(WRITE_TOOL, name, re.I), name
    for name in ("pay", "add_addon", "update_payment_status", "send_message", "set_price"):
        assert re.match(WRITE_TOOL, name, re.I), name


def test_agent_that_crashes_fails_the_question(eval_world):
    class Crashing:
        def run_turn(self, db, **kwargs):
            raise RuntimeError("model unreachable")

    report = run(eval_world, Crashing(), [1])
    assert not report.scores[0].passed and "no_error" in failed_names(report, 1)


# ---- Scorer details ------------------------------------------------------------------------


def test_number_extraction_forms():
    assert 150000.0 in extract_numbers("Rs 1,50,000 received")
    assert 12.0 in extract_numbers("बारह नहीं, १२ जॉब")
    assert 57.9 in extract_numbers("11 of 19 jobs") or 57.9 in extract_numbers("11 out of 19")
    assert 3.0 in extract_numbers("three crew")
    assert number_present("No jobs were missed.", Num("missed", 0))
    assert not number_present("5 jobs were missed.", Num("missed", 0))
    assert number_present("It is 4.04 out of 5", Num("average", 4.0, 0.05))
    assert not number_present("It is 4.2 out of 5", Num("average", 4.0, 0.05))


def test_migration_head_is_read_from_the_repo():
    number, name = migration_head()
    assert re.fullmatch(r"\d{4}", number) and name
    assert number >= "0042"


def test_real_agent_hook_builds_the_real_agent_without_calling_a_model(eval_world):
    agent = runner.AGENTS["mani"](eval_world["expected"], FIXED_NOW)  # building makes no network call
    assert isinstance(agent, runner.EvalMani) and callable(agent.prepare)
    assert type(agent.agent).__name__ == "ManiAgent"


def test_list_prints_questions_and_expected(capsys):
    assert runner.main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "Q1 [Code implementation, code]" in out and "RRF" in out
    assert "Q50 [How to run Priveo, run]" in out


@pytest.mark.parametrize("field", ["setup", "params"])
def test_question_is_immutable_record(field):
    with pytest.raises(AttributeError):
        setattr(QUESTIONS[0], field, ())
    assert replace(QUESTIONS[0], id=99).id == 99
    assert Outcome().answer == ""


def test_the_five_sets_split_the_fifty_questions_without_overlap():
    from tests.mani_eval.questions import SETS
    DROPPED = {7, 12, 20}  # marked Drop in the review files
    ranges = {"A1": (1, 10), "A2": (11, 20), "B": (21, 30), "C": (31, 40), "D": (41, 50)}
    assert list(SETS) == list(ranges)
    for name, (first, last) in ranges.items():
        assert [q.id for q in SETS[name]] == [i for i in range(first, last + 1) if i not in DROPPED]
    assert [q.id for q in QUESTIONS] == list(range(1, 51))
