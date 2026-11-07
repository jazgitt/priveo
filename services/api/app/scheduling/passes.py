"""Two-pass planning of one day (SCHR-HIER-01, 02, 07, SCHR-EXT-03, SCHR-INT-07
to 09, SCHR-WKE-02).

Pass A places every Exterior job. Pass B then places the Interiors in the gaps,
with Pass A's placements (and any job already fixed) kept as fixed jobs. Exterior
first is a planning order only: Pass B may give an Interior to a cleaner who is
free while others still work on Exteriors (SCHR-INT-08). A job that is not an
Exterior (Interior, Deep Spa) is planned in Pass B (Derived).

Each pass is one `solve_day` call with its own time limit
(`scheduler.solve_seconds`), so the limit applies per pass. The rule modules see
which pass they are in (`ctx.pass_name`) and may add per-day inputs:

    day_inputs(run_ctx, day, crew) -> object
        optional function of a solver rule module; the result is handed to that
        module as `ctx.inputs[NAME]` in both passes.

Pass A also receives `ctx.inputs["pending_interiors"]`: the Interior jobs still to
place, so an Exterior-pass rule can leave room for them. Rules that need more add
a module to `solver/rules/`; this file does not change.


"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any

from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, SolverResult, solve_day
from app.scheduling.solver.registry import discover

EXTERIOR = "Cleaning-External"
PASS_A, PASS_B = "exterior", "interior"
PENDING = "pending_interiors"


def _is_free(job: SolverJob, crew_keys: set[str]) -> bool:
    return job.fixed is None or job.fixed[0] not in crew_keys


def solve_passes(
    crew: list[SolverCrew],
    jobs: list[SolverJob],
    params: SolverParams | None = None,
    inputs: dict[str, Any] | None = None,
) -> SolverResult:
    """Pass A, then Pass B. `inputs` is per rule module, by NAME."""
    params = params or SolverParams()
    inputs = dict(inputs or {})
    keys = {c.key for c in crew}
    exterior = [j for j in jobs if j.service == EXTERIOR and _is_free(j, keys)]
    interior = [j for j in jobs if j.service != EXTERIOR and _is_free(j, keys)]
    kept = [j for j in jobs if not _is_free(j, keys)]
    if not exterior:
        return solve_day(crew, kept + interior, params, PASS_B, inputs)
    first = solve_day(crew, kept + exterior, params, PASS_A, {**inputs, PENDING: interior})
    if not interior:
        return first
    # Pass A's placements are fixed for Pass B; an Exterior that found no place
    # is not planned again.
    fixed = [
        replace(j, fixed=first.placed[j.key]) for j in exterior if j.key in first.placed
    ]
    second = solve_day(crew, kept + fixed + interior, params, PASS_B, inputs)
    result = SolverResult(
        placed=second.placed,
        unplaced={**first.unplaced, **second.unplaced},
        unplaced_codes={**first.unplaced_codes, **second.unplaced_codes},
        late=first.late | second.late,
    )
    return result


def day_inputs(run_ctx, day: date, crew: list[SolverCrew]) -> dict[str, Any]:
    """What the rule modules that define `day_inputs` want to know about the day."""
    found: dict[str, Any] = {}
    for rule in discover():
        fn = getattr(rule.module, "day_inputs", None)
        if fn is not None:
            found[rule.name] = fn(run_ctx, day, crew)
    return found


def solve_two_pass(
    run_ctx, day: date, crew: list[SolverCrew], jobs: list[SolverJob], params: SolverParams
) -> SolverResult:
    """The planner's entry (called by `run_schedule`)."""
    params = replace(params, settings=dict(run_ctx.settings))
    return solve_passes(crew, jobs, params, day_inputs(run_ctx, day, crew))
