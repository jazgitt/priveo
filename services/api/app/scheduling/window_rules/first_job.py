"""First-job floor: no job starts before the cleaner's first-job time, so a
window starts at the later of that time and its own start (SCHR-PAR-04,
SCHR-HARD-04). The reporting time is not used here. A Late start has already
moved the window start; the later of the two still wins."""
from app.scheduling import crew_rules

ORDER = 20  # after the base rules and the weekly off


def cleaner_windows(db, crew, day, windows, exception):
    site = getattr(crew, "society_id", None)  # a bare crew stand-in has no site
    if not windows or site is None:
        return windows
    floor = crew_rules.first_job_minute(db, crew)
    return [(max(s, floor), e) for s, e in windows if e > max(s, floor)]
