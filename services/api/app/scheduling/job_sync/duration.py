"""SCHS-11: a re-run gives an unfrozen Scheduled job the current duration.

A job copies its duration when it is created. After an admin changes a
service's duration, the next Draft re-run brings the jobs that are still open
to the new length. Jobs of a Frozen schedule and jobs that have started keep
theirs. The value comes from the service table through the lookup.
"""
from app.directory import lookup


def sync(ctx, job, item) -> None:
    if ctx.frozen or job.status != "Scheduled":
        return
    minutes = lookup.durations(ctx.db).get(job.service)
    if minutes is not None:
        job.duration_minutes = minutes
