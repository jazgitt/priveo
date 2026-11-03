"""Stages 5 and 6: push the combined branch, wait for CI, merge it into main.

GitHub Actions is the final gate. The branch is merged only through a pull request, with a merge
commit, and only when the checks that started are green. No --admin flag, so branch protection
(when on) is honoured.
"""
from __future__ import annotations

import time
from pathlib import Path

from lib import RunLog, StageFailed, gh_json

POLL_SECONDS = 30
NO_CHECKS_GRACE = 300
CI_TIMEOUT = 3600


def evaluate_checks(checks: list[dict], waited: float, grace: float = NO_CHECKS_GRACE) -> str:
    """'pass' | 'fail' | 'pending' | 'none' from `gh pr checks --json bucket,name`.

    bucket is one of pass, fail, pending, skipping, cancel. No checks after the grace period means
    path filters started nothing (a tools-only or docs-only change): 'none', which is allowed.
    """
    if not checks:
        return "none" if waited >= grace else "pending"
    buckets = {c.get("bucket") for c in checks}
    if buckets & {"fail", "cancel"}:
        return "fail"
    if "pending" in buckets:
        return "pending"
    return "pass"


def push_branch(log: RunLog, repo: str, branch: str) -> None:
    res = log.run("push combined branch", ["git", "push", "origin", f"{branch}:refs/heads/{branch}"], cwd=repo, timeout=300)
    if not res.ok:
        raise StageFailed("could not push the combined branch (it may already exist on GitHub)")


def open_pr(log: RunLog, repo: str, branch: str, body_file: Path, title: str) -> int:
    res = log.run("gh pr create", ["gh", "pr", "create", "--base", "main", "--head", branch, "--title", title,
                                   "--body-file", str(body_file)], cwd=repo, timeout=120)
    if not res.ok:
        raise StageFailed("could not open the nightly pull request")
    url = res.text().strip().splitlines()[-1]
    log.manifest["nightly_pr"] = url
    return int(url.rstrip("/").split("/")[-1])


def wait_for_checks(log: RunLog, repo: str, number: int, timeout: int = CI_TIMEOUT,
                    poll: float = POLL_SECONDS, grace: float = NO_CHECKS_GRACE) -> str:
    start = time.time()
    checks: list[dict] = []
    verdict = "pending"
    while True:
        waited = time.time() - start
        got = gh_json(log, f"gh pr checks #{number}",
                      ["gh", "pr", "checks", str(number), "--json", "name,state,bucket,link,workflow"], cwd=repo)
        # `gh pr checks` exits non-zero while checks fail or are pending but still prints JSON; a
        # missing list means no checks yet.
        checks = got or []
        verdict = evaluate_checks(checks, waited, grace)
        log.event("ci_poll", pr=number, verdict=verdict, checks=[(c["name"], c["bucket"]) for c in checks])
        if verdict != "pending" or waited > timeout:
            break
        time.sleep(poll)
    log.manifest["ci_checks"] = [
        {"name": c["name"], "state": c["state"], "bucket": c["bucket"], "link": c.get("link", "")} for c in checks]
    log.save()
    if verdict == "pending":
        raise StageFailed(f"CI did not finish within {timeout // 60} minutes")
    if verdict == "fail":
        bad = ", ".join(c["name"] for c in checks if c["bucket"] in ("fail", "cancel"))
        raise StageFailed(f"CI failed: {bad}")
    if verdict == "none":
        log.note("no CI check started for the nightly pull request (path filters); nothing was required")
    return verdict


def merge_pr(log: RunLog, repo: str, number: int) -> str:
    """Merge with a merge commit, delete the branch, return the merge commit SHA."""
    res = log.run("gh pr merge", ["gh", "pr", "merge", str(number), "--merge", "--delete-branch"], cwd=repo, timeout=180)
    if not res.ok:
        raise StageFailed("the merge was refused: " + res.text().strip()[-300:])
    info = gh_json(log, "gh pr view merge commit", ["gh", "pr", "view", str(number), "--json", "mergeCommit,state"], cwd=repo)
    if not info or info.get("state") != "MERGED" or not info.get("mergeCommit"):
        raise StageFailed("the pull request is not shown as merged after the merge command")
    sha = info["mergeCommit"]["oid"]
    log.manifest["merge_commit"] = sha
    return sha


def settle_included_prs(log: RunLog, repo: str, merged: list[dict], nightly_pr: int, sha: str) -> None:
    """GitHub marks the included PRs merged because their heads are now in main. Make sure."""
    for pr in merged:
        info = gh_json(log, f"gh pr view #{pr['number']}", ["gh", "pr", "view", str(pr["number"]), "--json", "state"], cwd=repo)
        if info and info.get("state") == "OPEN":
            msg = f"Merged into main by the nightly run in #{nightly_pr} (merge commit {sha[:9]}). Closing."
            log.run(f"close #{pr['number']}", ["gh", "pr", "close", str(pr["number"]), "--comment", msg], cwd=repo)
