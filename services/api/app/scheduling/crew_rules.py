"""A cleaner's reporting and first-job times: the cleaner's own value, else the
site's (SCHR-PAR-04, SCHR-PAR-05). Clearing the cleaner's value (null) returns
them to the site value, including a later change of it. Both come from the
settings layer; there is no default in code."""
from app.directory import lookup


def reporting_minute(db, crew) -> int:
    """When the cleaner reports. Recorded and shown only; never a job floor."""
    if crew.reporting_minute is not None:
        return crew.reporting_minute
    return lookup.site_setting(db, crew.society_id, "site.reporting_minute")


def first_job_minute(db, crew) -> int:
    """The earliest minute a job may start for this cleaner."""
    if crew.first_job_minute is not None:
        return crew.first_job_minute
    return lookup.site_setting(db, crew.society_id, "site.first_job_minute")
