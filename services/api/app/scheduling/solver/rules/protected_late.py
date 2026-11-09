"""Protected jobs placed late are counted as their own objective (SCHR-CUT-09,
SCHR-HIER-09; owner decisions of 09-Nov-26, items 1 and 4).

A protected job is an Exterior (`Cleaning-External`). It is never a hard cutoff,
so the solver may place it after its cutoff. This objective counts the protected
jobs that end after their cutoff (the `late` variable of `base`), and the order
puts it above the home-zone objective:

    placed > protected_late > zone > break > fifo > cutoff_order > late > ...

So the rescue of a protected job by another cleaner (SCHR-ZONE-12) is worth more
than the home zone, but only for the protected lateness. Any other lateness (a
weekend Interior, for example) stays below the zone objective, as before.

The weight is `scheduler.weight_protected_late` (default 2 * 10**10). Within the
ordered solve only the order matters. In the single weighted solve (a direct call
without an order) it sits above one cross-zone assignment (10**4 * 10**6) and
below the 30 minute placement (30 * 10**9), so a protected job is still placed
late rather than dropped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext, SolverJob

NAME = "protected_late"
PRIORITY = 5  # after `base`, which creates the `late` variables


def add_job_terms(ctx: ModelContext, job: SolverJob) -> None:
    if not job.protected or job.finish_by is None:
        return
    late = ctx.late_vars.get(job.key)
    if late is not None:
        ctx.add_term("protected_late", -late)
