"""Checks that the scenario-data matrix (tests/scheduling/scenario_matrix.py) is complete
and points at things that exist. It does not run the scenarios; those are in
test_scenario_data.py and the other rules_v2 files."""
import ast
import re
from pathlib import Path

from tests.scheduling import scenario_matrix as m
from tests.scheduling import scenarios

API = Path(__file__).resolve().parents[3]          # services/api
REPO = API.parents[1]                              # repo root
REQS = REPO / "docs" / "reqs" / "scheduler-requirements.md"
TESTS = API / "tests"


def _doc_ids() -> set[str]:
    return set(re.findall(r"^\| (SCHR-[A-Z]+-\d+) \|", REQS.read_text(), re.M))


def _test_names() -> set[str]:
    names: set[str] = set()
    for path in TESTS.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                names.add(node.name)
    return names


def _covered_by_name(rule_id: str, names: set[str]) -> bool:
    slug = "test_" + rule_id.lower().replace("-", "_")
    return any(n == slug or n.startswith(slug + "_") for n in names)


def _covered() -> set[str]:
    names = _test_names()
    scenario_rows = {r for rules in m.SCENARIO_RULES.values() for r in rules}
    named = {r for r in _doc_ids() if _covered_by_name(r, names)}
    return scenario_rows | set(m.KNOWN_OPEN) | named


def test_every_schr_row_is_in_the_matrix_once_as_covered_or_not_planner():
    doc = _doc_ids()
    assert len(doc) == 133
    covered = _covered()
    overlap = covered & set(m.NOT_PLANNER)
    assert not overlap, f"a row is both covered and not planner: {sorted(overlap)}"
    unknown = (covered | set(m.NOT_PLANNER)) - doc
    assert not unknown, f"the matrix names rows that are not in the requirements: {sorted(unknown)}"


def test_uncovered_planner_rows_are_exactly_the_known_gaps():
    doc = _doc_ids()
    uncovered = doc - _covered() - set(m.NOT_PLANNER)
    assert uncovered == set(m.KNOWN_GAPS), (
        f"uncovered planner rows {sorted(uncovered)} differ from KNOWN_GAPS "
        f"{sorted(m.KNOWN_GAPS)}; add a scenario or a test, or record the gap")


def test_every_scenario_in_the_matrix_is_built_by_scenarios_py():
    built = {name for name, value in vars(scenarios).items()
             if callable(value) and getattr(value, "__module__", "") == scenarios.__name__}
    missing = set(m.SCENARIO_RULES) - built
    assert not missing, f"scenarios named in the matrix but not in scenarios.py: {sorted(missing)}"


def test_every_scenario_has_a_checking_test():
    text = (TESTS / "scheduling" / "rules_v2" / "test_scenario_data.py").read_text()
    for name in m.SCENARIO_RULES:
        assert f"s.{name}(" in text, f"no test in test_scenario_data.py builds {name}"


def test_known_open_rules_have_a_strict_expected_failure_test():
    names = _test_names()
    text = (TESTS / "scheduling" / "rules_v2" / "test_scenario_data.py").read_text()
    for rule_id, test_name in m.KNOWN_OPEN.items():
        assert test_name in names, f"{rule_id}: {test_name} does not exist"
        assert "xfail(strict=True" in text, f"{rule_id}: the expected failure must be strict"
