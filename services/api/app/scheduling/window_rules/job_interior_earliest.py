"""Interior earliest start: a Cleaning-Internal job may not start before the
site's Interior-earliest time, on any day, weekday or weekend (SCHR-PAR-08,
SCHR-HARD-05, SCHR-INT-03). The band before it stays for Exterior jobs
(SCHR-EXT-08)."""
from app.directory import lookup
from app.directory.site_settings import SettingMissing

ORDER = 30  # after the base rules and weekly_off (10); distinct from first_job (SCHS-15)

INTERIOR = "Cleaning-Internal"


def job_windows(db, society_id, service, day, windows):
    if service != INTERIOR or not windows:
        return windows
    try:
        earliest = int(lookup.site_setting(db, society_id, "site.interior_earliest_minute"))
    except SettingMissing:
        return windows
    return tuple((max(s, earliest), e) for s, e in windows if e > earliest)
