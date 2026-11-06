"""Capacity: crew minutes against the minutes of work due, for each date
(ADM-CAP-01 to ADM-CAP-04). Moved out of service.py by SCHS-04; the windows
come from the window rules and the rules may add lines (see window_rules)."""
import uuid
from datetime import date
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory import lookup
from app.identity.models import Login
from app.scheduling import capacity_lines, service
from app.scheduling import windows as windows_module
from app.scheduling.models import Job, Schedule, SchedulingCrewException, Visit
from app.scheduling.window_rules import capacity_break


def _with_breaks(db: Session, crew, day: date, rows: list[dict]) -> list[dict]:
    """Adds the break to each working cleaner's availability row (SCHS-35)."""
    for row in rows:
        if row["status"] == "Off":
            continue
        found = capacity_break.visible_break(db, crew[row["crew_id"]], day)
        if found is not None:
            row["break_start"], row["break_end"] = found
    return rows


def capacity(
    db: Session, society_id: uuid.UUID, start: date, end: date, schedule: Schedule | None = None
) -> list[dict]:
    """Crew minutes against the minutes of work due, for each date (ADM-CAP-01
    to ADM-CAP-04)."""
    days = service.daterange(start, end)
    crew = service.load_crew(db, society_id)
    windows = service.availability(db, crew, days)
    day_exceptions: dict[date, dict[uuid.UUID, SchedulingCrewException]] = {d: {} for d in days}
    if crew and days:
        for ex in db.execute(
            select(SchedulingCrewException).where(
                SchedulingCrewException.crew_id.in_(list(crew)),
                SchedulingCrewException.on_date.in_(days),
            )
        ).scalars():
            day_exceptions[ex.on_date][ex.crew_id] = ex
    names = {
        row.id: row.display_name
        for row in db.execute(
            select(Login).where(Login.id.in_([c.login_id for c in crew.values()]))
        ).scalars()
    }
    demand_minutes = dict.fromkeys(days, 0)
    lines: dict[date, dict[tuple[str, str], list[int]]] = {day: {} for day in days}
    durations = lookup.durations(db)
    for d in service.build_demand(db, society_id, days):
        if d.skipped:
            continue
        minutes = durations.get(d.service, d.duration)
        demand_minutes[d.day] += minutes
        source = "Add-on" if (d.addon_request_id or d.addon_booking_id) else "Subscription"
        line = lines[d.day].setdefault((d.service, source), [0, 0])
        line[0] += 1
        line[1] += minutes
    for day in days:
        for extra in windows_module.capacity_lines(db, society_id, day):
            line = lines[day].setdefault((extra["service"], extra["source"]), [0, 0])
            line[0] += extra["jobs"]
            line[1] += extra["minutes"]
            demand_minutes[day] += extra["minutes"]
    # What capacity counts: the windows minus the break (SCHR-BRK-08, version 2 only).
    usable = {
        day: {cid: wins for cid, wins in
              ((cid, windows_module.capacity_windows(db, crew[cid], day, w))
               for cid, w in windows[day].items()) if wins}
        for day in days
    }
    scheduled = dict.fromkeys(days, 0)
    busy: dict[date, dict[uuid.UUID, list[tuple[int, int]]]] = {day: {} for day in days}
    if schedule is not None:
        rows = db.execute(
            select(Visit.date, Job.duration_minutes, Job.crew_id, Job.start_minute)
            .join(Job, Job.visit_id == Visit.id)
            .where(
                Visit.schedule_id == schedule.id, Job.crew_id.is_not(None), Job.status != "Skipped"
            )
        ).all()
        for day, minutes, crew_id, start in rows:
            if day in scheduled:
                scheduled[day] += minutes
                if start is not None:
                    busy[day].setdefault(crew_id, []).append((start, start + minutes))
    out = []
    for day in days:
        cap = sum(e - s for wins in usable[day].values() for s, e in wins)
        break_minutes = (sum(e - s for wins in windows[day].values() for s, e in wins) - cap)
        extra = capacity_lines.day_fields(
            db, society_id, day, SimpleNamespace(crew=crew, windows=usable[day], busy=busy[day]))
        crew_lines = [
            {
                "name": names.get(crew[cid].login_id, ""),
                "role": crew[cid].role,
                "minutes": sum(e - s for s, e in wins),
                "slots": ", ".join(f"{s // 60:02d}:{s % 60:02d}-{e // 60:02d}:{e % 60:02d}"
                                   for s, e in wins),
            }
            for cid, wins in usable[day].items()
        ]
        crew_lines.sort(key=lambda c: c["name"])
        out.append(
            {
                "date": day,
                "crew": crew_lines,
                "availability": _with_breaks(
                    db, crew, day, service.day_availability(crew, windows[day], day_exceptions[day], day)),
                "demand": [
                    {"service": svc_name, "source": source, "jobs": n, "minutes": m}
                    for (svc_name, source), (n, m) in sorted(lines[day].items())
                ],
                "capacity_minutes": cap,
                "demand_minutes": demand_minutes[day],
                "scheduled_minutes": scheduled[day],
                "over_capacity": demand_minutes[day] > cap,
                "break_minutes": break_minutes,
                "early_band_free_minutes": extra.get("early_band_free_minutes", 0),
            }
        )
    return out
