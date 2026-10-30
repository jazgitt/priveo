"""Today's jobs, jobs at risk, absent crew, the on-time rate and the next days' crew
capacity (Appendix A questions 15 to 17, 19, 20)."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory import lookup
from app.directory.models import Society
from app.identity.models import Login
from app.mani.contracts import ToolSpec
from app.mani.tools._base import (
    IST,
    TO_DATE,
    WEEK_START,
    ReadTool,
    capped,
    get_choice,
    get_date,
    get_int,
    get_period,
    hhmm,
    pct,
    schema,
    today_ist,
    week_start,
)
from app.scheduling import service as scheduling
from app.scheduling.models import (
    Job,
    Schedule,
    SchedulingCrew,
    SchedulingCrewException,
    Visit,
)
from app.visits.models import JobOutcome, JobTiming

OPEN = ("Scheduled", "In progress")
STATUSES = ("Scheduled", "In progress", "Completed", "Skipped", "Could not complete")


class OperationsSummary(ReadTool):
    title = "Operations summary"
    spec = ToolSpec(
        name="operations_summary",
        description=(
            "The jobs of one day (default today, India time) from frozen schedules: how many are "
            "scheduled, in progress, completed, skipped and missed (Could not complete); the "
            "societies with jobs at risk (not completed by the expected completion time, that is "
            "start time plus the service duration); and the crew absent that day with the open "
            "jobs still assigned to them."),
        parameters=schema({"date": {"type": "string", "description": "The day, YYYY-MM-DD. "
                                                                     "Default today."}}))

    def compute(self, db: Session, args: dict[str, Any], now: datetime) -> tuple[Any, str]:
        today = today_ist(now)
        day = get_date(args, "date", today)
        assert day is not None
        now_minute = now.astimezone(IST).hour * 60 + now.astimezone(IST).minute
        societies = dict(db.execute(select(Society.id, Society.name)).all())
        rows = db.execute(
            select(Job.id, Job.status, Job.service, Job.crew_id, Job.start_minute,
                   Job.duration_minutes, Job.late, Schedule.status.label("schedule_status"),
                   Schedule.society_id, JobOutcome.kind.label("outcome"))
            .join(Visit, Visit.id == Job.visit_id)
            .join(Schedule, Schedule.id == Visit.schedule_id)
            .outerjoin(JobOutcome, JobOutcome.job_id == Job.id)
            .where(Visit.date == day)).all()
        frozen = [r for r in rows if r.schedule_status == "Frozen"]
        counts = Counter(r.status for r in frozen)
        open_jobs = [r for r in frozen if r.status in OPEN]

        def at_risk(r) -> bool:
            if r.start_minute is None:
                return False  # no expected completion time yet
            if day < today:
                return True
            return day == today and r.start_minute + r.duration_minutes <= now_minute

        risky = [r for r in open_jobs if at_risk(r)]
        by_society: dict[str, Counter] = defaultdict(Counter)
        for r in risky:
            by_society[societies.get(r.society_id, "")][r.service] += 1

        # Crew away or starting late on the day, and the open jobs still on their name.
        absent_rows = db.execute(
            select(SchedulingCrewException.crew_id, SchedulingCrewException.kind,
                   SchedulingCrewException.from_minute, Login.display_name,
                   SchedulingCrew.role, SchedulingCrew.society_id)
            .join(SchedulingCrew, SchedulingCrew.id == SchedulingCrewException.crew_id)
            .join(Login, Login.id == SchedulingCrew.login_id)
            .where(SchedulingCrewException.on_date == day)
            .order_by(Login.display_name)).all()
        absent = []
        for a in absent_rows:
            mine = [r for r in open_jobs if r.crew_id == a.crew_id and (
                a.kind != "Late start" or (r.start_minute or 0) < (a.from_minute or 0))]
            absent.append({
                "crew": a.display_name, "role": a.role, "society": societies.get(a.society_id, ""),
                "kind": a.kind, "starts_from": hhmm(a.from_minute) if a.kind == "Late start" else None,
                "open_jobs_affected": len(mine),
                "jobs": [{"service": r.service, "start": hhmm(r.start_minute)} for r in
                         sorted(mine, key=lambda r: (r.start_minute or 0))[:10]],
            })
        unassigned = Counter(societies.get(r.society_id, "") for r in open_jobs if r.crew_id is None)
        data = {
            "date": day.isoformat(),
            "jobs_total": len(frozen),
            "by_status": {s: counts.get(s, 0) for s in STATUSES},
            "missed": counts.get("Could not complete", 0),
            "skipped": {"total": counts.get("Skipped", 0),
                        "by_crew_manager": sum(1 for r in frozen
                                               if r.status == "Skipped" and r.outcome == "skipped")},
            "open_without_crew": sum(unassigned.values()),
            "open_without_crew_by_society": [{"society": s, "jobs": n} for s, n in unassigned.most_common()],
            "planned_to_finish_after_cutoff": sum(1 for r in open_jobs if r.late),
            "at_risk": {
                "jobs": len(risky),
                "open_without_start_time": sum(1 for r in open_jobs if r.start_minute is None),
                "societies": [{"society": s, "jobs": sum(c.values()), "by_service": dict(c)}
                              for s, c in sorted(by_society.items(), key=lambda kv: (-sum(kv[1].values()), kv[0]))],
            },
            "crew_absent": capped(absent),
            "jobs_in_draft_schedules_not_counted": sum(1 for r in rows if r.schedule_status != "Frozen"),
        }
        summary = (
            f"{len(frozen)} jobs on {day.isoformat()}: {counts.get('Completed', 0)} completed, "
            f"{counts.get('Skipped', 0)} skipped, {counts.get('Could not complete', 0)} missed, "
            f"{len(open_jobs)} still open, {len(risky)} of them at risk. 'Missed' means Could not "
            "complete; skipped includes customer pauses and skips. Draft schedules are not counted.")
        return data, summary


class OnTimeSummary(ReadTool):
    title = "On-time completion"
    spec = ToolSpec(
        name="on_time_completion_rate",
        description=(
            "The on-time completion rate for a period (default this week so far, India time): "
            "of the completed jobs that have a customer cut-off time and a recorded finish time, "
            "the share finished at or before the cut-off."),
        parameters=schema({
            "from_date": {"type": "string", "description": "First day, YYYY-MM-DD. Default: the start of this week."},
            "to_date": TO_DATE, "week_starts_on": WEEK_START}))

    def compute(self, db: Session, args: dict[str, Any], now: datetime) -> tuple[Any, str]:
        today = today_ist(now)
        starts = get_choice(args, "week_starts_on", ("monday", "sunday"), "monday")
        first, last = get_period(args, week_start(today, starts), today)
        rows = db.execute(
            select(Visit.date, Job.finish_by_minute, JobTiming.finished_at)
            .join(Visit, Visit.id == Job.visit_id)
            .join(Schedule, Schedule.id == Visit.schedule_id)
            .outerjoin(JobTiming, JobTiming.job_id == Job.id)
            .where(Schedule.status == "Frozen", Job.status == "Completed",
                   Visit.date >= first, Visit.date <= last)).all()
        no_cutoff = no_finish = on_time = late = 0
        per_day: dict = defaultdict(lambda: [0, 0])
        for r in rows:
            if r.finish_by_minute is None:
                no_cutoff += 1
            elif r.finished_at is None:
                no_finish += 1
            else:
                cutoff = datetime.combine(r.date, datetime.min.time(), tzinfo=IST) + timedelta(
                    minutes=r.finish_by_minute)
                ok = r.finished_at <= cutoff
                on_time += ok
                late += not ok
                per_day[r.date][0] += ok
                per_day[r.date][1] += 1
        measured = on_time + late
        data = {
            "from_date": first.isoformat(), "to_date": last.isoformat(), "week_starts_on": starts,
            "completed_jobs": len(rows), "measured_jobs": measured, "on_time": on_time, "late": late,
            "on_time_rate_percent": pct(on_time, measured),
            "completed_without_cutoff_time": no_cutoff,
            "completed_without_finish_time": no_finish,
            "by_day": [{"date": d.isoformat(), "measured": v[1], "on_time": v[0],
                        "rate_percent": pct(v[0], v[1])} for d, v in sorted(per_day.items())],
        }
        summary = (
            f"On-time rate {data['on_time_rate_percent']}% over {measured} measured jobs"
            if measured else "No completed job in this period can be measured")
        summary += (f" ({first.isoformat()} to {last.isoformat()}). Only completed jobs with both a "
                    "cut-off time and a recorded finish time are measured; missed and skipped jobs "
                    "are not in the rate.")
        return data, summary


class CapacityOutlook(ReadTool):
    title = "Crew capacity outlook"
    spec = ToolSpec(
        name="crew_capacity_outlook",
        description=(
            "Crew capacity against the work due, for each housing society and each day from "
            "today for the next 7 days (1 to 14 on request). Capacity use is demand minutes over "
            "crew minutes. Tight means use from 90% to 100%; over means more than 100%, so the "
            "crew cannot meet the demand. Trainees, sick and leave days add no capacity."),
        parameters=schema({"days": {"type": "integer",
                                    "description": "How many days from today, 1 to 14. Default 7."}}))

    def compute(self, db: Session, args: dict[str, Any], now: datetime) -> tuple[Any, str]:
        today = today_ist(now)
        count = get_int(args, "days", 7, 1, 14)
        days = [today + timedelta(days=i) for i in range(count)]
        durations = lookup.durations(db)
        societies = db.execute(select(Society.id, Society.name).where(Society.active.is_(True))
                               .order_by(Society.name)).all()
        flagged: list[dict] = []
        table = []
        for society_id, name in societies:
            # Read the crew directly: the service's own loader also applies due society moves.
            crew = {c.id: c for c in db.scalars(
                select(SchedulingCrew).where(SchedulingCrew.society_id == society_id,
                                             SchedulingCrew.active.is_(True)))}
            windows = scheduling.availability(db, crew, days)
            demand = dict.fromkeys(days, 0)
            for d in scheduling.build_demand(db, society_id, days):
                if not d.skipped:
                    demand[d.day] += durations.get(d.service, d.duration)
            rows = []
            for day in days:
                cap = sum(e - s for wins in windows[day].values() for s, e in wins)
                need = demand[day]
                if need == 0:
                    status = "no_demand"
                elif need > cap:
                    status = "over"
                elif need * 100 >= cap * 90:
                    status = "tight"
                else:
                    status = "ok"
                row = {"date": day.isoformat(), "weekday": day.strftime("%A"),
                       "crew_minutes": cap, "demand_minutes": need,
                       "use_percent": pct(need, cap), "status": status}
                rows.append(row)
                if status in ("over", "tight"):
                    flagged.append({"society": name, **row})
            if any(r["demand_minutes"] or r["crew_minutes"] for r in rows):
                table.append({"society": name, "days": rows})
        data = {
            "from_date": days[0].isoformat(), "to_date": days[-1].isoformat(),
            "over_capacity_days": sum(1 for f in flagged if f["status"] == "over"),
            "tight_days": sum(1 for f in flagged if f["status"] == "tight"),
            "tight_or_over": capped(sorted(flagged, key=lambda f: (f["date"], f["society"])), 40),
            "societies": capped(table, 30),
        }
        summary = (
            f"{data['tight_days']} tight and {data['over_capacity_days']} over-capacity society-days "
            f"from {data['from_date']} to {data['to_date']}. Demand follows the scheduler's own "
            "rules for subscriptions, add-ons and open jobs; a use of None means no crew minutes.")
        return data, summary
