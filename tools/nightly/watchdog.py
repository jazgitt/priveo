#!/usr/bin/env python3
"""Missed-night watchdog: started by launchd at 06:30. If no real run left a report in the last
24 hours, send a Mac notification and open a GitHub issue. Reads the evidence trace only."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import DEFAULT_HOME  # noqa: E402


def last_real_run(logs: Path, now: datetime, hours: int = 24) -> Path | None:
    """The newest real-mode run folder with a report that started within `hours`."""
    best = None
    if not logs.is_dir():
        return None
    for folder in sorted(logs.iterdir()):
        manifest = folder / "manifest.json"
        if not manifest.is_file() or not (folder / "report.md").is_file():
            continue
        try:
            m = json.loads(manifest.read_text())
            started = datetime.fromisoformat(m["started"])
        except (ValueError, KeyError):
            continue
        if m.get("mode") == "real" and now - started <= timedelta(hours=hours):
            best = folder
    return best


def main() -> int:
    home = DEFAULT_HOME
    now = datetime.now().astimezone()
    found = last_real_run(home / "logs", now)
    if found:
        print(f"ok: {found.name}")
        return 0
    text = "No nightly run left a report in the last 24 hours."
    subprocess.run(["osascript", "-e", f'display notification "{text}" with title "Priveo nightly missed"'])
    body = home / "logs" / "watchdog-issue.md"
    body.write_text(text + " Check that the Mac was on, `launchctl print gui/$(id -u)/in.priveo.nightly`, "
                    "and the files launchd-in.priveo.nightly.out and .err in the nightly logs folder.\n")
    subprocess.run(["gh", "issue", "create", "--title", f"Nightly missed {now:%Y-%m-%d}", "--body-file", str(body)],
                   cwd=home)
    return 1


if __name__ == "__main__":
    sys.exit(main())
