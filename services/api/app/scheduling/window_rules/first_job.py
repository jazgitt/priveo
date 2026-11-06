"""First-job floor: no job starts before the cleaner's first-job time, so a
window starts at the later of that time and its own start (SCHR-PAR-04,
SCHR-HARD-04). The reporting time is not used here. A Late start has already
moved the window start; the later of the two still wins. Runs only at
`scheduler.rules_version` 2."""
from app.directory import lookup
from app.directory.site_settings import SettingMissing
from app.scheduling import crew_rules

ORDER = 20  # after the base rules and the weekly off


def _active(db, society_id) -> bool:
    try:
        return int(lookup.rules_version(db, society_id)) == 2
    except SettingMissing:
        return False


def cleaner_windows(db, crew, day, windows, exception):
    site = getattr(crew, "society_id", None)  # a bare crew stand-in has no site
    if not windows or site is None or not _active(db, site):
        return windows
    floor = crew_rules.first_job_minute(db, crew)
    return [(max(s, floor), e) for s, e in windows if e > max(s, floor)]
