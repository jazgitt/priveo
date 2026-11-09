"""Base rule: a job may be placed in the site's working slot for its service on
that day (ADM-CAP-08). The slot comes from the slot resolver, so an exception
for the date (ADM-SVS-12) replaces the Root slots for it. A service with no
slot, or a day with no slot, has no window: no work is planned there
(SCHR-PAR-16, ADM-SVS-05)."""
from app.directory import slot_resolver

ORDER = 0


def job_windows(db, society_id, service, day, windows):
    return slot_resolver.effective(db, society_id, service, day).windows
