"""The SQL implementation of [VisitReadRepository], over the scheduling
module's `visits` and `jobs` tables. Each job also carries its confirmed proof
(from `media_uploads`, as signed read URLs), its checklist with the times, its
start and finish times and the crew member's first name."""
import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customer_reads.repository import ChecklistEntry, Job, ProofItem, Visit
from app.identity.models import Login
from app.media.service import confirmed_proof, download_url
from app.media.store import ObjectStore, get_object_store
from app.scheduling.models import Job as JobRow
from app.scheduling.models import SchedulingCrew
from app.scheduling.models import Visit as VisitRow
from app.visits.models import JobChecklistProgress, JobTiming
from app.visits.service import CHECKLISTS

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


def _visit(row: VisitRow) -> Visit:
    return Visit(id=str(row.id), vehicle_id=str(row.vehicle_id), date=row.date,
                 status=_VISIT_STATUS.get(row.status, row.status))


class SqlVisitReadRepository:
    def __init__(self, db: Session, store: ObjectStore | None = None):
        self.db = db
        self.store = store or get_object_store()

    def visits_in_range(self, vehicle_ids: Sequence[str], start: date, end: date):
        ids = _ids(vehicle_ids)
        if not ids:
            return []
        rows = self.db.scalars(
            select(VisitRow)
            .where(VisitRow.vehicle_id.in_(ids), VisitRow.date >= start,
                   VisitRow.date <= end)
            .order_by(VisitRow.date, VisitRow.id)).all()
        return [_visit(r) for r in rows]

    def history(self, vehicle_ids: Sequence[str], statuses: Sequence[str],
                limit: int, offset: int, start: date | None = None,
                end: date | None = None):
        ids = _ids(vehicle_ids)
        if not ids:
            return []
        stored = {"Missed": "Could not complete"}
        wanted = [stored.get(s, s) for s in statuses]
        query = select(VisitRow).where(VisitRow.vehicle_id.in_(ids),
                                       VisitRow.status.in_(wanted))
        if start is not None:
            query = query.where(VisitRow.date >= start)
        if end is not None:
            query = query.where(VisitRow.date <= end)
        rows = self.db.scalars(
            query.order_by(VisitRow.date.desc(), VisitRow.id.desc())
            .limit(limit).offset(offset)).all()
        return [_visit(r) for r in rows]

    def visit(self, visit_id: str):
        ids = _ids([visit_id])
        row = self.db.get(VisitRow, ids[0]) if ids else None
        return _visit(row) if row else None

    def jobs(self, visit_ids: Sequence[str]):
        ids = _ids(visit_ids)
        if not ids:
            return []
        rows = self.db.scalars(
            select(JobRow).where(JobRow.visit_id.in_(ids))
            .order_by(JobRow.start_minute, JobRow.id)).all()
        job_ids = [r.id for r in rows]
        proof = confirmed_proof(self.db, job_ids)
        timings = {t.job_id: t for t in self.db.scalars(
            select(JobTiming).where(JobTiming.job_id.in_(job_ids)))} if job_ids else {}
        ticks: dict[uuid.UUID, dict[str, datetime]] = {}
        if job_ids:
            for p in self.db.scalars(select(JobChecklistProgress)
                                     .where(JobChecklistProgress.job_id.in_(job_ids))):
                ticks.setdefault(p.job_id, {})[p.item_key] = p.checked_at
        crew_ids = {r.crew_id for r in rows if r.crew_id}
        names = {c.id: n for c, n in self.db.execute(
            select(SchedulingCrew, Login.display_name)
            .join(Login, Login.id == SchedulingCrew.login_id)
            .where(SchedulingCrew.id.in_(crew_ids)))} if crew_ids else {}
        out = []
        for r in rows:
            timing = timings.get(r.id)
            first = (names.get(r.crew_id) or "").split(" ")[0] if r.crew_id else ""
            out.append(Job(
                id=str(r.id), visit_id=str(r.visit_id), service=r.service,
                status=_JOB_STATUS.get(r.status, r.status),
                proof=[ProofItem(kind=u.kind, url=download_url(self.store, u), stage=u.stage,
                                 taken_at=u.confirmed_at) for u in proof[r.id]],
                crew_name=first or None,
                started_at=timing.started_at if timing else None,
                finished_at=timing.finished_at if timing else None,
                checklist=[ChecklistEntry(key=key, label=label,
                                          checked_at=ticks.get(r.id, {}).get(key))
                           for key, label in CHECKLISTS.get(r.service, ())]))
        return out
