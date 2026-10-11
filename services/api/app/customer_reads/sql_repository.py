"""The SQL implementation of [VisitReadRepository], over the scheduling
module's `visits` and `jobs` tables. Proof (photos and video) joins in when the
media tables arrive."""
import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customer_reads.repository import Job, Visit
from app.identity.models import Login
from app.scheduling.models import Job as JobRow
from app.scheduling.models import Schedule, SchedulingCrew
from app.scheduling.models import Visit as VisitRow

# The scheduler's job statuses as the customer screens name them.
_JOB_STATUS = {
    "Scheduled": "Pending",
    "In progress": "In progress",
    "Completed": "Done",
    "Skipped": "Skipped",
    "Could not complete": "Missed",
}
_VISIT_STATUS = {"Could not complete": "Missed"}


def _ids(values: Sequence[str]) -> list[uuid.UUID]:
    out = []
    for value in values:
        try:
            out.append(uuid.UUID(str(value)))
        except ValueError:
            continue
    return out


def _visit(row: VisitRow, frozen: bool = False) -> Visit:
    return Visit(id=str(row.id), vehicle_id=str(row.vehicle_id), date=row.date,
                 status=_VISIT_STATUS.get(row.status, row.status), frozen=frozen)


class SqlVisitReadRepository:
    def __init__(self, db: Session):
        self.db = db

    def _visits(self, rows: Sequence[VisitRow]) -> list[Visit]:
        """The visits, each with whether its schedule is frozen."""
        schedule_ids = {r.schedule_id for r in rows}
        frozen = set()
        if schedule_ids:
            frozen = set(self.db.scalars(select(Schedule.id).where(
                Schedule.id.in_(schedule_ids), Schedule.status == "Frozen")))
        return [_visit(r, r.schedule_id in frozen) for r in rows]

    def visits_in_range(self, vehicle_ids: Sequence[str], start: date, end: date):
        ids = _ids(vehicle_ids)
        if not ids:
            return []
        rows = self.db.scalars(
            select(VisitRow)
            .where(VisitRow.vehicle_id.in_(ids), VisitRow.date >= start,
                   VisitRow.date <= end)
            .order_by(VisitRow.date, VisitRow.id)).all()
        return self._visits(rows)

    def history(self, vehicle_ids: Sequence[str], statuses: Sequence[str],
                limit: int, offset: int):
        ids = _ids(vehicle_ids)
        if not ids:
            return []
        stored = {"Missed": "Could not complete"}
        wanted = [stored.get(s, s) for s in statuses]
        rows = self.db.scalars(
            select(VisitRow)
            .where(VisitRow.vehicle_id.in_(ids), VisitRow.status.in_(wanted))
            .order_by(VisitRow.date.desc(), VisitRow.id.desc())
            .limit(limit).offset(offset)).all()
        return self._visits(rows)

    def visit(self, visit_id: str):
        ids = _ids([visit_id])
        row = self.db.get(VisitRow, ids[0]) if ids else None
        return self._visits([row])[0] if row else None

    def jobs(self, visit_ids: Sequence[str]):
        ids = _ids(visit_ids)
        if not ids:
            return []
        rows = self.db.execute(
            select(JobRow, Login.display_name)
            .outerjoin(SchedulingCrew, JobRow.crew_id == SchedulingCrew.id)
            .outerjoin(Login, SchedulingCrew.login_id == Login.id)
            .where(JobRow.visit_id.in_(ids))
            .order_by(JobRow.start_minute, JobRow.id)).all()
        return [Job(id=str(r.id), visit_id=str(r.visit_id), service=r.service,
                    status=_JOB_STATUS.get(r.status, r.status),
                    crew_name=name if r.crew_id is not None else None,
                    start_minute=r.start_minute, duration_minutes=r.duration_minutes,
                    finish_by_minute=r.finish_by_minute,
                    addon_request_id=str(r.addon_request_id) if r.addon_request_id else None)
                for r, name in rows]
