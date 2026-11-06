"""Capacity extras, found by folder. A module in this package may define

    ORDER = 100
    day_fields(db, society_id, day, ctx) -> dict
        extra fields for one day of the capacity page. `ctx` has `crew`
        ({id: SchedulingCrew}), `windows` ({crew_id: usable windows}, break
        already taken out) and `busy` ({crew_id: [(start, end)]} of jobs
        already scheduled that day).

Modules whose name starts with an underscore are skipped (SCHS-34)."""
from types import ModuleType

from app.scheduling import hooks


def discover() -> list[ModuleType]:
    return hooks.discover_in(__name__, __path__)


def day_fields(db, society_id, day, ctx) -> dict:
    out: dict = {}
    for module in discover():
        fn = getattr(module, "day_fields", None)
        if fn is not None:
            out.update(fn(db, society_id, day, ctx) or {})
    return out
