"""Solver rules, one module per rule, found automatically by `solver.registry`.

Drop a file here and it is used; no other file changes. A module may define:

- `NAME` (str): defaults to the module name.
- `PRIORITY` (int): lower runs first; defaults to 100. Ties break by NAME.
- `add_job_terms(ctx, job)`: called for each placeable job after its variables
  exist; may add constraints and append objective terms to `ctx.objective`.
- `add_day_terms(ctx)`: called once after all jobs, before the overlap
  constraints and the objective are closed.

A module starting with an underscore is ignored.
"""
