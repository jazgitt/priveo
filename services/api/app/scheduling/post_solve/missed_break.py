"""Missed break flag (SCHR-BRK-04): after a day is solved, every cleaner whose
planned work overlaps their break gets a finding `missed_break` that names the
cleaner, the date and the reason."""
from __future__ import annotations

from sqlalchemy import select

from app.identity.models import Login
from app.scheduling import breaks
from app.scheduling.models import SchedulingCrew

ORDER = 60
CODE = "missed_break"
REASON_EXTERIOR = "Exterior work needed that time."
REASON_HAND = "A job placed by hand covers the break."
REASON_OTHER = "The job could not go to another time."


def _reason(job) -> str:
    if job.manual:
        return REASON_HAND
    return REASON_EXTERIOR if job.service == "Cleaning-External" else REASON_OTHER


def after_solve(ctx, day, items, result) -> None:
    by_crew: dict = {}
    for job, _visit in items:
        if job.crew_id is not None and job.start_minute is not None and job.status != "Skipped":
            by_crew.setdefault(job.crew_id, []).append(job)
    for crew_id, jobs in by_crew.items():
        crew = ctx.db.get(SchedulingCrew, crew_id)
        brk = breaks.effective_break(ctx.db, crew, day) if crew else None
        if brk is None:
            continue
        hit = sorted(
            (j for j in jobs
             if j.start_minute < brk.end_minute and j.start_minute + j.duration_minutes > brk.start_minute),
            key=lambda j: (j.start_minute, str(j.id)))
        if not hit:
            continue
        name = ctx.db.scalar(select(Login.display_name).where(Login.id == crew.login_id)) or str(crew_id)
        ctx.add_finding(CODE, f"{name}, {day:%d-%b-%y}: {_reason(hit[0])}", hit[0].id)
