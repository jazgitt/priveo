"""Performance harness for the two-pass planner (SCHS-49).

Times `passes.solve_passes` on generated sites and prints the solve seconds per
site-day against the limit, for 30, 60 and 120 cars and for a 7-day run. The
limit is read from the settings: `scheduler.solve_seconds` per pass, so a site-day
may take twice that (Exterior pass plus Interior pass), plus 10 percent for building
the model. Nothing touches a
database; the data is generated from a fixed seed.

Run it from services/api:

    .venv/bin/python scripts/bench_scheduler.py                 # 30, 60, 120 cars and 7 days
    .venv/bin/python scripts/bench_scheduler.py --cars 60 --days 3 --seconds 5

The exit code is 1 when a site-day went over the limit. The pytest check of the
full sizes, `tests/scheduling/rules_v2/test_schs_SCHS-49_bench_smoke.py`, is
skipped unless the environment variable PRIVEO_BENCH is set (PRIVEO_BENCH=1
pytest tests/scheduling/rules_v2/test_schs_SCHS-49_bench_smoke.py); a small
sample always runs.

Generated day (Derived): a cleaner works 05:30 to 11:00 for every 6 cars, each
car has a 30 minute Exterior, one car in three has a 30 minute Interior due by a
cutoff between 09:30 and 11:00, and each cleaner has the default break.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.directory import settings_registry
from app.scheduling import passes
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams

SIZES = (30, 60, 120)
CARS_PER_CLEANER = 6
GRACE = 1.1  # model building is outside the solver's own clock
WEEK = 7
PASS_LIMIT_KEY = "scheduler.solve_seconds"
INTERIOR = "Cleaning-Internal"


@dataclass(frozen=True)
class Row:
    label: str
    cars: int
    days: int
    seconds: float  # per site-day, the slowest
    total: float
    limit: float  # per site-day
    placed: int
    unplaced: int

    @property
    def ok(self) -> bool:
        return self.seconds <= self.limit * GRACE


def _value(key: str) -> int:
    return int(settings_registry.default_for(key))


def make_day(cars: int, seed: int) -> tuple[list[SolverCrew], list[SolverJob], dict]:
    rng = random.Random(seed)
    start, end = _value("site.first_job_minute"), 660
    cleaners = max(1, -(-cars // CARS_PER_CLEANER))
    crew = [SolverCrew(f"c{i}|0", start, end) for i in range(cleaners)]
    brk = (_value("site.break_start_minute"), _value("site.break_end_minute"))
    inputs = {"break_block": {c.key: brk for c in crew}}
    jobs = []
    for n in range(cars):
        jobs.append(SolverJob(f"e{n}", f"v{n}", 30, service=passes.EXTERIOR))
        if n % 3 == 0:
            cutoff = rng.choice((570, 600, 630, 660))
            jobs.append(SolverJob(f"i{n}", f"v{n}", 30, finish_by=cutoff, service=INTERIOR,
                                  windows=((_value("site.interior_earliest_minute"), end),)))
    return crew, jobs, inputs


def bench(cars: int, days: int = 1, seed: int = 7, max_seconds: float | None = None, label: str = "") -> Row:
    pass_limit = float(max_seconds if max_seconds is not None else _value(PASS_LIMIT_KEY))
    settings = {k: v for k, v in ((d.key, d.default) for d in settings_registry.RULE_DEFINITIONS)}
    params = SolverParams(max_seconds=pass_limit, settings=settings)
    worst = total = 0.0
    placed = unplaced = 0
    for day in range(days):
        crew, jobs, inputs = make_day(cars, seed + day)
        begun = time.perf_counter()
        result = passes.solve_passes(crew, jobs, params, inputs)
        spent = time.perf_counter() - begun
        worst, total = max(worst, spent), total + spent
        placed, unplaced = placed + len(result.placed), unplaced + len(result.unplaced)
    return Row(label or f"{cars} cars", cars, days, worst, total, 2 * pass_limit, placed, unplaced)


def run(sizes=SIZES, week_cars: int = 60, max_seconds: float | None = None) -> list[Row]:
    rows = [bench(n, 1, max_seconds=max_seconds) for n in sizes]
    rows.append(bench(week_cars, WEEK, max_seconds=max_seconds, label=f"{WEEK}-day run, {week_cars} cars"))
    return rows


def render(rows: list[Row]) -> str:
    head = f"{'case':<22}{'days':>5}{'s/site-day':>12}{'total s':>9}{'limit s':>9}"
    lines = [head + f"{'placed':>8}{'unplaced':>9}  result"]
    for r in rows:
        lines.append(f"{r.label:<22}{r.days:>5}{r.seconds:>12.2f}{r.total:>9.2f}{r.limit:>9.1f}"
                     f"{r.placed:>8}{r.unplaced:>9}  {'ok' if r.ok else 'OVER'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cars", type=int, nargs="*", help="car counts (default 30 60 120)")
    parser.add_argument("--days", type=int, default=WEEK, help="days of the long run (default 7)")
    parser.add_argument("--seconds", type=float, help="time limit of one pass (default: the setting)")
    args = parser.parse_args(argv)
    rows = [bench(n, 1, max_seconds=args.seconds) for n in (args.cars or SIZES)]
    if not args.cars:
        rows.append(bench(60, args.days, max_seconds=args.seconds, label=f"{args.days}-day run, 60 cars"))
    print(render(rows))
    return 0 if all(r.ok for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
