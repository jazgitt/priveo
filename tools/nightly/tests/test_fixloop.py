import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import fixloop  # noqa: E402
import nightly  # noqa: E402
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
        self.orig = (fixloop.run_checks, fixloop.fixers_for, fixloop.FLAKE_PAUSE)
        g(self.fx.clone, "config", "user.name", "T")
        g(self.fx.clone, "config", "user.email", "t@t.invalid")

    def tearDown(self):
        fixloop.run_checks, fixloop.fixers_for, fixloop.FLAKE_PAUSE = self.orig
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

    # ---- flake retry -------------------------------------------------------------

    PG_FAIL = [{"result": "PASS", "stage": "api: ruff, pytest (SQLite), contract", "seconds": 1},
               {"result": "FAIL", "stage": "api: pytest on PostgreSQL", "seconds": 5},
               {"result": "FAIL", "stage": "web: Playwright browser tests", "seconds": 5}]

    def test_flake_retry_reruns_only_the_failed_stages_and_records_both(self):
        calls = self.script_checks([(True, PASS_ROWS), (True, PASS_ROWS)])
        pauses = []
        ok = fixloop.flake_retry(self.log, self.repo, self.PG_FAIL, 7, sleep=pauses.append)
        self.assertTrue(ok)
        self.assertEqual(calls, [["--only", "pg"], ["--only", "e2e"]])
        self.assertEqual(pauses, [7])
        rec = self.log.manifest["flake_retries"][0]
        self.assertEqual(rec["second"], "passed")
        self.assertEqual(rec["stages"], ["api: pytest on PostgreSQL", "web: Playwright browser tests"])
        events = [e["event"] for e in map(__import__("json").loads, (self.log.dir / "events.jsonl").read_text().splitlines())]
        self.assertIn("flake_retry_start", events)
        self.assertIn("flake_retry_end", events)

    def test_flake_retry_fails_when_one_stage_fails_again(self):
        self.script_checks([(True, PASS_ROWS), (False, FAIL_ROWS)])
        self.assertFalse(fixloop.flake_retry(self.log, self.repo, self.PG_FAIL, 0, sleep=lambda s: None))
        self.assertEqual(self.log.manifest["flake_retries"][0]["second"], "failed: e2e")

    def test_flake_retry_refused_for_a_failure_that_is_not_a_stage(self):
        calls = self.script_checks([])
        rows = [{"result": "FAIL", "stage": "something else", "seconds": 1}]
        self.assertFalse(fixloop.flake_retry(self.log, self.repo, rows, 0, sleep=lambda s: None))
        self.assertEqual(calls, [])
        self.assertEqual(self.log.manifest["flake_retries"], [])

    def test_single_pr_gets_the_retry_before_the_fix_loop(self):
        fixloop.fixers_for = lambda keys, py: self.fail("the fix loop must not run when the retry passes")
        calls = self.script_checks([(False, self.PG_FAIL), (True, PASS_ROWS), (True, PASS_ROWS)])
        self.assertTrue(fixloop.local_checks(self.log, self.repo, "py", single=True, pause=0))
        self.assertEqual(calls, [["--e2e"], ["--only", "pg"], ["--only", "e2e"]])
        self.assertEqual(self.log.manifest["fix_attempts"], [])

    def test_no_retry_when_not_single(self):
        fixloop.fixers_for = lambda keys, py: [("noop", ["true"], ".")]
        calls = self.script_checks([(False, FAIL_ROWS)])
        self.assertFalse(fixloop.local_checks(self.log, self.repo, "py", single=False))
        self.assertEqual(calls, [["--e2e"]])
        self.assertEqual(self.log.manifest["flake_retries"], [])

    def test_single_pr_failing_twice_behaves_as_before(self):
        fixloop.fixers_for = lambda keys, py: [("noop", ["true"], ".")]
        calls = self.script_checks([(False, FAIL_ROWS), (False, FAIL_ROWS)])
        self.assertFalse(fixloop.local_checks(self.log, self.repo, "py", single=True, pause=0))
        self.assertEqual(calls, [["--e2e"], ["--only", "api"]])
        self.assertEqual(self.log.manifest["flake_retries"][0]["second"], "failed: api")
        self.assertEqual(self.log.manifest["fix_attempts"][0]["outcome"], "no change; stopped")

    # ---- the stage: several pull requests ------------------------------------------

    def stage_fixture(self, retry_ok):
        """Two PRs that each pass alone; the combined run fails on PostgreSQL. Returns (built, selection, calls)."""
        h1 = self.fx.pr(1, {"b.txt": "b\n"})
        h2 = self.fx.pr(2, {"c.txt": "c\n"})
        selection = sel((1, h1), (2, h2))
        built = {"merged": [{"number": 1, "title": "T1", "head": h1}, {"number": 2, "title": "T2", "head": h2}]}
        calls = []
        seq = [(False, self.PG_FAIL), (True, PASS_ROWS), (True, PASS_ROWS)]  # combined, solo 1, solo 2
        seq += [(retry_ok, PASS_ROWS if retry_ok else FAIL_ROWS)] * 2

        def fake(log, repo, label, args):
            calls.append((label, args))
            ok, rows = seq.pop(0)
            log.manifest["local_checks"].append({"label": label, "stages": rows})
            return ok, rows
        fixloop.run_checks = fake
        fixloop.fixers_for = lambda keys, py: [("noop", ["true"], ".")]
        fixloop.FLAKE_PAUSE = 0
        return built, selection, calls

    def run_stage(self, built, selection):
        args = type("A", (), {"dry_run": True})()
        return nightly.local_check_stage(self.log, self.repo, Path(self.tmp.name), "py", selection, built,
                                         "nightly/t", "d", args)

    def test_several_prs_that_pass_alone_get_a_retry_of_the_failed_stages(self):
        built, selection, calls = self.stage_fixture(retry_ok=True)
        out = self.run_stage(built, selection)
        self.assertEqual({p["number"] for p in out["merged"]}, {1, 2})
        self.assertEqual([c[1] for c in calls[-2:]], [["--only", "pg"], ["--only", "e2e"]])
        self.assertEqual(self.log.manifest["flake_retries"][0]["second"], "passed")

    def test_several_prs_that_pass_alone_and_fail_again_stop_the_night(self):
        built, selection, _ = self.stage_fixture(retry_ok=False)
        with self.assertRaises(lib.StageFailed):
            self.run_stage(built, selection)
        self.assertTrue(self.log.manifest["flake_retries"][0]["second"].startswith("failed"))


if __name__ == "__main__":
    unittest.main()
