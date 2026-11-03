#!/usr/bin/env python3
"""The nightly pipeline, TEST PATH ONLY. See docs/nightly-pipeline.md.

    run-nightly.sh [--dry-run] [--skip-checks] [--ignore-recent-deploy]

Stages: 0 preflight, 1 select, 2 build, 3 local checks (4 fix loop inside), 5 push and CI,
6 merge, 7 test deploy and smoke test, 10 report. Stages 8 and 9 (production) do not exist: there
is no code path to production, to its database, or to a tag.
Every stage is a hard gate. The report always runs.
"""
from __future__ import annotations

import argparse
import importlib
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_combined  # noqa: E402
import fixloop  # noqa: E402
import report  # noqa: E402
import select_prs  # noqa: E402
from lib import DEFAULT_HOME, RunLog, Skipped, StageFailed, gh_json, kill_reason, now_iso  # noqa: E402

def optional(name: str):
    """A stage module that may not be installed in this version of the pipeline, or None."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def require(name: str):
    mod = optional(name)
    if mod is None:
        raise StageFailed(f"{name} is not part of this version of the pipeline")
    return mod


LOCK_STALE_SECONDS = 6 * 3600
RECENT_DEPLOY_SECONDS = 2 * 3600
TOOLS = ["git", "gh", "python3", "flutter", "dart", "node", "npm", "pg_ctl", "osascript"]


# ---- lock --------------------------------------------------------------------------

def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def acquire_lock(home: Path, now: float | None = None) -> str | None:
    """Create the lock. Returns None on success, else the reason it could not be taken."""
    lock = home / "nightly.lock"
    now = now or time.time()
    if lock.exists():
        try:
            pid_s, started_s = lock.read_text().split()
            pid, started = int(pid_s), float(started_s)
        except ValueError:
            return "the lock file is unreadable; check it and remove it by hand"
        if pid_alive(pid):
            if now - started > LOCK_STALE_SECONDS:
                return f"a run (pid {pid}) has held the lock for more than 6 hours; check it and remove the lock by hand"
            return f"another run is in progress (pid {pid})"
        lock.unlink()  # the process is gone: a crashed run
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as f:
        f.write(f"{os.getpid()} {now}\n")
    return None


def release_lock(home: Path) -> None:
    try:
        (home / "nightly.lock").unlink()
    except FileNotFoundError:
        pass


# ---- stage 0 -----------------------------------------------------------------------

def preflight(log: RunLog, home: Path, repo: str, args) -> str:
    """Returns the nightly date. Raises Skipped / StageFailed."""
    why = kill_reason(home, ignore_enabled=args.dry_run)
    if why:
        raise Skipped(f"switched off: {why}")
    missing = [t for t in TOOLS if shutil.which(t) is None]
    if missing:
        raise StageFailed("missing tools: " + ", ".join(missing))
    if not (Path(repo) / "services/api/.venv/bin/python").exists():
        raise StageFailed("no virtualenv in the nightly clone; run tools/nightly/setup-clone.sh")
    if not log.run("gh auth status", ["gh", "auth", "status"], timeout=60).ok:
        raise StageFailed("gh is not signed in")
    for name, argv in [("fetch", ["git", "fetch", "-q", "origin", "main"])]:
        if not log.run(name, argv, cwd=repo, timeout=300).ok:
            raise StageFailed("cannot reach GitHub (git fetch failed)")
    dirty = log.run("clone status", ["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo).text().strip()
    log.run("reset to origin/main", ["git", "checkout", "-q", "-B", "main", "origin/main"], cwd=repo)
    log.run("hard reset", ["git", "reset", "-q", "--hard", "origin/main"], cwd=repo)
    if dirty:
        log.note("the nightly clone had uncommitted tracked changes; they were discarded (it is a private clone)")
    runs = gh_json(log, "gh run list api-deploy", ["gh", "run", "list", "--workflow", "api-deploy.yml", "--limit", "8",
                   "--json", "createdAt,event,conclusion,status,headBranch,url"], cwd=repo) or []
    now = datetime.now().astimezone()
    for r in runs:
        age = (now - datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))).total_seconds()
        if age < RECENT_DEPLOY_SECONDS and not args.ignore_recent_deploy:
            raise Skipped(f"a deploy ran {int(age // 60)} minutes ago ({r['url']}); skipping the night")
    last_main = next((r for r in runs if r["event"] == "push" and r["headBranch"] == "main"
                      and r["status"] == "completed"), None)
    if last_main and last_main["conclusion"] == "failure":
        raise StageFailed(f"main is red: the last test deploy failed ({last_main['url']})")
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def between(home: Path, log: RunLog, dry: bool = False) -> None:
    why = kill_reason(home, ignore_enabled=dry)
    if why:
        raise Skipped(f"stopped between stages: {why}")


# ---- helpers -----------------------------------------------------------------------

def drop(log: RunLog, repo: str, home: Path, number: int, reason: str, comment: bool, dry: bool) -> None:
    log.manifest["dropped"].append({"number": number, "reason": reason})
    if comment and not dry:
        require("notify").label_needs_human(log, repo, number, reason, log.dir / f"drop-{number}.md")
    elif comment:
        log.note(f"dry run: would comment on #{number} and label it needs-human ({reason})")


def nightly_body(log: RunLog, merged: list[dict]) -> str:
    lines = ["Combined branch built by the nightly run (test path only). It includes:", ""]
    lines += [f"- #{p['number']} {p['title']} (head `{p['head'][:9]}`)" for p in merged]
    lines += ["", "Merged with a merge commit once the required checks are green. Production is not touched.",
              f"Local evidence: {log.dir.name} in the nightly clone's logs folder."]
    return "\n".join(lines) + "\n"


# ---- the run -----------------------------------------------------------------------

def run(args) -> int:
    home = Path(args.home)
    repo = str(home)
    if not args.allow_any_clone and Path(repo).resolve() != DEFAULT_HOME.resolve():
        print("Refusing to run outside the nightly clone", DEFAULT_HOME, file=sys.stderr)
        return 2
    (home / "logs").mkdir(exist_ok=True)
    log = RunLog(home / "logs", dry_run=args.dry_run)
    why = acquire_lock(home)
    if why:
        log.manifest["result"] = "quiet"
        log.manifest["quiet_reason"] = why
        finish(log, home, repo, args, notify_user=False)
        return 0
    try:
        return pipeline(log, home, repo, args)
    finally:
        release_lock(home)


def pipeline(log: RunLog, home: Path, repo: str, args) -> int:
    m = log.manifest
    py = f"{repo}/services/api/.venv/bin/python"
    date = ""
    try:
        with log.stage(0, "Preflight"):
            date = preflight(log, home, repo, args)
        branch = f"nightly/{date}"
        if not args.dry_run:
            if log.run("remote branch check", ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
                       cwd=repo).ok:
                branch += datetime.now().strftime("-%H%M")

        between(home, log, args.dry_run)
        with log.stage(1, "Select pull requests") as st:
            prs = select_prs.list_prs()
            chain = select_prs.main_chain_from_repo(repo)
            mig = {p["number"]: select_prs.pr_migrations_from_repo(repo, p) for p in prs
                   if select_prs.ineligible_reason(p) is None}
            selection = select_prs.select(prs, chain, mig)
            m["selected"] = selection["selected"]
            for d in selection["dropped"]:
                if d["comment"]:
                    drop(log, repo, home, d["number"], d["reason"], True, args.dry_run)
                else:
                    log.event("not_taken", number=d["number"], reason=d["reason"])
            st["detail"] = f"{len(selection['selected'])} selected"
            if not selection["selected"]:
                m["quiet_reason"] = "no pull request has the label nightly and is ready"
                raise Skipped(m["quiet_reason"])

        # migration safety (step 5): drop a PR whose migration would break the previous version
        safety = optional("migration_safety")
        if safety is None:
            log.note("migration safety checks are not part of this version of the pipeline")
        for pr in list(selection["selected"]) if safety else []:
            texts = select_prs.pr_migration_texts(repo, pr["number"]) if pr.get("migrations") else []
            verdicts = [safety.check_migration(t) for t in texts]
            blocks = [b for v in verdicts for b in v["block"]]
            for v in verdicts:
                for w in v["warn"]:
                    log.note(f"PR #{pr['number']} migration warning: {w}")
            if blocks:
                selection["selected"].remove(pr)
                drop(log, repo, home, pr["number"], "its migration is not forward-safe: " + "; ".join(blocks),
                     True, args.dry_run)
        m["selected"] = selection["selected"]
        if not selection["selected"]:
            m["quiet_reason"] = "every selected pull request was dropped"
            raise Skipped(m["quiet_reason"])

        between(home, log, args.dry_run)
        with log.stage(2, "Build the combined branch") as st:
            built = build_combined.build(repo, selection, branch)
            for d in built["dropped"]:
                drop(log, repo, home, d["number"], d["reason"], True, args.dry_run)
            if built["migration_problems"]:
                raise StageFailed("migration chain problem: " + "; ".join(built["migration_problems"]))
            merged_numbers = {p["number"] for p in built["merged"]}
            for p in m["selected"]:
                p["in_branch"] = p["number"] in merged_numbers
            if not built["merged"]:
                m["quiet_reason"] = "no pull request could be merged into the combined branch"
                raise Skipped(m["quiet_reason"])
            st["detail"] = f"{len(built['merged'])} merged into {branch}, base {built['base'][:9]}"

        between(home, log, args.dry_run)
        with log.stage(3, "Local checks") as st:
            if args.skip_checks:
                log.note("local checks skipped by --skip-checks (never use this for a real night)")
                st["detail"] = "skipped"
            else:
                ok = fixloop.local_checks(log, repo, py)
                if not ok:
                    culprits = fixloop.bisect_and_drop(log, repo, selection, built["merged"], date)
                    if not culprits:
                        raise StageFailed("local checks fail and no single pull request is the cause "
                                          "(they fail only in combination, or on main itself)")
                    for c in culprits:
                        drop(log, repo, home, c["number"], c["reason"], True, args.dry_run)
                    keep = {"selected": [p for p in selection["selected"]
                                         if p["number"] not in {c["number"] for c in culprits}]}
                    built = build_combined.build(repo, keep, branch)
                    if not built["merged"]:
                        raise StageFailed("no pull request is left after dropping the failing ones")
                    ok, _ = fixloop.run_checks(log, repo, "combined branch after drops, all stages", ["--e2e"])
                    if not ok:
                        raise StageFailed("local checks still fail after dropping the failing pull requests")
                st["detail"] = "all local checks passed"
        merged = built["merged"]

        if args.dry_run:
            m["result"] = "dry-run-ok"
            log.note(f"dry run: would push {branch}, open a pull request, wait for CI, merge it with a merge "
                     f"commit, wait for the test deploy and smoke test, and roll back on red. PRs: "
                     + ", ".join(f"#{p['number']}@{p['head'][:9]}" for p in merged))
            return finish(log, home, repo, args, merged=[])

        between(home, log, args.dry_run)
        with log.stage(5, "Push and CI") as st:
            gate = require("gate")
            gate.push_branch(log, repo, branch)
            body = log.dir / "nightly-pr-body.md"
            body.write_text(nightly_body(log, merged))
            number = gate.open_pr(log, repo, branch, body, f"Nightly {date}: " + ", ".join(f"#{p['number']}" for p in merged))
            verdict = gate.wait_for_checks(log, repo, number)
            st["detail"] = f"CI {verdict} on #{number}"

        between(home, log, args.dry_run)
        with log.stage(6, "Merge to main") as st:
            sha = gate.merge_pr(log, repo, number)
            gate.settle_included_prs(log, repo, merged, number, sha)
            m["merged_prs"] = merged
            st["detail"] = f"merge commit {sha[:9]}"

        with log.stage(7, "Test deploy and smoke test") as st:
            deploy = require("deploy")
            rec = deploy.wait_and_check(log, repo, sha)
            m["deploy"] = rec
            st["detail"] = f"{rec['conclusion']}; smoke {rec['smoke']}; health {rec['health']}"
            if not rec["ok"]:
                rb = require("rollback").rollback(log, repo, sha)
                raise StageFailed(st["detail"] + ("; rolled back" if rb["ok"] else "; ROLLBACK FAILED, act by hand"))
        m["result"] = "ok"
        return finish(log, home, repo, args, merged=merged)
    except Skipped as e:
        m["result"] = "quiet"
        m.setdefault("quiet_reason", str(e))
        return finish(log, home, repo, args, notify_user=False)
    except StageFailed:
        m["result"] = "failed"
        return finish(log, home, repo, args, merged=m["merged_prs"])
    except Exception as e:  # noqa: BLE001
        m["result"] = "failed"
        log.note(f"unexpected error: {type(e).__name__}: {e}")
        return finish(log, home, repo, args, merged=m["merged_prs"])


# ---- stage 10 ----------------------------------------------------------------------

def finish(log: RunLog, home: Path, repo: str, args, merged: list[dict] | None = None, notify_user: bool = True) -> int:
    with log.stage(10, "Morning report"):
        m = log.manifest
        m["finished"] = now_iso()
        text = report.build(m, log.dir)
        (log.dir / "report.md").write_text(text)
        log.save()
        (home / "logs" / "latest").unlink(missing_ok=True)
        (home / "logs" / "latest").symlink_to(log.dir.name)
        if args.dry_run or not notify_user:
            if notify_user is False and not args.dry_run and m["result"] == "quiet":
                log.event("quiet", reason=m.get("quiet_reason"))
            return 0 if m["result"] != "failed" else 1
        short = report.result_line(m)
        notify = optional("notify")
        if notify is None:
            log.note("notifications are not part of this version of the pipeline")
            return 0 if m["result"] == "ok" else 1
        notify.mac_notification(log, "Priveo nightly", short)
        public = log.dir / "report-public.md"
        public.write_text(text)
        for pr in merged or []:
            notify.comment_on_pr(log, repo, pr["number"], public)
        issue = notify.github_issue(log, repo, f"Nightly {m['started'][:10]}: {m['result']}", public)
        if issue:
            log.note(f"issue: {issue}")
            m["issue"] = issue
            log.save()
    return 0 if m["result"] == "ok" else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-checks", action="store_true")
    ap.add_argument("--ignore-recent-deploy", action="store_true")
    ap.add_argument("--home", default=str(DEFAULT_HOME))
    ap.add_argument("--allow-any-clone", action="store_true", help="tests only")
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
