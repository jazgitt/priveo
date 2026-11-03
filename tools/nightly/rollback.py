#!/usr/bin/env python3
"""Roll the TEST environment back by reverting a merge commit on main.

    rollback.py --merge-sha SHA [--repo-dir DIR] [--logs-root DIR] [--dry-run]

Pushing the revert to main makes api-deploy deploy test again, which is the rollback. This is also
the drill: run it on a harmless merge to prove the path on test. Production is not touched: this
script acts on `main`, which only ever deploys to test, and never starts a workflow or pushes a tag.
A database migration in the reverted merge is NOT undone (see docs/nightly-pipeline.md, section 8.5).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy  # noqa: E402
from lib import DEFAULT_HOME, RunLog  # noqa: E402

IDENT = ["-c", "user.name=Priveo Nightly", "-c", "user.email=nightly@priveo.invalid"]


def revert_merge(log: RunLog, repo: str, merge_sha: str, push: bool = True) -> str | None:
    """Revert the merge commit on a fresh main and push it. Returns the revert commit or None."""
    log.run("fetch main", ["git", "fetch", "-q", "origin", "main"], cwd=repo)
    log.run("checkout main", ["git", "checkout", "-q", "-B", "nightly-rollback", "origin/main"], cwd=repo)
    parents = log.run("count parents", ["git", "rev-list", "--parents", "-n", "1", merge_sha], cwd=repo).text().split()
    args = ["-m", "1"] if len(parents) > 2 else []
    res = log.run("revert merge", ["git", *IDENT, "revert", "--no-edit", *args, merge_sha], cwd=repo)
    if not res.ok:
        log.run("revert abort", ["git", "revert", "--abort"], cwd=repo)
        return None
    sha = log.run("revert sha", ["git", "rev-parse", "HEAD"], cwd=repo).text().strip()
    if push:
        pushed = log.run("push revert to main", ["git", "push", "origin", "HEAD:refs/heads/main"], cwd=repo, timeout=300)
        if not pushed.ok:
            return None
    return sha


def rollback(log: RunLog, repo: str, merge_sha: str, push: bool = True) -> dict:
    rec = {"merge": merge_sha, "revert": None, "deploy": None, "ok": False}
    rec["revert"] = revert_merge(log, repo, merge_sha, push)
    if rec["revert"] and push:
        rec["deploy"] = deploy.wait_and_check(log, repo, rec["revert"], label="rollback deploy")
        rec["ok"] = rec["deploy"]["ok"]
    elif rec["revert"]:
        rec["ok"] = True  # dry: the revert applied cleanly, nothing was pushed
    log.manifest["rollback"] = rec
    log.save()
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--merge-sha", required=True)
    ap.add_argument("--repo-dir", default=str(DEFAULT_HOME))
    ap.add_argument("--logs-root", default=str(DEFAULT_HOME / "logs"))
    ap.add_argument("--dry-run", action="store_true", help="revert locally, push nothing")
    args = ap.parse_args()
    log = RunLog(Path(args.logs_root), dry_run=args.dry_run)
    rec = rollback(log, args.repo_dir, args.merge_sha, push=not args.dry_run)
    log.manifest["result"] = "rollback-ok" if rec["ok"] else "rollback-failed"
    log.save()
    print(log.manifest["rollback"])
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
