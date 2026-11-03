import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import fixloop  # noqa: E402
import lib  # noqa: E402
from test_build import Fixture, g, sel  # noqa: E402

FAIL_ROWS = [{"result": "FAIL", "stage": "api: ruff, pytest (SQLite), contract", "seconds": 1}]
PASS_ROWS = [{"result": "PASS", "stage": "api: ruff, pytest (SQLite), contract", "seconds": 1}]


class FixLoop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self.tmp.name))
        self.repo = str(self.fx.clone)
        self.log = lib.RunLog(Path(self.tmp.name) / "logs", dry_run=True)
        self.orig = (fixloop.run_checks, fixloop.fixers_for)
        g(self.fx.clone, "config", "user.name", "T")
        g(self.fx.clone, "config", "user.email", "t@t.invalid")

    def tearDown(self):
        fixloop.run_checks, fixloop.fixers_for = self.orig
        self.tmp.cleanup()

    def script_checks(self, results):
        """Replace run_checks with a scripted sequence of (ok, rows)."""
        calls = []
        seq = list(results)

        def fake(log, repo, label, args):
            calls.append(args)
            return seq.pop(0)
        fixloop.run_checks = fake
        return calls

    def test_green_first_time_needs_no_fix(self):
        calls = self.script_checks([(True, PASS_ROWS)])
        self.assertTrue(fixloop.local_checks(self.log, self.repo, "py"))
        self.assertEqual(calls, [["--e2e"]])
        self.assertEqual(self.log.manifest["fix_attempts"], [])

    def test_mechanical_fix_is_committed_and_rerun(self):
        fixloop.fixers_for = lambda keys, py: [("regen", ["sh", "-c", "echo gen > generated.txt"], ".")]
        calls = self.script_checks([(False, FAIL_ROWS), (True, PASS_ROWS)])
        self.assertTrue(fixloop.local_checks(self.log, self.repo, "py"))
        self.assertEqual(calls[1], ["--only", "api"])
        self.assertEqual(self.log.manifest["fix_attempts"][0]["outcome"], "fixed")
        self.assertIn("nightly: regenerate files", g(self.fx.clone, "log", "-1", "--format=%s"))

    def test_fix_that_changes_nothing_stops_the_loop(self):
        fixloop.fixers_for = lambda keys, py: [("noop", ["true"], ".")]
        self.script_checks([(False, FAIL_ROWS)])
        self.assertFalse(fixloop.local_checks(self.log, self.repo, "py"))
        self.assertEqual(len(self.log.manifest["fix_attempts"]), 1)

    def test_at_most_two_attempts(self):
        counter = {"n": 0}

        def fixers(keys, py):
            counter["n"] += 1
            return [("regen", ["sh", "-c", f"echo {counter['n']} > g.txt"], ".")]
        fixloop.fixers_for = fixers
        self.script_checks([(False, FAIL_ROWS)] * 3)
        self.assertFalse(fixloop.local_checks(self.log, self.repo, "py"))
        self.assertEqual(len(self.log.manifest["fix_attempts"]), 2)

    def test_bisect_finds_the_pr_that_fails_alone(self):
        h1 = self.fx.pr(1, {"b.txt": "b\n"})
        h2 = self.fx.pr(2, {"bad.txt": "x\n"})
        merged = [{"number": 1, "title": "T1", "head": h1}, {"number": 2, "title": "T2", "head": h2}]

        def fake(log, repo, label, args):
            bad = (Path(repo) / "bad.txt").exists()
            return (not bad, FAIL_ROWS if bad else PASS_ROWS)
        fixloop.run_checks = fake
        culprits = fixloop.bisect_and_drop(self.log, self.repo, sel((1, h1), (2, h2)), merged, "d")
        self.assertEqual([c["number"] for c in culprits], [2])


if __name__ == "__main__":
    unittest.main()
