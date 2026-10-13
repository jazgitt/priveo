"""The scheduler as a pure function (ADM-SCH-02 to ADM-SCH-08).

One day, one society at a time. Jobs with a `fixed` placement (made by hand, or
already frozen) are kept and take up their crew member's time; the rest are
placed to use as much of the crew's time as possible. A job that cannot meet
its finish-by time is still placed when it fits, and flagged late; a job that
fits nowhere is returned as unplaced with a reason.
"""

from dataclasses import dataclass, field

from ortools.sat.python import cp_model

STEP = 5  # Start times fall on a grid of 5 minutes.

_PLACED = 1_000_000_000  # per minute of work placed: capacity use comes first
_LATE = 10_000_000  # then meeting the cutoff times
_EARLY = 1  # then earlier starts


@dataclass(frozen=True)
class SolverCrew:
    key: str
    start: int  # minutes after midnight
    end: int


@dataclass(frozen=True)
class SolverJob:
    key: str
    vehicle: str
    duration: int
    finish_by: int | None = None
    fixed: tuple[str, int] | None = None  # (crew key, start minute)
    windows: tuple[tuple[int, int], ...] | None = None


@dataclass
class SolverResult:
    placed: dict[str, tuple[str, int]] = field(default_factory=dict)
    unplaced: dict[str, str] = field(default_factory=dict)
    late: set[str] = field(default_factory=set)


def _up(minutes: int) -> int:
    return -(-minutes // STEP)


def solve_day(
    crew: list[SolverCrew], jobs: list[SolverJob], max_seconds: float = 10.0
) -> SolverResult:
    result = SolverResult()
    crew_by_key = {c.key: c for c in crew}
    free: list[SolverJob] = []
    kept: list[SolverJob] = []
    for job in jobs:
        if job.fixed is not None and job.fixed[0] in crew_by_key:
            result.placed[job.key] = job.fixed
            kept.append(job)
            if job.finish_by is not None and job.fixed[1] + job.duration > job.finish_by:
                result.late.add(job.key)
        else:
            free.append(job)

    if not free:
        return result
    if not crew:
        result.unplaced = {j.key: "No crew member works that day." for j in free}
        return result

    model = cp_model.CpModel()
    per_crew: dict[str, list] = {c.key: [] for c in crew}
    per_vehicle: dict[str, list] = {}
    objective = []

    for job in kept:
        crew_key, start = job.fixed
        interval = model.NewFixedSizeIntervalVar(start // STEP, _up(job.duration), f"fix_{job.key}")
        per_crew[crew_key].append(interval)
        per_vehicle.setdefault(job.vehicle, []).append(interval)

    placed_vars: dict[str, object] = {}
    start_vars: dict[str, object] = {}
    late_vars: dict[str, object] = {}
    presence: dict[tuple[str, str], object] = {}

    for job in free:
        dur = _up(job.duration)
        allowed = job.windows if job.windows is not None else ((0, 1440),)
        domains = [[_up(s), e // STEP - dur] for s, e in allowed if _up(s) + dur <= e // STEP]
        if not domains:
            result.unplaced[job.key] = "No working slot allows this service that day."
            continue
        fits = [
            c
            for c in crew
            if any(
                max(_up(c.start), lo) + dur <= min(c.end // STEP, hi + dur) for lo, hi in domains
            )
        ]
        if not fits:
            result.unplaced[job.key] = "No crew member's hours are long enough for this job."
            continue
        start = model.NewIntVarFromDomain(cp_model.Domain.FromIntervals(domains), f"s_{job.key}")
        start_vars[job.key] = start
        flags = []
        for c in fits:
            p = model.NewBoolVar(f"p_{job.key}_{c.key}")
            presence[(job.key, c.key)] = p
            flags.append(p)
            model.Add(start >= _up(c.start)).OnlyEnforceIf(p)
            model.Add(start + dur <= c.end // STEP).OnlyEnforceIf(p)
            per_crew[c.key].append(
                model.NewOptionalFixedSizeIntervalVar(start, dur, p, f"i_{job.key}_{c.key}")
            )
        placed = model.NewBoolVar(f"placed_{job.key}")
        model.Add(sum(flags) == placed)
        placed_vars[job.key] = placed
        # One vehicle is not worked on by two crew members at the same time.
        per_vehicle.setdefault(job.vehicle, []).append(
            model.NewOptionalFixedSizeIntervalVar(start, dur, placed, f"v_{job.key}")
        )
        objective.append(_PLACED * job.duration * placed)
        objective.append(-_EARLY * start)
        if job.finish_by is not None:
            late = model.NewBoolVar(f"late_{job.key}")
            late_vars[job.key] = late
            model.Add(start + dur <= job.finish_by // STEP).OnlyEnforceIf(late.Not())
            objective.append(-_LATE * late)

    for intervals in per_crew.values():
        model.AddNoOverlap(intervals)
    for intervals in per_vehicle.values():
        model.AddNoOverlap(intervals)
    model.Maximize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_seconds
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = 7
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for job in free:
            result.unplaced.setdefault(job.key, "The scheduler found no plan.")
        return result

    for job in free:
        if job.key in result.unplaced:
            continue
        if not solver.Value(placed_vars[job.key]):
            result.unplaced[job.key] = "Capacity is short for that day."
            continue
        crew_key = next(
            c.key
            for c in crew
            if (job.key, c.key) in presence and solver.Value(presence[(job.key, c.key)])
        )
        begin = solver.Value(start_vars[job.key]) * STEP
        result.placed[job.key] = (crew_key, begin)
        if job.finish_by is not None and begin + job.duration > job.finish_by:
            result.late.add(job.key)
    return result
