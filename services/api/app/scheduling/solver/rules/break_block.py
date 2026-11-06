"""The break in the solver (SCHR-BRK-01 to 03).

Each cleaner tries to keep a continuous break (default 09:30 to 10:00). The
breaks of the day come from `day_inputs` (the break rules store, SCHS-23) as
`ctx.inputs["break_block"]`: `{crew key: (start minute, end minute)}`.

- Interior pass: a hard block. An Interior never overlaps a kept break; one that
  cannot go elsewhere is deferred (BRK-02). On a weekend this makes the break win
  over the cutoff, which stays soft there (HIER-05).
- Exterior pass (and a single pass): a soft block. Overlapping the break is
  allowed but costs the "break" objective, which ranks below coverage, so
  Exterior coverage wins over the break (BRK-03). A weekday hard cutoff is a hard
  constraint and so also wins.

Derived: on a weekday an Interior with a hard cutoff that only fits across the
break is left unassigned (the break is hard in the Interior pass, BRK-02).
Jobs fixed before the run (by hand, or Pass A) may sit on a break; they are
reported by `post_solve/missed_break.py`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext

NAME = "break_block"
PRIORITY = 60
INTERIOR_PASS = "interior"


def day_inputs(run_ctx, day, crew) -> dict[str, tuple[int, int]]:
    """The break of each solver crew key that works through it."""
    from app.scheduling import breaks
    from app.scheduling.models import SchedulingCrew

    found: dict[str, tuple[int, int]] = {}
    cache: dict[str, breaks.Break | None] = {}
    for member in crew:
        crew_id = member.key.split("|", 1)[0]
        if crew_id not in cache:
            row = run_ctx.db.get(SchedulingCrew, uuid.UUID(crew_id))
            cache[crew_id] = breaks.effective_break(run_ctx.db, row, day) if row else None
        brk = cache[crew_id]
        if brk is not None and member.start <= brk.start_minute and brk.end_minute <= member.end:
            found[member.key] = (brk.start_minute, brk.end_minute)
    return found


def add_day_terms(ctx: ModelContext) -> None:
    held = ctx.inputs.get(NAME) or {}
    if not held:
        return
    model, step = ctx.model, ctx.params.step
    hard = ctx.pass_name == INTERIOR_PASS
    missed: dict[str, object] = {}
    for (job_key, crew_key), present in ctx.presence.items():
        if crew_key not in held:
            continue
        begin, end = held[crew_key]
        first, last = begin // step, -(-end // step)  # the break, widened to the grid
        start, dur = ctx.start_vars[job_key], ctx.durations[job_key]
        before = model.NewBoolVar(f"brk_before_{job_key}_{crew_key}")
        after = model.NewBoolVar(f"brk_after_{job_key}_{crew_key}")
        model.Add(start + dur <= first).OnlyEnforceIf(before)
        model.Add(start >= last).OnlyEnforceIf(after)
        if hard:
            model.AddBoolOr([before, after, present.Not()])
            continue
        over = model.NewBoolVar(f"brk_over_{job_key}_{crew_key}")
        model.AddBoolOr([before, after, over, present.Not()])
        if crew_key not in missed:
            missed[crew_key] = model.NewBoolVar(f"brk_missed_{crew_key}")
        model.Add(missed[crew_key] >= over)
    for var in missed.values():
        ctx.add_term("break", -var)
