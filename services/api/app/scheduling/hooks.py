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

Kill switch: the run hooks run only when the site is on `scheduler.rules_version`
2 (`ctx.active`). Handlers can read the version from `ctx.rules_version`.
"""
from __future__ import annotations

import importlib
import pkgutil
import uuid
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
    if not ctx.active:
        return demand
    extra: list = []
    for fn in _each("demand_providers", "provide"):
        extra.extend(fn(ctx, demand) or [])
    return demand + extra if extra else demand


def sync_existing_job(ctx, job, item) -> None:
    if not ctx.active:
        return
    for fn in _each("job_sync", "sync"):
        fn(ctx, job, item)


def after_solve(ctx, day, items, result) -> None:
    if not ctx.active:
        return
    for fn in _each("post_solve", "after_solve"):
        fn(ctx, day, items, result)


def job_rules_version(db, job) -> int:
    """The rules version of the site a job belongs to (1 when unknown)."""
    from sqlalchemy import select

    from app.scheduling.models import Schedule, Visit

    society_id = db.scalar(
        select(Schedule.society_id).join(Visit, Visit.schedule_id == Schedule.id)
        .where(Visit.id == job.visit_id))
    return 1 if society_id is None else _version(db, society_id)


def job_status_changed(db, job, source: str) -> None:
    """Nothing is read from the database unless a handler exists and the job's
    site is on rules version 2."""
    handlers = list(_each("hook_handlers", "on_status_change"))
    if not handlers:
        return
    if job_rules_version(db, job) != 2:
        return
    for fn in handlers:
        fn(db, job, source)


def _version(db, society_id: uuid.UUID) -> int:
    """The site's rules version; a missing setting means 1 (the old rules)."""
    from app.directory import lookup
    from app.directory.site_settings import SettingMissing

    try:
        return int(lookup.rules_version(db, society_id))
    except SettingMissing:
        return 1
