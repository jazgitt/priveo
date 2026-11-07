"""Weekly off: a weekday on which none of the site's working slots, for any
service, is open is closed for the whole site (SCHR-PAR-02, SCHR-PAR-16,
SCHR-HARD-07). No cleaner has a window that day, whatever the crew hours say,
and no job has a window. A site with no slots has no closed day."""
from app.directory import lookup

ORDER = 10  # after the base rules, which build the windows this one clears


def _closed(db, society_id, day) -> bool:
    slots = lookup.working_slots(db, society_id)
    return bool(slots) and all(day.weekday() not in s.days for s in slots)


def cleaner_windows(db, crew, day, windows, exception):
    site = getattr(crew, "society_id", None)  # a bare crew stand-in has no site
    if site is not None and _closed(db, site, day):
        return []
    return windows


def job_windows(db, society_id, service, day, windows):
    if _closed(db, society_id, day):
        return ()
    return windows
