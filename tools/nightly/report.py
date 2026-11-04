"""Stage 10: the morning report, built from the manifest."""
from __future__ import annotations

import re
from pathlib import Path

CHECK_LINE = re.compile(r"^\s*(PASS|FAIL)\s+(.+?)\s+\((\d+)s\)\s*$")


def parse_check_summary(text: str) -> list[dict]:
    """The Summary block of tools/dev/check-local.sh: `  PASS  api: ruff...  (12s)`."""
    out = []
    for line in text.splitlines():
        m = CHECK_LINE.match(line)
        if m:
            out.append({"result": m.group(1), "stage": m.group(2), "seconds": int(m.group(3))})
    return out


def result_line(m: dict) -> str:
    result = m["result"]
    if result == "ok":
        n = len(m["merged_prs"])
        return f"All stages passed. {n} pull request(s) merged and test deployed."
    if result == "quiet":
        return "Quiet night: " + (m.get("quiet_reason") or "nothing to do") + "."
    if result == "dry-run-ok":
        return "Dry run finished. Nothing was pushed, merged, labelled or deployed."
    failed = [s for s in m["stages"] if s["status"] in ("failed", "error")]
    if failed:
        s = failed[-1]
        return f"Stopped at stage {s['num']} ({s['name']}): {s['detail']}"
    return f"Result: {result}"


def build(m: dict, log_dir: Path, shorten_home: bool = True) -> str:
    L: list[str] = []
    add = L.append
    add(f"# Nightly report, {m['started'][:10]} ({m['mode']})")
    add("")
    add(f"**Result:** {result_line(m)}")
    add(f"**Started:** {m['started']}  **Finished:** {m.get('finished') or 'n/a'}")
    add(f"**Production:** {m['production']}")
    add("")
    add("## Pull requests taken")
    if m["selected"]:
        merged = {p["number"] for p in m["merged_prs"]}
        for p in m["selected"]:
            tag = "merged" if p["number"] in merged else ("in combined branch" if p.get("in_branch") else "selected")
            add(f"- #{p['number']} {p['title']} (head `{p['head'][:9]}`, {tag}) {p.get('url', '')}")
    else:
        add("- none")
    add("")
    add("## Pull requests dropped")
    if m["dropped"]:
        for d in m["dropped"]:
            add(f"- #{d['number']}: {d['reason']}")
    else:
        add("- none")
    add("")
    add("## Stages")
    add("| # | Stage | Status | Started | Ended | Seconds | Detail |")
    add("|---|---|---|---|---|---|---|")
    for s in m["stages"]:
        add(f"| {s['num']} | {s['name']} | {s['status']} | {s['started'][11:19]} | "
            f"{(s['ended'] or '')[11:19]} | {s.get('seconds', '')} | {s['detail']} |")
    add("")
    add("## Local checks (run on the combined branch in the nightly clone)")
    if m["local_checks"]:
        for run in m["local_checks"]:
            add(f"- {run['label']}: `{run['command']}` exit {run['exit']}")
            for c in run["stages"]:
                add(f"  - {c['result']} {c['stage']} ({c['seconds']}s)")
    else:
        add("- none run")
    add("")
    if m.get("flake_retries"):
        add("## Flake retry")
        for r in m["flake_retries"]:
            add(f"- first run failed: {', '.join(r['stages'])}; after {int(r['pause_seconds'])}s only those "
                f"stages were rerun: {r['second']}")
        add("")
    add(f"## Fix attempts used: {len(m['fix_attempts'])} of 2")
    for a in m["fix_attempts"]:
        add(f"- attempt {a['n']}: {a['outcome']}")
    add("")
    add("## CI on the nightly pull request")
    if m.get("nightly_pr"):
        add(f"- Nightly pull request: {m['nightly_pr']}")
    if m["ci_checks"]:
        for c in m["ci_checks"]:
            add(f"- {c['name']}: {c['state']} {c.get('link', '')}")
    else:
        add("- no CI checks recorded")
    add("")
    add("## Merge and test deploy")
    add(f"- Merge commit on main: {m['merge_commit'] or 'none'}")
    d = m.get("deploy")
    if d:
        add(f"- Deploy run: {d.get('run_url') or 'none'} ({d.get('conclusion')})")
        add(f"- Smoke test step: {d.get('smoke')}")
        add(f"- Health check: {d.get('health')}")
    else:
        add("- no test deploy recorded")
    if m.get("rollback"):
        add(f"- ROLLBACK: {m['rollback']}")
    add("")
    if m["notes"]:
        add("## Notes")
        for n in m["notes"]:
            add(f"- {n}")
        add("")
    add("## Log trace")
    add(f"Folder: `{log_dir}` (events.jsonl, commands/, manifest.json, report.md)")
    text = "\n".join(L) + "\n"
    if shorten_home:
        text = text.replace(str(Path.home()), "~")
    return text
