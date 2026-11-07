"""Why a job sits outside its cleaner's home zone (SCHS-45, SCHR-ZONE-06).

After a day is solved, every placed job whose car is in a zone other than the
home zone of its cleaner gets `Job.cross_zone_reason`; any other job loses a
reason it carried. The facts come from the solver rule `zones` (`ctx.zone_days`).

The reason is one of four texts (SCHR-ZONE-06):

* home-zone cleaner absent: no cleaner of the car's zone works that day,
* home zone full: the cleaners of that zone have no free time for the job,
* needed to meet a cutoff or the weekly Interior: they have no free time before
  the job's cutoff, or the job is the plan's Interior and they are full,
* spare capacity used: they had room, and this cleaner had spare time.

Derived: "full" is judged from the finished day, with the home cleaners' working
windows and the jobs they hold; the job's own slots are not checked again.
"""
from __future__ import annotations

import uuid

from app.scheduling import entitlements

ORDER = 70
ABSENT = "Home-zone cleaner absent"
FULL = "Home zone full"
NEEDED = "Needed to meet a cutoff or the weekly Interior"
SPARE = "Spare capacity used"
REASONS = (ABSENT, FULL, NEEDED, SPARE)


def _fits(windows, busy, duration, latest_end) -> tuple[bool, bool]:
    """(room anywhere, room before `latest_end`) in the windows around the busy spans."""
    anywhere = before = False
    for s, e in windows:
        at = s
        for b0, b1 in sorted(x for x in busy if x[0] < e and x[1] > s):
            if b0 - at >= duration:
                anywhere = True
                before = before or latest_end is None or at + duration <= latest_end
            at = max(at, b1)
        if e - at >= duration:
            anywhere = True
            before = before or latest_end is None or at + duration <= latest_end
    return anywhere, before


def after_solve(ctx, day, items, result) -> None:
    data = getattr(ctx, "zone_days", {}).get(day)
    for job, _visit in items:
        job.cross_zone_reason = None
    if not data:
        return
    home, cars = data["home"], data["vehicle_zone"]
    held: dict[uuid.UUID, list[tuple[int, int]]] = {}
    for job, _visit in items:
        if job.crew_id is not None and job.start_minute is not None and job.status != "Skipped":
            held.setdefault(job.crew_id, []).append((job.start_minute, job.start_minute + job.duration_minutes))

    def cleaner(key: str) -> uuid.UUID:
        return uuid.UUID(key.split("|", 1)[0])

    for job, visit in items:
        zone = cars.get(str(visit.vehicle_id))
        if zone is None or job.crew_id is None or job.start_minute is None or job.status == "Skipped":
            continue
        mine = {home.get(k) for k in home if cleaner(k) == job.crew_id} - {None}
        if not mine or zone in mine:
            continue  # no home zone for this cleaner, or the job is in it
        owners = {cleaner(k) for k, z in home.items() if z == zone}
        if not owners:
            job.cross_zone_reason = ABSENT
            continue
        windows = [data["crew"][k] for k, z in home.items() if z == zone]
        busy = [span for cid in owners for span in held.get(cid, ())]
        room, in_time = _fits(windows, busy, job.duration_minutes, job.finish_by_minute)
        if not room:
            job.cross_zone_reason = NEEDED if entitlements.uses_entitlement(job) else FULL
        elif not in_time:
            job.cross_zone_reason = NEEDED
        else:
            job.cross_zone_reason = SPARE
