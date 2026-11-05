"""Base rule: a job may be placed in the site's working slots for its service
on that weekday (ADM-CAP-08). Without slots the existing fallbacks apply."""
from app.directory import lookup

ORDER = 0


def job_windows(db, society_id, service, day, windows):
    slots = lookup.working_slots(db, society_id, service)
    if not slots:
        return ((0, 1440),) if service == "Deep Spa" else ((300, 660),)
    return tuple((s.start_minute, s.end_minute) for s in slots if day.weekday() in s.days)
