import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import fixloop  # noqa: E402
import lib  # noqa: E402
import nightly  # noqa: E402


class Lock(unittest.TestCase):
    def test_second_run_is_refused_while_first_is_alive(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            self.assertIsNone(nightly.acquire_lock(home))
            self.assertIn("in progress", nightly.acquire_lock(home))
            nightly.release_lock(home)
            self.assertIsNone(nightly.acquire_lock(home))

    def test_lock_of_a_dead_process_is_cleared(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            (home / "nightly.lock").write_text("999999 1\n")
            self.assertIsNone(nightly.acquire_lock(home))

    def test_stale_lock_of_a_live_process_is_reported_not_removed(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            (home / "nightly.lock").write_text(f"{os.getpid()} 1\n")
            self.assertIn("6 hours", nightly.acquire_lock(home, now=1 + 7 * 3600))
            self.assertTrue((home / "nightly.lock").exists())

    def test_garbled_lock_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            (home / "nightly.lock").write_text("junk")
            self.assertIn("unreadable", nightly.acquire_lock(home))


class RecentDeploy(unittest.TestCase):
    def test_wait_until_two_hours_old(self):
        from datetime import datetime, timedelta, timezone
        now = datetime(2026, 11, 5, 2, 0, tzinfo=timezone.utc)
        runs = [{"createdAt": (now - timedelta(minutes=84)).strftime("%Y-%m-%dT%H:%M:%SZ"), "url": "u1"},
                {"createdAt": (now - timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%SZ"), "url": "u2"}]
        wait, url = nightly.recent_deploy_wait(runs, now)
        self.assertEqual((int(wait // 60), url), (36, "u1"))
        self.assertEqual(nightly.recent_deploy_wait(runs[1:], now)[0], 0)
        self.assertEqual(nightly.recent_deploy_wait([], now), (0.0, ""))


class KillSwitch(unittest.TestCase):
    def test_kill_file_and_enabled_flag(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            self.assertIn("NIGHTLY_ENABLED", lib.kill_reason(home, {}))
            (home / "nightly.env").write_text("NIGHTLY_ENABLED=true\n")
            self.assertIsNone(lib.kill_reason(home, {}))
            self.assertIn("not true", lib.kill_reason(home, {"NIGHTLY_ENABLED": "false"}))
            (home / "KILL").write_text("")
            self.assertIn("KILL", lib.kill_reason(home, {"NIGHTLY_ENABLED": "true"}))

    def test_dry_run_ignores_enabled_flag_but_not_kill_file(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            self.assertIsNone(lib.kill_reason(home, {}, ignore_enabled=True))
            (home / "KILL").write_text("")
            self.assertIn("KILL", lib.kill_reason(home, {}, ignore_enabled=True))


class RunLogTrace(unittest.TestCase):
    def test_commands_and_stages_leave_a_trace(self):
        with tempfile.TemporaryDirectory() as d:
            log = lib.RunLog(Path(d), dry_run=True)
            with log.stage(0, "Preflight"):
                res = log.run("say hi", ["echo", "hi"])
                bad = log.run("fail", ["sh", "-c", "echo oops; exit 3"])
            self.assertTrue(res.ok)
            self.assertEqual(bad.rc, 3)
            events = [json.loads(line) for line in (log.dir / "events.jsonl").read_text().splitlines()]
            cmds = [e for e in events if e["event"] == "command"]
            self.assertEqual([c["exit"] for c in cmds], [0, 3])
            self.assertTrue(all(c["started"] and c["ended"] for c in cmds))
            self.assertIn("oops", (log.dir / cmds[1]["output"]).read_text())
            self.assertEqual(log.manifest["stages"][0]["status"], "passed")
            self.assertTrue((log.dir / "manifest.json").exists())
            self.assertIn("dryrun", log.dir.name)

    def test_a_sleeping_mac_is_noticed(self):
        import types
        wall, mono = iter([100.0, 1100.0]), iter([5.0, 6.0])
        fake = types.SimpleNamespace(time=lambda: next(wall), monotonic=lambda: next(mono), sleep=lambda s: None)
        with tempfile.TemporaryDirectory() as d:
            log = lib.RunLog(Path(d), dry_run=True)
            real, lib.time = lib.time, fake
            try:
                log.run("long", ["true"])
            finally:
                lib.time = real
            events = [json.loads(line) for line in (log.dir / "events.jsonl").read_text().splitlines()]
            cmd = [e for e in events if e["event"] == "command"][0]
            self.assertEqual(cmd["slept_seconds"], 999.0)
            self.assertTrue(any("slept" in n for n in log.manifest["notes"]))
            lib.RunLog(Path(d), dry_run=True).run("quick", ["true"])  # no sleep, no note

    def test_failed_stage_is_recorded_and_reraised(self):
        with tempfile.TemporaryDirectory() as d:
            log = lib.RunLog(Path(d), dry_run=False)
            with self.assertRaises(lib.StageFailed):
                with log.stage(3, "Local checks"):
                    raise lib.StageFailed("web failed")
            self.assertEqual(log.manifest["stages"][0]["status"], "failed")
            self.assertEqual(log.manifest["stages"][0]["detail"], "web failed")

    def test_second_real_run_same_day_gets_new_folder(self):
        with tempfile.TemporaryDirectory() as d:
            a = lib.RunLog(Path(d), dry_run=False)
            b = lib.RunLog(Path(d), dry_run=False)
            self.assertNotEqual(a.dir, b.dir)


class FixLoopPieces(unittest.TestCase):
    ROWS = [
        {"result": "PASS", "stage": "api: ruff, pytest (SQLite), contract", "seconds": 1},
        {"result": "FAIL", "stage": "api: pytest on PostgreSQL (disposable local cluster)", "seconds": 1},
        {"result": "FAIL", "stage": "mobile: generated files, analyze, test", "seconds": 1},
        {"result": "FAIL", "stage": "web: Playwright browser tests", "seconds": 1},
    ]

    def test_failed_keys(self):
        self.assertEqual(fixloop.failed_keys(self.ROWS), ["pg", "mobile", "e2e"])

    def test_fixers_are_mechanical_only(self):
        names = [n for n, _, _ in fixloop.fixers_for(["api", "mobile", "web"], "py")]
        self.assertEqual(names, ["ruff autofix", "export OpenAPI contract", "theme", "translations",
                                 "API client", "contract cases", "web lint autofix"])
        self.assertEqual(fixloop.fixers_for(["pg"], "py")[0][0], "ruff autofix")
        self.assertEqual(fixloop.fixers_for(["e2e"], "py"), [])


class NoProductionPath(unittest.TestCase):
    """The pipeline must have no way to reach production, its database or a release tag."""

    FORBIDDEN = [
        (r"\"tag\"|'tag'", "creating a tag"),
        (r"refs/tags|--tags|push.*\bv\d", "pushing a tag"),
        (r"\"workflow\"\s*,\s*\"run\"", "starting a workflow"),
        (r"\"release\"", "gh release"),
        (r"api-prod|priveo-api-prod", "the production project"),
        (r"-f\"?,?\s*\"?environment=|environment=production", "dispatching to an environment"),
        (r"MIGRATION_DATABASE_URL|DATABASE_URL|VERCEL_TOKEN", "a database or deploy credential"),
    ]

    def test_no_script_mentions_a_production_action(self):
        files = [p for p in HERE.iterdir() if p.suffix in (".py", ".sh")]
        self.assertGreater(len(files), 5)
        for path in files:
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                code = line.split("#", 1)[0]
                for pattern, what in self.FORBIDDEN:
                    if re.search(pattern, code):
                        self.fail(f"{path.name}:{lineno} mentions {what}: {line.strip()}")


if __name__ == "__main__":
    unittest.main()
