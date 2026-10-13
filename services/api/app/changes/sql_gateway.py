"""The scheduler-backed [ScheduleChangeGateway]: reads and changes the
`visits` and `jobs` of the scheduling module.

A skipped or paused visit has its open jobs set to Skipped, and putting it
back sets them to Scheduled again. Only days the scheduler has already planned
exist here, so a change reaches as far as the planned weeks."""
import uuid
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.gateway import ServiceDay
from app.scheduling.models import Job, Schedule, Visit
from app.scheduling.rules import visit_status

OPEN = ("Scheduled",)


class SqlScheduleChangeGateway:
    def __init__(self, db: Session):
        self.db = db

    def _visits(self, vehicle_id: uuid.UUID, start: date, end: date | None = None):
        q = select(Visit).where(Visit.vehicle_id == vehicle_id, Visit.date >= start,
                                Visit.addon_key == "")
        if end is not None:
            q = q.where(Visit.date <= end)
        return self.db.scalars(q.order_by(Visit.date)).all()

    def _jobs(self, visit_id: uuid.UUID):
        return self.db.scalars(select(Job).where(Job.visit_id == visit_id)).all()

    def _refresh(self, visit: Visit) -> None:
        self.db.flush()
        visit.status = visit_status([j.status for j in self._jobs(visit.id)])

    def upcoming_days(self, vehicle_id, start, count):
        days: dict[date, list[str]] = {}
        for visit in self._visits(vehicle_id, start):
            jobs = self._jobs(visit.id)
            days.setdefault(visit.date, []).extend(j.service for j in jobs)
        return [ServiceDay(d, tuple(s)) for d, s in sorted(days.items())[:count]]

    def is_frozen(self, vehicle_id, day):
        visit = self.db.scalars(select(Visit).where(
            Visit.vehicle_id == vehicle_id, Visit.date == day, Visit.addon_key == "")).first()
        if visit is None:
            return False
        schedule = self.db.get(Schedule, visit.schedule_id)
        return schedule is not None and schedule.status == "Frozen"

    def _set(self, vehicle_id, start: date, end: date, frm: str, to: str) -> int:
        changed = 0
        for visit in self._visits(vehicle_id, start, end):
            touched = False
            for job in self._jobs(visit.id):
                if job.status == frm:
                    job.status = to
                    touched = True
            if touched:
                self._refresh(visit)
                changed += 1
        return changed

    def skip_day(self, vehicle_id, day):
        self._set(vehicle_id, day, day, "Scheduled", "Skipped")

    def unskip_day(self, vehicle_id, day):
        self._set(vehicle_id, day, day, "Skipped", "Scheduled")

    def pause_range(self, vehicle_id, start, end):
        return self._set(vehicle_id, start, end, "Scheduled", "Skipped")

    def resume_range(self, vehicle_id, start, end):
        return self._set(vehicle_id, start, end, "Skipped", "Scheduled")

    def set_cutoff(self, vehicle_id, day: date, cutoff: time) -> None:
        minutes = cutoff.hour * 60 + cutoff.minute
        for visit in self._visits(vehicle_id, day, day):
            for job in self._jobs(visit.id):
                job.finish_by_minute = minutes
        self.db.flush()


