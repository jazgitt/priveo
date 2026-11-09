"""Weekly off: a day on which no service of the site has an open slot is closed
for the whole site (SCHR-PAR-02, SCHR-PAR-16, SCHR-HARD-07). No cleaner has a
window that day, whatever the crew hours say, and no job has a window. An
exception that opens a service on a date (ADM-SVS-12) keeps that date open,
because the slot resolver counts it (decision 8, 9-Nov-26). A site with no Root
slots has no closed day."""
from app.directory import slot_resolver

ORDER = 10  # after the base rules, which build the windows this one clears


def _closed(db, society_id, day) -> bool:
    return slot_resolver.load(db, society_id).closed(day)


def cleaner_windows(db, crew, day, windows, exception):
    site = getattr(crew, "society_id", None)  # a bare crew stand-in has no site
    if site is not None and _closed(db, site, day):
        return []
    return windows


def job_windows(db, society_id, service, day, windows):
    if _closed(db, society_id, day):
        return ()
    return windows
