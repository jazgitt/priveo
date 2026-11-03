import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import watchdog  # noqa: E402


def make(logs: Path, name: str, mode: str, started: datetime, report=True):
    d = logs / name
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"mode": mode, "started": started.isoformat()}))
    if report:
        (d / "report.md").write_text("x")


class Watchdog(unittest.TestCase):
    def test_finds_recent_real_run_only(self):
        now = datetime.now().astimezone()
        with tempfile.TemporaryDirectory() as t:
            logs = Path(t)
            self.assertIsNone(watchdog.last_real_run(logs, now))
            make(logs, "a-dry", "dry-run", now - timedelta(hours=1))
            make(logs, "b-old", "real", now - timedelta(hours=30))
            make(logs, "c-noreport", "real", now - timedelta(hours=2), report=False)
            self.assertIsNone(watchdog.last_real_run(logs, now))
            make(logs, "d-real", "real", now - timedelta(hours=5))
            self.assertEqual(watchdog.last_real_run(logs, now).name, "d-real")


if __name__ == "__main__":
    unittest.main()
