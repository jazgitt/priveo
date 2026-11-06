"""The break is not capacity (SCHR-BRK-08, Derived): a cleaner's capacity for a
day is the working windows minus the break. This is a capacity-only adjustment.
It is not a `cleaner_windows` rule, because the break lookup reads the cleaner's
windows to decide whether the break falls inside them (SCHR-BRK-07). Runs only
at `scheduler.rules_version` 2."""
from app.directory import lookup
from app.directory.site_settings import SettingMissing
from app.scheduling import breaks


def _active(db, society_id) -> bool:
    try:
        return int(lookup.rules_version(db, society_id)) == 2
    except SettingMissing:
        return False


def capacity_windows(db, crew, day, windows):
    """`windows` with the cleaner's break taken out. Unchanged without a break."""
    if not windows or not _active(db, crew.society_id):
        return windows
    found = breaks.effective_break(db, crew, day)
    if found is None:
        return windows
    out = []
    for s, e in windows:
        if e <= found.start_minute or s >= found.end_minute:
            out.append((s, e))
            continue
        if s < found.start_minute:
            out.append((s, found.start_minute))
        if e > found.end_minute:
            out.append((found.end_minute, e))
    return out


def visible_break(db, crew, day):
    """The (start, end) minutes of the break to draw for the cleaner on `day`,
    or None: no break, the cleaner's day does not cover it, or the site is not
    at version 2 (SCHR-BRK-09, SCHS-35)."""
    if not _active(db, crew.society_id):
        return None
    found = breaks.effective_break(db, crew, day)
    return None if found is None else (found.start_minute, found.end_minute)
