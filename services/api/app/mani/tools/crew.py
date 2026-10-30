"""Crew counts, missed and skipped jobs by crew member, and blocked crew accounts
(Appendix A questions 26 to 28). Only the crew member's name, role and society are
returned; mobile numbers (the crew sign-in ID) are never selected."""
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.directory.models import Society
from app.identity.models import Login
from app.mani.contracts import ToolSpec
from app.mani.tools._base import (
    FROM_DATE,
    TO_DATE,
    ReadTool,
    capped,
    first_of_month,
    get_int,
    get_period,
    iso,
    schema,
    today_ist,
)
from app.scheduling.models import CREW_ROLES, Job, Schedule, SchedulingCrew, Visit
from app.visits.models import JobOutcome


class CrewSummary(ReadTool):
    title = "Crew summary"
    spec = ToolSpec(
        name="crew_summary",
        description=(
            "Crew facts for the Founder: active crew by role and how many Trainees are paired "
            "with a Member; the crew with the most missed (Could not complete) or skipped-by-"
            "manager jobs in a period (default this month so far); and the crew accounts "
            "blocked after wrong passwords. No mobile numbers are returned."),
        parameters=schema({
            "from_date": FROM_DATE, "to_date": TO_DATE,
            "top": {"type": "integer", "description": "How many crew to list for missed jobs, 1 to 25. Default 10."}}))

    def compute(self, db: Session, args: dict[str, Any], now) -> tuple[Any, str]:
        today = today_ist(now)
        first, last = get_period(args, first_of_month(today), today)
        top = get_int(args, "top", 10, 1, 25)
        societies = dict(db.execute(select(Society.id, Society.name)).all())
        paired_with = aliased(SchedulingCrew)

        crew = db.execute(
            select(SchedulingCrew.id, SchedulingCrew.role, SchedulingCrew.society_id,
                   SchedulingCrew.active, SchedulingCrew.paired_member_id, Login.display_name,
                   Login.active.label("login_active"), Login.locked, Login.blocked_until,
                   Login.failed_attempts, paired_with.role.label("paired_role"))
            .join(Login, Login.id == SchedulingCrew.login_id)
            .outerjoin(paired_with, paired_with.id == SchedulingCrew.paired_member_id)).all()
        active = [c for c in crew if c.active and c.login_active]
        roles = {role: sum(1 for c in active if c.role == role) for role in CREW_ROLES}
        trainees = [c for c in active if c.role == "Trainee"]
        paired = [c for c in trainees if c.paired_member_id is not None]

        counts: dict = defaultdict(lambda: {"missed": 0, "skipped_by_manager": 0, "assigned_jobs": 0})
        for crew_id, status, outcome in db.execute(
                select(Job.crew_id, Job.status, JobOutcome.kind)
                .join(Visit, Visit.id == Job.visit_id)
                .join(Schedule, Schedule.id == Visit.schedule_id)
                .outerjoin(JobOutcome, JobOutcome.job_id == Job.id)
                .where(Schedule.status == "Frozen", Job.crew_id.is_not(None),
                       Visit.date >= first, Visit.date <= last)):
            row = counts[crew_id]
            row["assigned_jobs"] += 1
            if status == "Could not complete":
                row["missed"] += 1
            elif status == "Skipped" and outcome == "skipped":
                row["skipped_by_manager"] += 1
        by_id = {c.id: c for c in crew}
        ranked = sorted(
            ({"crew": by_id[cid].display_name, "role": by_id[cid].role,
              "society": societies.get(by_id[cid].society_id, ""),
              "missed": v["missed"], "skipped_by_manager": v["skipped_by_manager"],
              "total": v["missed"] + v["skipped_by_manager"], "assigned_jobs": v["assigned_jobs"]}
             for cid, v in counts.items() if cid in by_id and v["missed"] + v["skipped_by_manager"] > 0),
            key=lambda d: (-d["total"], -d["missed"], d["crew"]))

        blocked = [c for c in crew if c.locked or (c.blocked_until is not None and c.blocked_until > now)]
        blocked.sort(key=lambda c: c.display_name)
        data = {
            "active_crew": len(active),
            "by_role": roles,
            "inactive_or_left": len(crew) - len(active),
            "trainees": {"active": len(trainees), "paired": len(paired),
                         "not_paired": len(trainees) - len(paired)},
            "missed_and_skipped": {
                "from_date": first.isoformat(), "to_date": last.isoformat(),
                "crew_with_any": len(ranked), "top": ranked[:top],
                "note": "Skipped counts only jobs a crew Manager skipped; customer skips and "
                        "pauses are not the crew's."},
            "blocked_accounts": capped([{
                "crew": c.display_name, "role": c.role, "society": societies.get(c.society_id, ""),
                "locked_until_admin_lifts": bool(c.locked),
                "blocked_until": iso(c.blocked_until) if c.blocked_until and c.blocked_until > now else None,
                "wrong_attempts": c.failed_attempts} for c in blocked]),
        }
        summary = (
            f"{len(active)} active crew ({roles['Manager']} Managers, {roles['Member']} Members, "
            f"{roles['Trainee']} Trainees, {len(paired)} Trainees paired); {len(ranked)} crew have "
            f"missed or skipped jobs between {first.isoformat()} and {last.isoformat()}; "
            f"{len(blocked)} accounts are blocked now. Missed means Could not complete.")
        return data, summary
