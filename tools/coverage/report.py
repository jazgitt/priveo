"""Aggregate fresh tool outputs and enforce 90% line coverage per application area.

Run from the repository root after the three full suites. No source files are
omitted from the backend/web denominators. Flutter's generated sources are
reported separately and also included in the full mobile/combined totals.
"""
import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def lines(hit, total):
    return {"covered": hit, "total": total, "percent": round(100 * hit / total, 4) if total else 100}


def area(path):
    if ".g.dart" in path or "/l10n/" in path:
        return "Mobile generated"
    if "/admin_quick/" in path:
        return "Admin Mobile"
    if "/crew/" in path:
        return "Crew Mobile"
    if any(f"/{part}/" in path for part in ("customer", "changes_money", "support")):
        return "Customer Mobile"
    return "Mobile shared"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mobile", default="apps/mobile/coverage/final-lcov.info")
    parser.add_argument("--output", default="docs/coverage/unit-test-coverage.json")
    args = parser.parse_args()
    backend = json.loads((ROOT / "services/api/coverage-final.json").read_text())
    web = json.loads((ROOT / "apps/web/coverage/coverage-summary.json").read_text())
    results = {"Backend shared": lines(backend["totals"]["covered_lines"], backend["totals"]["num_statements"]), "Admin Web": lines(web["total"]["lines"]["covered"], web["total"]["lines"]["total"])}
    files = defaultdict(dict)
    for line in (ROOT / args.mobile).read_text().splitlines():
        if line.startswith("SF:"):
            name = line[3:].replace("\\", "/")
        elif line.startswith("DA:"):
            number, hit = map(int, line[3:].split(",")[:2])
            files[name][number] = files[name].get(number, 0) + hit
    totals = defaultdict(lambda: [0, 0])
    uncovered = []
    for name, records in files.items():
        hit, total = sum(v > 0 for v in records.values()), len(records)
        group = area(name)
        totals[group][0] += hit
        totals[group][1] += total
        uncovered.append({"file": name, "area": group, **lines(hit, total), "missing_lines": [n for n, v in records.items() if not v]})
    for group, (hit, total) in totals.items():
        results[group] = lines(hit, total)
    mobile_hit = sum(t[0] for t in totals.values())
    mobile_total = sum(t[1] for t in totals.values())
    results["Mobile all (including generated)"] = lines(mobile_hit, mobile_total)
    results["All application sources"] = lines(mobile_hit + results["Backend shared"]["covered"] + results["Admin Web"]["covered"], mobile_total + results["Backend shared"]["total"] + results["Admin Web"]["total"])
    # These two Dart libraries contain only exports/constants, not executable
    # statements. Everything else must appear in LCOV, even if uncovered.
    declarative = {"lib/core/ui/tokens.g.dart", "lib/features/splash/splash_strings.dart", "lib/main.dart"}
    sources = {p.relative_to(ROOT / "apps/mobile").as_posix() for p in (ROOT / "apps/mobile/lib").rglob("*.dart")}
    missing_sources = sorted(sources - files.keys() - declarative)
    branch = backend["totals"]
    result = {"measured_at_utc": datetime.now(timezone.utc).isoformat(), "metric": "executable line coverage", "threshold": 90, "areas": results, "unmeasured_mobile_sources": missing_sources, "mobile_declarative_sources": sorted(declarative), "backend_branch_percent": round(100 * branch.get("covered_branches", 0) / branch["num_branches"], 4) if branch.get("num_branches") else None, "web_branches": web["total"]["branches"], "web_statements": web["total"]["statements"], "web_functions": web["total"]["functions"], "mobile_files": sorted(uncovered, key=lambda r: r["total"] - r["covered"], reverse=True)}
    failures = [name for name, metric in results.items() if metric["percent"] < 90]
    result["passed"] = not failures and not missing_sources
    result["failed_areas"] = failures
    (ROOT / args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for name, metric in results.items():
        print(f"{name}: {metric['percent']:.2f}% ({metric['covered']}/{metric['total']})")
    if missing_sources:
        print("Not instrumented:", ", ".join(missing_sources))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
