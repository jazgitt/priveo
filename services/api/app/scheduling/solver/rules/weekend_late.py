"""Weekend cutoff stays soft (SCHR-WKE-01, 03, 04): on a weekend day a job may
end after its car's Customer cutoff. It is counted as late (the base rule's
penalty prefers on-time) and must still end inside the cleaner's shift. The
car is assumed available at planning time.

The caller leaves `hard_cutoff` off a job when `is_flexible_day` is true, so
the hard cutoff of `job_cutoff` does not apply and the base soft penalty does.
The module adds no solver terms of its own."""

from __future__ import annotations

NAME = "weekend_late"
PRIORITY = 41


def is_flexible_day(ctx, day) -> bool:
    """True when the cutoff is only a preference on `day`: the site is on
    version 2, the setting is on and the weekday is a weekend day."""
    if not ctx.active or not ctx.setting("site.weekend_cutoff_flexible"):
        return False
    return day.weekday() in set(ctx.setting("site.weekend_weekdays"))
