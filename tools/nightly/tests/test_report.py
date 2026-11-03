import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import report  # noqa: E402

SUMMARY = """[01:00:00] ---- web ----

Summary:
  PASS  api: ruff, pytest (SQLite), contract  (95s)
  PASS  api: pytest on PostgreSQL (disposable local cluster)  (310s)
  FAIL  web: Playwright browser tests  (41s)
"""


class Report(unittest.TestCase):
    def test_parse_check_summary(self):
        rows = report.parse_check_summary(SUMMARY)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1]["stage"], "api: pytest on PostgreSQL (disposable local cluster)")
        self.assertEqual(rows[2]["result"], "FAIL")

    def manifest(self, **kw):
        m = {"mode": "real", "started": "2026-11-05T02:00:00+05:30", "finished": "2026-11-05T02:40:00+05:30",
             "result": "ok", "stages": [], "selected": [], "dropped": [], "merged_prs": [], "local_checks": [],
             "fix_attempts": [], "ci_checks": [], "merge_commit": None, "nightly_pr": None, "deploy": None,
             "rollback": None, "notes": [], "production": "untouched (manual)"}
        m.update(kw)
        return m

    def test_failed_result_names_the_stage(self):
        m = self.manifest(result="failed", stages=[
            {"num": 3, "name": "Local checks", "status": "failed", "detail": "web failed", "started": "2026-11-05T02:01:00",
             "ended": "2026-11-05T02:05:00", "seconds": 240}])
        self.assertIn("Stopped at stage 3", report.build(m, Path("/x")))

    def test_evidence_sections_present(self):
        m = self.manifest(
            selected=[{"number": 7, "title": "T", "head": "abcdef123456", "url": "u"}],
            merged_prs=[{"number": 7}],
            local_checks=[{"label": "combined", "command": "check-local.sh --e2e", "exit": 0,
                           "stages": report.parse_check_summary(SUMMARY)}],
            ci_checks=[{"name": "ci-gate", "state": "SUCCESS", "link": "https://x/run/1"}],
            merge_commit="deadbeef",
            deploy={"run_url": "https://x/run/2", "conclusion": "success", "smoke": "success", "health": "ok build 5"})
        text = report.build(m, Path("/x/logs/d"))
        for needle in ("abcdef123", "PostgreSQL", "Playwright", "https://x/run/1", "https://x/run/2",
                       "Smoke test step: success", "untouched (manual)", "deadbeef"):
            self.assertIn(needle, text)

    def test_home_is_shortened(self):
        text = report.build(self.manifest(), Path.home() / "priveo-nightly/logs/d")
        self.assertNotIn(str(Path.home()), text)


if __name__ == "__main__":
    unittest.main()
