"""Stages 3 and 4: local checks, the mechanical fix loop, and bisect-and-drop.

Only mechanical fixes (lint autofix, regenerated files) are applied, at most MAX_ATTEMPTS times.
Nothing here edits tests or application logic. A failure that survives is traced by running each
pull request alone; the one that fails alone is dropped and the night goes on without it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_combined  # noqa: E402
import report  # noqa: E402
from lib import RunLog, StageFailed  # noqa: E402

MAX_ATTEMPTS = 2
CHECKS_TIMEOUT = 5400


def stage_key(stage_name: str) -> str | None:
    """Map a check-local.sh summary line to its --only key."""
    if stage_name.startswith("api: pytest on PostgreSQL"):
        return "pg"
    if stage_name.startswith("api:"):
        return "api"
    if stage_name.startswith("mobile:"):
        return "mobile"
    if stage_name.startswith("web: Playwright"):
        return "e2e"
    if stage_name.startswith("web:"):
        return "web"
    return None


def failed_keys(rows: list[dict]) -> list[str]:
    keys = []
    for r in rows:
        if r["result"] == "FAIL":
            k = stage_key(r["stage"])
            if k and k not in keys:
                keys.append(k)
    return keys


def fixers_for(keys: list[str], py: str) -> list[tuple[str, list[str], str]]:
    """(name, argv, folder relative to the repo) for the keys that failed."""
    out: list[tuple[str, list[str], str]] = []
    if "api" in keys or "pg" in keys:
        out.append(("ruff autofix", [py, "-m", "ruff", "check", "--fix", "."], "services/api"))
        out.append(("export OpenAPI contract", [py, "scripts/export_openapi.py"], "services/api"))
    if "mobile" in keys:
        out += [
            ("theme", ["dart", "run", "tool/gen_theme.dart"], "apps/mobile"),
            ("translations", ["flutter", "gen-l10n"], "apps/mobile"),
            ("API client", ["dart", "run", "tool/gen_api.dart"], "apps/mobile"),
            ("contract cases", [py, "tools/coverage/generate_contract_cases.py"], "."),
        ]
    if "web" in keys:
        out.append(("web lint autofix", ["npm", "run", "lint", "--", "--fix"], "apps/web"))
    return out


def check_env(repo: str) -> dict:
    return {"PYTHONPATH": f"{repo}/services/api"}


def run_checks(log: RunLog, repo: str, label: str, args: list[str]) -> tuple[bool, list[dict]]:
    """Run check-local.sh and record the stage lines. This is the evidence of what ran locally."""
    argv = [f"{repo}/tools/dev/check-local.sh", "--skip-sync", *args]
    res = log.run(f"check-local {label}", argv, cwd=repo, env=check_env(repo), timeout=CHECKS_TIMEOUT)
    rows = report.parse_check_summary(res.text())
    log.manifest["local_checks"].append({
        "label": label, "command": "tools/dev/check-local.sh " + " ".join(["--skip-sync", *args]),
        "exit": res.rc, "stages": rows, "log": str(res.log_path.relative_to(log.dir)),
    })
    log.save()
    return res.rc == 0, rows


def local_checks(log: RunLog, repo: str, py: str, attempts: int = MAX_ATTEMPTS) -> bool:
    """Run everything (PostgreSQL and browser tests included), then the fix loop. True when green."""
    ok, rows = run_checks(log, repo, "combined branch, all stages", ["--e2e"])
    if ok:
        return True
    keys = failed_keys(rows)
    if not keys:
        log.note("check-local failed without naming a stage (setup error?); no fix attempted")
        return False
    for n in range(1, attempts + 1):
        with log.stage(4, f"Fix and rerun (attempt {n} of {attempts})") as st:
            changed = False
            for name, argv, folder in fixers_for(keys, py):
                log.run(f"fix: {name}", argv, cwd=f"{repo}/{folder}", env=check_env(repo), timeout=900)
            status = log.run("git status after fix", ["git", "status", "--porcelain"], cwd=repo)
            changed = bool(status.text().strip())
            if not changed:
                st["detail"] = "the mechanical fixes changed nothing"
                log.manifest["fix_attempts"].append({"n": n, "outcome": "no change; stopped"})
                return False
            log.run("git add", ["git", "add", "-A"], cwd=repo)
            log.run("git commit", ["git", "-c", "user.name=Priveo Nightly", "-c", "user.email=nightly@priveo.invalid",
                                   "commit", "-q", "-m", "nightly: regenerate files"], cwd=repo)
            still = []
            for key in keys:
                ok, _ = run_checks(log, repo, f"rerun after fix {n}: {key}", ["--only", key])
                if not ok:
                    still.append(key)
            log.manifest["fix_attempts"].append(
                {"n": n, "outcome": "fixed" if not still else "still failing: " + ", ".join(still)})
            if not still:
                st["detail"] = "fixed by regenerating files"
                return True
            keys = still
    return False


def bisect_and_drop(log: RunLog, repo: str, selection: dict, merged: list[dict], date: str) -> list[dict]:
    """Run each merged PR alone. Returns [{number, reason}] for the ones that fail alone."""
    culprits = []
    for pr in merged:
        n = pr["number"]
        one = {"selected": [{"number": n, "title": pr["title"], "head": pr["head"], "url": pr.get("url", "")}]}
        res = build_combined.build(repo, one, f"nightly/solo-{date}-{n}")
        if res["dropped"] or res["migration_problems"]:
            culprits.append({"number": n, "reason": "it does not build alone on main: "
                             + "; ".join([d["reason"] for d in res["dropped"]] + res["migration_problems"])})
            continue
        ok, rows = run_checks(log, repo, f"solo PR #{n}", ["--changed", "--e2e"])
        if not ok:
            bad = ", ".join(r["stage"] for r in rows if r["result"] == "FAIL") or "setup"
            culprits.append({"number": n, "reason": f"its own local checks fail alone ({bad})"})
    return culprits
