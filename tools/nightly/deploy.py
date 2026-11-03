"""Stage 7: wait for the test deploy of the merge commit and read its smoke test.

Only the test environment is looked at. The api-deploy workflow deploys a push to main to `test`.
This module never starts a workflow.
"""
from __future__ import annotations

import json
import time
import urllib.request

from lib import TEST_API_URL, RunLog, gh_json

FIND_TIMEOUT = 240
DEPLOY_TIMEOUT = 2400
POLL = 20


def smoke_step(run: dict) -> str:
    """Conclusion of the step named 'Smoke test' in a run's jobs, else 'not found'."""
    for job in run.get("jobs", []):
        for step in job.get("steps", []):
            if step.get("name") == "Smoke test":
                return step.get("conclusion") or step.get("status") or "unknown"
    return "not found"


def find_run(log: RunLog, repo: str, sha: str, wait: float = FIND_TIMEOUT, poll: float = POLL) -> dict | None:
    """The api-deploy run for a commit on main. None when the merge touched no deploy path."""
    start = time.time()
    while True:
        runs = gh_json(log, "gh run list api-deploy", [
            "gh", "run", "list", "--workflow", "api-deploy.yml", "--commit", sha, "--limit", "5",
            "--json", "databaseId,status,conclusion,url,event,number"], cwd=repo) or []
        runs = [r for r in runs if r.get("event") == "push"]
        if runs:
            return runs[0]
        if time.time() - start >= wait:
            return None
        time.sleep(poll)


def health(url: str = TEST_API_URL) -> dict:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/v1/public/health", timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001 - any failure is a failed health check
        return {"status": f"error: {type(e).__name__}"}


def wait_and_check(log: RunLog, repo: str, sha: str, label: str = "test deploy", find_wait: float = FIND_TIMEOUT,
                   timeout: float = DEPLOY_TIMEOUT, poll: float = POLL) -> dict:
    """Returns the deploy record: {ok, run_url, conclusion, smoke, health}. ok False means rollback."""
    rec = {"label": label, "commit": sha, "ok": False, "run_url": None, "conclusion": None,
           "smoke": "n/a", "health": "n/a"}
    run = find_run(log, repo, sha, find_wait, poll)
    if run is None:
        rec.update(ok=True, conclusion="no deploy triggered",
                   smoke="n/a (no API or portal path changed)")
        log.note(f"{label}: no api-deploy run started for {sha[:9]}; nothing was deployed")
        return rec
    rec["run_url"] = run["url"]
    start = time.time()
    detail: dict = {}
    while True:
        detail = gh_json(log, "gh run view api-deploy", [
            "gh", "run", "view", str(run["databaseId"]), "--json", "status,conclusion,url,number,jobs"], cwd=repo) or {}
        if detail.get("status") == "completed" or time.time() - start > timeout:
            break
        time.sleep(poll)
    rec["conclusion"] = detail.get("conclusion") or "timed out"
    rec["smoke"] = smoke_step(detail)
    h = health()
    rec["health"] = f"{h.get('status')} build {h.get('build_number')}"
    run_number = str(detail.get("number", ""))
    rec["build_matches_run"] = str(h.get("build_number")) == run_number
    rec["ok"] = rec["conclusion"] == "success" and rec["smoke"] == "success" and h.get("status") == "ok"
    return rec
