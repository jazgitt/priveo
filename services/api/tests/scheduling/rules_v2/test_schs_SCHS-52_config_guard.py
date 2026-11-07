"""SCHS-52: the build fails if a removed scheduler constant comes back.

SCHR-CFG-01 and SCHR-CFG-09 list the constants that moved into configuration
(scheduler-gap-analysis.md, "Hardcoded values to remove"). A source scan of the
scheduler, crew and directory code looks for each one. Seed values in
`directory/defaults.py` and `directory/seed.py`, and the type and range table in
`directory/settings_registry.py`, are allowed: they are what seeds the setting.

The constants whose removal belongs to stories that were not merged when this
guard was written are in a second test marked xfail (not strict): it starts to
pass when those stories land, and then the marker can be removed.
"""
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[3] / "app"
SCANNED = ("scheduling", "crew", "directory")
ALLOWED = {"directory/defaults.py", "directory/seed.py", "directory/settings_registry.py"}


def _code_lines():
    for folder in SCANNED:
        for path in sorted((APP / folder).rglob("*.py")):
            rel = path.relative_to(APP).as_posix()
            if rel in ALLOWED:
                continue
            for number, line in enumerate(path.read_text().splitlines(), 1):
                code = line.split("#", 1)[0]
                if code.strip():
                    yield rel, number, code


def _hits(patterns, only=None):
    found = []
    for rel, number, code in _code_lines():
        if only and not rel.startswith(only):
            continue
        for name, pattern in patterns.items():
            if re.search(pattern, code):
                found.append(f"{rel}:{number} {name}")
    return found


# Removed by SCHS-09 (freeze, customer hour, code, retry), SCHS-10 (durations),
# SCHS-25 (solver parameters).
REMOVED = {
    "FREEZE_HOUR": r"\bFREEZE_HOUR\b",
    "CUSTOMER_HOUR": r"\bCUSTOMER_HOUR\b",
    "UNFREEZE_CODE": r"\bUNFREEZE_CODE\b",
    "STEP module constant": r"^STEP\s*=",
    "solve time limit literal": r"max_seconds\s*=\s*\d",
    "worker count literal": r"num_workers\s*=\s*\d",
    "random seed literal": r"random_seed\s*=\s*\d",
    "retry minutes literal": r"timedelta\(\s*minutes\s*=\s*\d",
}

# Listed in the gap analysis; removed by later stories (objective weights,
# window fallbacks, crew defaults).
PENDING = {
    "objective weight _PLACED": r"^_PLACED\s*=",
    "objective weight _LATE": r"^_LATE\s*=",
    "objective weight _EARLY": r"^_EARLY\s*=",
    "default window (0, 1440)": r"\(0,\s*1440\)",
    "fallback window (300, 660)": r"\(300,\s*660\)",
    "crew model default start 360": r"start_minute.*default=360",
    "crew model default end 660": r"end_minute.*default=660",
}


def test_schr_cfg_09_removed_constants_do_not_come_back():
    assert _hits(REMOVED) == []


def test_schr_par_06_planner_has_no_duration_constant():
    # The service table is the only source of a duration for the planner. The
    # directory keeps its seed copy in defaults.py (allowed above).
    assert _hits({"DURATIONS": r"\bDURATIONS\b"}, only=("scheduling/", "crew/")) == []


def test_schr_cfg_01_no_hardcoded_scheduler_time_in_scheduler_code():
    # The settings lookup is the only place a freeze, customer or retry time
    # comes from: no clock literal such as 20:00 or 21:00 in the planner rules.
    literals = {"clock literal": r"""["']\d{2}:\d{2}["']"""}
    hits = [h for h in _hits(literals) if h.startswith(("scheduling/rules.py", "scheduling/automatic.py"))]
    assert hits == []


@pytest.mark.xfail(
    reason=("still hard-coded on 06-Nov-26 (open): the no-slot fallback window (300, 660) in "
            "window_rules/base_job_slots.py and crew/service.py; the full-day fallback (0, 1440) "
            "in solver/core.py, solver/rules/objective_order.py and window_rules/base_job_slots.py; "
            "the crew model defaults 360 and 660 in scheduling/models.py. Removing the fallbacks "
            "needs an owner decision: SCHR-PAR-16 says a weekday with no slot is a day off."),
    strict=False)
def test_schr_cfg_09_pending_constants_are_gone():
    assert _hits(PENDING) == []


def test_schr_cfg_09_guard_catches_a_returning_constant():
    # The scan itself works: a pattern matches the shapes it is meant to catch.
    assert re.search(REMOVED["FREEZE_HOUR"], "FREEZE_HOUR = 20")
    assert re.search(REMOVED["STEP module constant"], "STEP = 5")
    assert not re.search(REMOVED["STEP module constant"], "    STEP = params.step")
    assert re.search(REMOVED["retry minutes literal"], "timedelta(minutes=30)")
    assert not re.search(REMOVED["retry minutes literal"], "timedelta(minutes=lookup.x)")
