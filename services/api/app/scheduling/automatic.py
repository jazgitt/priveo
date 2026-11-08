"""Disabled-by-default next-period drafts; preserve existing and frozen work."""
import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.directory import lookup
from app.directory.models import Society
from app.notifications.bridge import SupportNotifier
from app.platform.clock import IST
from app.scheduling import service
from app.scheduling.models import AutomaticPlanningRun, Schedule
from app.support import alerts

log = logging.getLogger(__name__)


def next_day(day: date) -> date:
    """The day the automatic planner drafts: tomorrow. A run covers one day (ADM-SCH-09)."""
    return day + timedelta(days=1)


def run_due(db, now):
    local = now.astimezone(IST)
    at = lookup.setting(db, "schedule.auto_time")
    if not at or local.strftime("%H:%M") < at:
        return {"not_due": True, "planned": 0, "errors": 0}
    start = next_day(local.date())
    planned = errors = 0
    society_ids = list(db.scalars(select(Society.id).where(Society.active.is_(True))))
    for sid in society_ids:
        row = db.scalar(select(AutomaticPlanningRun).where(
            AutomaticPlanningRun.society_id == sid, AutomaticPlanningRun.start_date == start,
        ).with_for_update(skip_locked=True))
        if row is None:
            if db.scalar(select(AutomaticPlanningRun.id).where(
                AutomaticPlanningRun.society_id == sid, AutomaticPlanningRun.start_date == start)):
                db.rollback()
                continue  # Existing row was locked by another worker.
            row = AutomaticPlanningRun(society_id=sid, start_date=start,
                end_date=start, next_attempt_at=now)
            db.add(row)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()  # Another worker owns this target.
                continue
        if row.status in ("Done", "Existing") or row.next_attempt_at > now:
            db.rollback()
            continue
        row.status, row.attempts = "Running", row.attempts + 1
        row.next_attempt_at = now + timedelta(
            minutes=lookup.setting(db, "scheduler.retry_minutes_running"))
        rid = row.id
        db.commit()
        try:
            if row.schedule_id:
                schedule = db.get(Schedule, row.schedule_id)
                if schedule.status != "Draft":
                    row.status = "Existing"
                    db.commit()
                    continue
            else:
                existing = db.scalar(select(Schedule).where(Schedule.society_id == sid,
                                                           Schedule.start_date == start))
                if existing:
                    row.status, row.schedule_id = "Existing", existing.id
                    db.commit()
                    continue
                schedule = service.get_or_create_schedule(db, sid, start, 1)
                row.schedule_id = schedule.id
                db.commit()
            service.run_schedule(db, schedule, None)
            row.status, row.error = "Done", ""
            db.commit()
            planned += 1
        except Exception as exc:
            db.rollback()
            row = db.get(AutomaticPlanningRun, rid)
            row.status, row.error = "Error", type(exc).__name__
            row.next_attempt_at = now + timedelta(
                minutes=lookup.setting(db, "scheduler.retry_minutes_error"))
            db.commit()
            log.exception("automatic planning failed for society %s", sid)
            alerts.raise_alert(db, "planning_error", "Automatic planning failed",
                f"Society {sid}, period {start:%d-%b-%y}. Retry is scheduled; inspect the server log.",
                ref_type="schedule", ref_id=str(row.schedule_id) if row.schedule_id else None,
                push=SupportNotifier(db))
            errors += 1
    return {"planned": planned, "errors": errors, "period_start": str(start)}
