"""Stage 10 helpers: macOS notification, GitHub issue, comments on merged pull requests."""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib import RunLog


def mac_notification(log: RunLog, title: str, text: str) -> None:
    safe = lambda s: s.replace("\\", " ").replace('"', "'")[:200]  # noqa: E731
    script = f'display notification "{safe(text)}" with title "{safe(title)}"'
    log.run("macOS notification", ["osascript", "-e", script], timeout=20)


def github_issue(log: RunLog, repo: str, title: str, body_file: Path) -> str | None:
    res = log.run("gh issue create", ["gh", "issue", "create", "--title", title, "--body-file", str(body_file)],
                  cwd=repo, timeout=60)
    return res.text().strip().splitlines()[-1] if res.ok and res.text().strip() else None


def comment_on_pr(log: RunLog, repo: str, number: int, body_file: Path) -> bool:
    return log.run(f"comment on #{number}", ["gh", "pr", "comment", str(number), "--body-file", str(body_file)],
                   cwd=repo, timeout=60).ok


def label_needs_human(log: RunLog, repo: str, number: int, reason: str, body_file: Path) -> None:
    """Comment why a pull request was dropped and add needs-human. Never closes or edits it."""
    body_file.write_text(f"The nightly run did not take this pull request tonight: {reason}.\n\n"
                         "Fix the cause and remove the `needs-human` label. The next night can then take it "
                         "if it still has the `nightly` label.\n")
    comment_on_pr(log, repo, number, body_file)
    log.run(f"label #{number}", ["gh", "pr", "edit", str(number), "--add-label", "needs-human"], cwd=repo, timeout=60)
