"""Base rule: a job may be placed in the site's working slots for its service
on that weekday (ADM-CAP-08). A service with no slot, or a weekday with no slot,
has no window: no work is planned there (SCHR-PAR-16, ADM-SVS-05)."""
from app.directory import lookup

ORDER = 0


def job_windows(db, society_id, service, day, windows):
    slots = lookup.working_slots(db, society_id, service)
    return tuple((s.start_minute, s.end_minute) for s in slots if day.weekday() in s.days)
