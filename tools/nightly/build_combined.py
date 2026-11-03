#!/usr/bin/env python3
"""Stage 2: build the combined branch `nightly/DATE` from origin/main.

    build_combined.py --repo-dir DIR --selection FILE --branch nightly/2026-11-05 [--out FILE]

Each selected pull request is fetched (`pull/N/head`) and merged with --no-ff, in order.
A PR whose fetched head differs from the head recorded at selection is dropped ("head moved"),
so what is tested is what was selected. A PR that conflicts is dropped and the merge is aborted.
The branch is never pushed here. Nothing outside the given clone is touched.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import migrations  # noqa: E402

IDENT = ["-c", "user.name=Priveo Nightly", "-c", "user.email=nightly@priveo.invalid"]
MIGRATION_DIR = "services/api/migrations/versions"


def git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *IDENT, *args], cwd=repo, check=check, capture_output=True, text=True)


def chain_problems(repo: str) -> list[str]:
    folder = Path(repo) / MIGRATION_DIR
    if not folder.is_dir():
        return []
    texts = [p.read_text() for p in sorted(folder.glob("*.py"))]
    dupes = []
    seen = set()
    for t in texts:
        parsed = migrations.parse_migration(t)
        if parsed:
            if parsed[0] in seen:
                dupes.append(f"revision {parsed[0]} is defined twice")
            seen.add(parsed[0])
    return dupes + migrations.check_chain(migrations.chain_from_texts(texts))


def build(repo: str, selection: dict, branch: str) -> dict:
    git(repo, "fetch", "-q", "origin", "main")
    base = git(repo, "rev-parse", "origin/main").stdout.strip()
    git(repo, "checkout", "-q", "-B", branch, "origin/main")
    merged: list[dict] = []
    dropped: list[dict] = []
    for pr in selection["selected"]:
        n = pr["number"]
        fetched = git(repo, "fetch", "-q", "origin", f"+pull/{n}/head:refs/nightly/pr-{n}", check=False)
        if fetched.returncode != 0:
            dropped.append({"number": n, "reason": "its head could not be fetched", "comment": True})
            continue
        sha = git(repo, "rev-parse", f"refs/nightly/pr-{n}").stdout.strip()
        if sha != pr["head"]:
            dropped.append({"number": n, "comment": True,
                            "reason": f"its head moved from {pr['head'][:9]} to {sha[:9]} during the night"})
            continue
        res = git(repo, "merge", "--no-ff", "--no-edit", "-m", f"Merge PR #{n}: {pr['title']}", sha, check=False)
        if res.returncode != 0:
            files = git(repo, "diff", "--name-only", "--diff-filter=U", check=False).stdout.split()
            git(repo, "merge", "--abort", check=False)
            dropped.append({"number": n, "comment": True,
                            "reason": "it conflicts with main or an earlier pull request in "
                                      + (", ".join(files[:8]) or "unknown files")})
            continue
        merged.append({"number": n, "title": pr["title"], "head": sha, "url": pr.get("url", "")})
    problems = chain_problems(repo)
    return {"branch": branch, "base": base,
            "tip": git(repo, "rev-parse", "HEAD").stdout.strip(),
            "merged": merged, "dropped": dropped, "migration_problems": problems}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--selection", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()
    result = build(args.repo_dir, json.loads(Path(args.selection).read_text()), args.branch)
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(text)
    return 1 if result["migration_problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
