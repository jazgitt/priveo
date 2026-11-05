"""Window rules, found by folder. Each module in this package is one rule; a
new rule is a new file, with no registry to edit. A module may define any of:

    ORDER = 100                       # lower runs first; ties by module name
    cleaner_windows(db, crew, day, windows, exception) -> windows
        adjusts one cleaner's working windows for one day. `windows` is the
        previous rule's result (None for the first); `exception` is that
        day's SchedulingCrewException or None.
    job_windows(db, society_id, service, day, windows) -> windows
        adjusts the windows a service's jobs may be placed in on `day`.
    capacity_lines(db, society_id, day) -> list[dict]
        extra lines for the day's `demand` list on the capacity page; each is
        {"service", "source", "jobs", "minutes"} and its minutes count as demand.

Modules whose name starts with an underscore are skipped.
"""
import importlib
import pkgutil
from types import ModuleType

DEFAULT_ORDER = 100


def discover() -> list[ModuleType]:
    """The rule modules in this folder, in a fixed order: ORDER, then name."""
    mods = [
        importlib.import_module(f"{__name__}.{info.name}")
        for info in pkgutil.iter_modules(__path__)
        if not info.name.startswith("_")
    ]
    return sorted(mods, key=lambda m: (getattr(m, "ORDER", DEFAULT_ORDER), m.__name__))
