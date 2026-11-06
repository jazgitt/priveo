"""Hard weekday cutoff (SCHR-CUT-01 to 04, SCHR-HARD-08): on a strict day a job
that is placed ends by its car's Customer cutoff. A job that cannot is left
unassigned with the reason Customer cutoff. The caller marks a job
`hard_cutoff` only for a site on `scheduler.rules_version` 2 and a strict day
(`is_strict_day`), so version 1 and weekend days keep the soft penalty of the
base rule (the weekend is SCHS-20)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext, SolverJob

NAME = "job_cutoff"
PRIORITY = 40


def is_strict_day(ctx, day) -> bool:
    """True when the cutoff is a hard limit on `day`: the site is on version 2,
    the setting is on and the weekday is not a weekend day."""
    if not ctx.active or not ctx.setting("site.weekday_cutoff_hard"):
        return False
    return day.weekday() not in set(ctx.setting("site.weekend_weekdays"))


def add_job_terms(ctx: ModelContext, job: SolverJob) -> None:
    if not job.hard_cutoff or job.finish_by is None:
        return
    ctx.model.Add(
        ctx.start_vars[job.key] + ctx.durations[job.key] <= job.finish_by // ctx.params.step
    ).OnlyEnforceIf(ctx.placed_vars[job.key])


def cutoff_blocks(job: SolverJob) -> bool:
    """True when the cutoff is a hard limit for the job. A job of such a day
    that was not placed would have been placed late without it, so the cutoff is
    the reason it stays unassigned (S36)."""
    return job.hard_cutoff and job.finish_by is not None
