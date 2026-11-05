"""Base rule: a cleaner's windows are the weekday's hours (one or more slots),
then the role and the date's exception (ADM-CRW-04, ADM-CRW-09, ADM-CRW-25)."""
from app.scheduling import rules

ORDER = 0


def cleaner_windows(db, crew, day, windows, exception):
    base = rules.hours_windows(
        crew.working_hours, day.weekday(), crew.start_minute, crew.end_minute)
    return rules.windows_for(
        crew.role, base, exception.kind if exception else None,
        exception.from_minute if exception else None)
