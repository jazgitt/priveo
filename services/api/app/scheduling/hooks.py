"""Named hook points of the planner (SCHS-06). A hook point calls every module
found in its folder, in a fixed order, and does nothing when the folder holds
no module. Later stories add a file to a folder and edit no shared code.

Folder, function a module may define, and when it runs:

    demand_providers/  provide(ctx, demand) -> list[Demand] | None
        after `build_demand`; the returned items join the demand.
    job_sync/          sync(ctx, job, item)
        for a job that already exists and is refreshed from its demand item.
    post_solve/        after_solve(ctx, day, items, result)
        after a day was solved and its placements were copied to the jobs.
    hook_handlers/     on_status_change(db, job, source)
        after a job's status changed. `source` says where: "crew", "visit_skip",
        "customer_change" or "addon_cancel". It runs inside the caller's
        transaction before its commit; a handler must not commit.
    routes/            router (an APIRouter) or routers (a list of them)
        included by `scheduling.register`.

Each module may also set `ORDER` (default 100; lower runs first, ties by
module name). A name that starts with an underscore is skipped.

"""
from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

DEFAULT_ORDER = 100


def discover_in(package: str, path) -> list[ModuleType]:
    """The public modules of a folder, by (ORDER, module name)."""
    importlib.invalidate_caches()
    mods = [
        importlib.import_module(f"{package}.{info.name}")
        for info in pkgutil.iter_modules(path)
        if not info.name.startswith("_")
    ]
    return sorted(mods, key=lambda m: (getattr(m, "ORDER", DEFAULT_ORDER), m.__name__))


def _each(folder: str, function: str):
    """(module, function) for every module of the folder that defines it."""
    package = importlib.import_module(f"app.scheduling.{folder}")
    for module in package.discover():
        fn = getattr(module, function, None)
        if fn is not None:
            yield fn


def demand_providers(ctx, demand: list) -> list:
    extra: list = []
    for fn in _each("demand_providers", "provide"):
        extra.extend(fn(ctx, demand) or [])
    return demand + extra if extra else demand


def sync_existing_job(ctx, job, item) -> None:
    for fn in _each("job_sync", "sync"):
        fn(ctx, job, item)


def after_solve(ctx, day, items, result) -> None:
    for fn in _each("post_solve", "after_solve"):
        fn(ctx, day, items, result)


def job_status_changed(db, job, source: str) -> None:
    """Nothing is read from the database unless a handler exists."""
    for fn in _each("hook_handlers", "on_status_change"):
        fn(db, job, source)
