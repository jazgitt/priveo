"""The SQL implementation of [VisitReadRepository], over the scheduling
module's `visits` and `jobs` tables. Each job also carries its confirmed proof
(from `media_uploads`, as signed read URLs), its checklist with the times, its
start and finish times and the crew member's first name."""
import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customer_reads.repository import ChecklistEntry, Job, JobOutcomeEntry, ProofItem, Visit
from app.directory import lookup
from app.identity.models import Login
from app.media.models import STATUS_CONFIRMED, MediaUpload
from app.media.service import confirmed_proof, download_url
from app.media.store import ObjectStore, get_object_store
from app.scheduling.models import Job as JobRow
from app.scheduling.models import Schedule, SchedulingCrew
from app.scheduling.models import Visit as VisitRow
from app.visits.models import JobChecklistProgress, JobOutcome, JobTiming

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
    def __init__(self, db: Session, store: ObjectStore | None = None):
        self.db = db
        self.store = store or get_object_store()

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
        return self._visits(rows)

    def visit(self, visit_id: str):
        ids = _ids([visit_id])
        row = self.db.get(VisitRow, ids[0]) if ids else None
        return self._visits([row])[0] if row else None

    def _checklist(self, job: JobRow, ticked: dict[str, datetime]) -> list[ChecklistEntry]:
        """The issued definition with original tick times (ADM-CHK-05)."""
        from app.visits.checklists import items_for_job

        items = [(i.key, i.label) for i in items_for_job(self.db, job)]
        return [ChecklistEntry(key=k, label=label, checked_at=ticked.get(k))
                for k, label in items]

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
        job_ids = [r.id for r, _ in rows]
        proof = confirmed_proof(self.db, job_ids)
        timings = {t.job_id: t for t in self.db.scalars(
            select(JobTiming).where(JobTiming.job_id.in_(job_ids)))} if job_ids else {}
        outcomes = self._outcomes(job_ids)
        ticks: dict[uuid.UUID, dict[str, datetime]] = {}
        if job_ids:
            for p in self.db.scalars(select(JobChecklistProgress)
                                     .where(JobChecklistProgress.job_id.in_(job_ids))):
                ticks.setdefault(p.job_id, {})[p.item_key] = p.checked_at
        out = []
        for r, name in rows:
            timing = timings.get(r.id)
            first = (name or "").split(" ")[0] if r.crew_id else ""
            out.append(Job(
                id=str(r.id), visit_id=str(r.visit_id), service=r.service,
                source_job_id=str(r.source_job_id) if r.source_job_id else None,
                status=_JOB_STATUS.get(r.status, r.status),
                proof=[ProofItem(id=str(u.id), kind=u.kind, url=download_url(self.store, u), stage=u.stage,
                                 taken_at=u.confirmed_at) for u in proof[r.id]],
                crew_name=first or None,
                started_at=timing.started_at if timing else None,
                finished_at=timing.finished_at if timing else None,
                checklist=self._checklist(r, ticks.get(r.id, {})),
                start_minute=r.start_minute, duration_minutes=r.duration_minutes,
                finish_by_minute=r.finish_by_minute,
                addon_request_id=str(r.addon_booking_id or r.addon_request_id)
                    if r.addon_booking_id or r.addon_request_id else None,
                outcome=outcomes.get(r.id)))
        return out

    def _outcomes(self, job_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, JobOutcomeEntry]:
        """The crew's reason, note and photo for jobs that were not done."""
        if not job_ids:
            return {}
        rows = list(self.db.scalars(select(JobOutcome).where(JobOutcome.job_id.in_(job_ids))))
        out = {}
        for o in rows:
            photo = self.db.get(MediaUpload, o.upload_id) if o.upload_id else None
            label = lookup.reason_label(self.db, o.reason_key) if o.reason_key else None
            out[o.job_id] = JobOutcomeEntry(
                kind=o.kind,
                # A reason missing from every list still shows its stored key.
                reason=label or o.reason_key or "",
                note=o.note or "",
                photo_url=download_url(self.store, photo)
                if photo is not None and photo.status == STATUS_CONFIRMED else None)
        return out
