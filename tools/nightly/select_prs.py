#!/usr/bin/env python3
"""Stage 1: choose and order the pull requests for tonight.

    select_prs.py [--repo-dir DIR] [--from-json FILE] [--out FILE]

Eligible: open, not a draft, base main, from this repository (not a fork), labelled `nightly`,
none of the labels `no-nightly`, `hold`, `needs-human`, and not reported as conflicting.
Order: ascending pull request number. Then migration clashes (see migrations.py) drop more.
Writes JSON: {"selected": [...], "dropped": [{"number", "reason"}]}.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import migrations  # noqa: E402

REQUIRED_LABEL = "nightly"
BLOCKING_LABELS = ("no-nightly", "hold", "needs-human")
MIGRATION_DIR = "services/api/migrations/versions/"
PR_FIELDS = "number,title,isDraft,baseRefName,labels,mergeable,headRefOid,headRefName,isCrossRepository,author,url"


def ineligible_reason(pr: dict) -> str | None:
    """None when the pull request may be taken, else the reason it is not."""
    labels = {label["name"] if isinstance(label, dict) else label for label in pr.get("labels", [])}
    if pr.get("isDraft"):
        return "it is a draft"
    if pr.get("baseRefName") != "main":
        return f"its base is {pr.get('baseRefName')}, not main"
    if pr.get("isCrossRepository"):
        return "it comes from a fork"
    if REQUIRED_LABEL not in labels:
        return "it has no `nightly` label"
    for blocking in BLOCKING_LABELS:
        if blocking in labels:
            return f"it has the label `{blocking}`"
    if pr.get("mergeable") == "CONFLICTING":
        return "it conflicts with main"
    return None


def select(prs: list[dict], main_chain: dict, pr_migrations: dict[int, dict]) -> dict:
    """Pure selection. pr_migrations: PR number -> {revision: down revisions} added by that PR."""
    dropped: list[dict] = []
    candidates = []
    for pr in sorted(prs, key=lambda p: p["number"]):
        reason = ineligible_reason(pr)
        if reason:
            dropped.append({"number": pr["number"], "reason": reason, "comment": False})
        else:
            candidates.append(pr)
    rejected = migrations.clashes(
        main_chain, {pr["number"]: pr_migrations.get(pr["number"], {}) for pr in candidates}
    )
    selected = []
    for pr in candidates:
        if pr["number"] in rejected:
            dropped.append({"number": pr["number"], "reason": rejected[pr["number"]], "comment": True})
        else:
            selected.append({
                "number": pr["number"], "title": pr["title"], "head": pr["headRefOid"],
                "branch": pr["headRefName"], "url": pr.get("url", ""),
                "migrations": sorted(pr_migrations.get(pr["number"], {})),
            })
    return {"selected": selected, "dropped": dropped}


# ---- real repository access -------------------------------------------------------

def _run(argv: list[str], cwd: str | None = None) -> str:
    return subprocess.run(argv, cwd=cwd, check=True, capture_output=True, text=True).stdout


def list_prs() -> list[dict]:
    """Open pull requests that carry the label, with an explicit limit (never silently capped)."""
    out = _run(["gh", "pr", "list", "--state", "open", "--label", REQUIRED_LABEL,
                "--limit", "100", "--json", PR_FIELDS])
    return json.loads(out)


def _show(repo_dir: str, rev: str, path: str) -> str:
    return _run(["git", "show", f"{rev}:{path}"], cwd=repo_dir)


def main_chain_from_repo(repo_dir: str) -> dict:
    names = _run(["git", "ls-tree", "--name-only", "origin/main", MIGRATION_DIR], cwd=repo_dir).split()
    return migrations.chain_from_texts([_show(repo_dir, "origin/main", n) for n in names if n.endswith(".py")])


def pr_migration_texts(repo_dir: str, number: int) -> list[str]:
    """Text of the migration files a fetched PR adds relative to main."""
    ref = f"refs/nightly/pr-{number}"
    added = _run(["git", "diff", "--name-only", "--diff-filter=A", f"origin/main...{ref}", "--", MIGRATION_DIR],
                 cwd=repo_dir).split()
    return [_show(repo_dir, ref, p) for p in added if p.endswith(".py")]


def pr_migrations_from_repo(repo_dir: str, pr: dict) -> dict:
    """Fetch the PR head and read the migrations it adds relative to main."""
    ref = f"refs/nightly/pr-{pr['number']}"
    _run(["git", "fetch", "-q", "origin", f"+pull/{pr['number']}/head:{ref}"], cwd=repo_dir)
    sha = _run(["git", "rev-parse", ref], cwd=repo_dir).strip()
    if sha != pr["headRefOid"]:
        pr["headRefOid"] = sha  # the head moved since the list call; record what we fetched
    added = _run(["git", "diff", "--name-only", "--diff-filter=A", f"origin/main...{ref}", "--", MIGRATION_DIR],
                 cwd=repo_dir).split()
    return migrations.chain_from_texts([_show(repo_dir, ref, p) for p in added if p.endswith(".py")])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--from-json", help="a fixture: {prs, main_chain, pr_migrations}; no network, no git")
    ap.add_argument("--out")
    args = ap.parse_args()
    if args.from_json:
        fx = json.loads(Path(args.from_json).read_text())
        chain = {k: tuple(v) for k, v in fx["main_chain"].items()}
        mig = {int(k): {r: tuple(d) for r, d in v.items()} for k, v in fx["pr_migrations"].items()}
        result = select(fx["prs"], chain, mig)
    else:
        prs = list_prs()
        chain = main_chain_from_repo(args.repo_dir)
        mig = {pr["number"]: pr_migrations_from_repo(args.repo_dir, pr)
               for pr in prs if ineligible_reason(pr) is None}
        result = select(prs, chain, mig)
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
