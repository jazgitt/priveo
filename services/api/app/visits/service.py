"""The crew's work on jobs. Visits, jobs and their statuses belong to the
scheduling module: this reads its tables and changes a status only through
`app.scheduling.service.set_job_status`."""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import Vehicle
from app.directory import lookup
from app.directory.models import Society
from app.identity.models import Login
from app.media.models import STATUS_CONFIRMED, MediaUpload
from app.media.service import profile_photo_url, proof_counts, vehicle_photo_urls
from app.media.store import get_object_store
from app.notifications import emit  # notify hook
from app.platform.db import utcnow
from app.platform.errors import ApiError
from app.scheduling import queue, rules
from app.scheduling.models import Job, Schedule, SchedulingCrew, Visit
from app.scheduling.outcomes import visit_outcomes
from app.scheduling.service import set_job_status
from app.visits import manager as manager_checks
from app.visits import schemas as s
from app.visits.checklists import items_for_job
from app.visits.models import (
    CrewPhoto,
    JobChecklistProgress,
    JobOutcome,
    JobReassignment,
    JobTiming,
)

JOB_CLOSED = ("Completed", "Skipped", "Could not complete")

# The checklists, proof minimums and reasons are reference data the admin
# manages (ADM-CHK-01, ADM-CHK-06, ADM-CNC-01): see `app.directory.lookup`.


# ---- Who can see what ---------------------------------------------------------


def crew_of(db: Session, login_id: uuid.UUID) -> SchedulingCrew | None:
    return db.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == login_id))


def _my_crew_ids(db: Session, login_id: uuid.UUID) -> list[uuid.UUID]:
    """The crew members whose jobs this person sees: themselves, and for a
    Trainee the paired Member (CRW-SCH-10)."""
    me = crew_of(db, login_id)
    if me is None:
        return []
    ids = [me.id]
    if me.role == "Trainee" and me.paired_member_id:
        ids.append(me.paired_member_id)
    return ids


def require_manager(db: Session, login_id: uuid.UUID) -> SchedulingCrew:
    me = crew_of(db, login_id)
    if me is None or me.role != "Manager":
        raise ApiError("forbidden", "Only a Manager can do this.", 403)
    return me


def _job_row(db: Session, job_id: str) -> tuple[Job, Visit, Schedule]:
    try:
        key = uuid.UUID(job_id)
    except ValueError:
        key = None
    row = None
    if key is not None:
        row = db.execute(
            select(Job, Visit, Schedule)
            .join(Visit, Visit.id == Job.visit_id)
            .join(Schedule, Schedule.id == Visit.schedule_id)
            .where(Job.id == key)
        ).first()
    # A draft schedule is not shown to the crew (CRW-SCH-11).
    if row is None or row[2].status != "Frozen":
        raise ApiError("not_found", "This job was not found.", 404)
    return row[0], row[1], row[2]


def visible_job(db: Session, login_id: uuid.UUID, job_id: str) -> Job:
    job, _, _ = _job_row(db, job_id)
    if job.crew_id is None or job.crew_id not in _my_crew_ids(db, login_id):
        raise ApiError("not_found", "This job was not found.", 404)
    return job


def managed_job(db: Session, login_id: uuid.UUID, job_id: str) -> Job:
    """A job of the Manager's own society (CRW-MGR-01)."""
    manager = require_manager(db, login_id)
    job, _, schedule = _job_row(db, job_id)
    if schedule.society_id != manager.society_id:
        raise ApiError("not_found", "This job was not found.", 404)
    return job


# ---- Cards ---------------------------------------------------------------------


def _cards(db: Session, jobs: list[Job]) -> list[s.CrewJobCard]:
    if not jobs:
        return []
    visits = {
        v.id: v for v in db.scalars(select(Visit).where(Visit.id.in_({j.visit_id for j in jobs})))
    }
    vehicles = {
        v.id: v
        for v in db.scalars(
            select(Vehicle).where(Vehicle.id.in_({v.vehicle_id for v in visits.values()}))
        )
    }
    schedules = {
        sc.id: sc
        for sc in db.scalars(
            select(Schedule).where(Schedule.id.in_({v.schedule_id for v in visits.values()}))
        )
    }
    societies = {
        so.id: so.name
        for so in db.scalars(
            select(Society).where(Society.id.in_({sc.society_id for sc in schedules.values()}))
        )
    }
    derived = visit_outcomes(db, list(visits))
    checked: dict[uuid.UUID, int] = {}
    for (job_id,) in db.execute(
        select(JobChecklistProgress.job_id).where(
            JobChecklistProgress.job_id.in_({j.id for j in jobs})
        )
    ):
        checked[job_id] = checked.get(job_id, 0) + 1
    crew_ids = {j.crew_id for j in jobs if j.crew_id}
    names = (
        {
            c.id: n
            for c, n in db.execute(
                select(SchedulingCrew, Login.display_name)
                .join(Login, Login.id == SchedulingCrew.login_id)
                .where(SchedulingCrew.id.in_(crew_ids))
            )
        }
        if crew_ids
        else {}
    )

    photos = vehicle_photo_urls(db, get_object_store(), vehicles.keys())
    states = queue.states_for(db, jobs)

    cards = []
    for job in jobs:
        visit = visits[job.visit_id]
        vehicle = vehicles[visit.vehicle_id]
        state = states.get(job.id)
        parking = "-".join(p for p in (vehicle.parking_basement, vehicle.parking_number) if p)
        cards.append(
            s.CrewJobCard(
                id=str(job.id),
                visit_id=str(visit.id),
                visit_status=visit.status,
                visit_outcome=derived[visit.id].outcome,
                planned_services=derived[visit.id].planned,
                delivered_services=derived[visit.id].delivered,
                date=visit.date,
                service=job.service,
                status=job.status,
                vehicle=s.VehicleInfo(
                    id=str(vehicle.id),
                    registration=vehicle.registration or "",
                    make=vehicle.make,
                    model=vehicle.model,
                    category=vehicle.category,
                    photo_url=photos.get(vehicle.id),
                ),
                society=societies.get(schedules[visit.schedule_id].society_id, ""),
                parking=parking,
                start_time=rules.hhmm(job.start_minute),
                finish_by=rules.hhmm(job.finish_by_minute),
                checklist_total=len(items_for_job(db, job)),
                checklist_done=checked.get(job.id, 0),
                assigned_to=(
                    s.CrewRef(id=str(job.crew_id), name=names.get(job.crew_id, ""))
                    if job.crew_id
                    else None
                ),
                sequence=job.sequence,
                locked=bool(state and state.locked),
                current=bool(state and state.current),
            )
        )
    return cards


def _jobs_where(db: Session, *where) -> list[Job]:
    q = (
        select(Job)
        .join(Visit, Visit.id == Job.visit_id)
        .join(Schedule, Schedule.id == Visit.schedule_id)
        .where(Schedule.status == "Frozen", *where)
        .order_by(
            Visit.date,
            Job.crew_id,
            Job.sequence.is_(None),
            Job.sequence,
            Job.start_minute.is_(None),
            Job.start_minute,
            Job.service,
            Job.id,
        )
    )
    return list(db.scalars(q))


def list_jobs(db: Session, login_id: uuid.UUID, day: date | None) -> s.VisitList:
    """The crew member's own cards, for a day or (day None) all of them
    (CRW-SCH-06). Only Frozen schedules show (CRW-SCH-11)."""
    ids = _my_crew_ids(db, login_id)
    where = [Job.crew_id.in_(ids)] if ids else [Job.id.is_(None)]
    where.append(Job.status != "Skipped")  # CRW-SCH-08: a skipped job leaves the cards
    if day is not None:
        where.append(Visit.date == day)
    cards = _cards(db, _jobs_where(db, *where))
    me = crew_of(db, login_id)
    society = ""
    if me is not None:
        society = db.scalar(select(Society.name).where(Society.id == me.society_id)) or ""
    done = sum(1 for c in cards if c.status in JOB_CLOSED)
    return s.VisitList(
        date=day, society=society, total=len(cards), done=done, left=len(cards) - done, jobs=cards
    )


# ---- One job -------------------------------------------------------------------


def _progress(db: Session, job: Job) -> dict[str, JobChecklistProgress]:
    return {
        p.item_key: p
        for p in db.scalars(
            select(JobChecklistProgress).where(JobChecklistProgress.job_id == job.id)
        )
    }


def _missing(db: Session, job: Job, progress: dict, counts: dict[str, int]) -> list[str]:
    missing = []
    left = sum(1 for item in items_for_job(db, job) if item.key not in progress)
    if left:
        missing.append(f"{left} checklist item{'s' if left != 1 else ''} not checked")
    need_photos, need_videos = lookup.proof_minimums(db, job.service)
    for kind, need, have in (
        ("photo", need_photos, counts["photos"]),
        ("video", need_videos, counts["videos"]),
    ):
        if have < need:
            n = need - have
            missing.append(f"{n} more {kind}{'s' if n != 1 else ''} to upload")
    if counts["pending"]:
        missing.append(
            f"{counts['pending']} upload{'s' if counts['pending'] != 1 else ''} not confirmed yet"
        )
    return missing


def job_detail(db: Session, job: Job) -> s.JobDetail:
    progress = _progress(db, job)
    counts = proof_counts(db, job.id)
    uploads = list(
        db.scalars(
            select(MediaUpload)
            .where(MediaUpload.job_id == job.id, MediaUpload.purpose == "proof")
            .order_by(MediaUpload.created_at)
        )
    )
    outcome = db.scalar(select(JobOutcome).where(JobOutcome.job_id == job.id))
    timing = db.get(JobTiming, job.id)
    missing = _missing(db, job, progress, counts)
    photos, videos = lookup.proof_minimums(db, job.service)
    items = [(i.key, i.label) for i in items_for_job(db, job)]
    return s.JobDetail(
        job=_cards(db, [job])[0],
        checklist=[
            s.ChecklistItem(
                id=key,
                label=label,
                checked_at=progress[key].checked_at if key in progress else None,
            )
            for key, label in items
        ],
        requirements=s.Requirements(
            photos_required=photos,
            videos_required=videos,
            photos_confirmed=counts["photos"],
            videos_confirmed=counts["videos"],
            pending_uploads=counts["pending"],
        ),
        uploads=[
            s.UploadInfo(id=str(u.id), kind=u.kind, stage=u.stage, status=u.status) for u in uploads
        ],
        missing=missing,
        can_complete=job.status not in JOB_CLOSED and not missing,
        outcome=(
            s.Outcome(
                kind=outcome.kind, reason_key=outcome.reason_key, note=outcome.note, at=outcome.at
            )
            if outcome
            else None
        ),
        started_at=timing.started_at if timing else None,
        finished_at=timing.finished_at if timing else None,
    )


def _open_job(job: Job) -> None:
    """CRW-SVC-12: a closed job cannot be changed by the crew."""
    if job.status in JOB_CLOSED:
        raise ApiError("job_closed", "This job is already closed.", 409)


def _stamp(db: Session, job: Job, *, started: bool = False, finished: bool = False) -> None:
    """Records the time, without committing."""
    row = db.get(JobTiming, job.id)
    if row is None:
        row = JobTiming(job_id=job.id)
        db.add(row)
    if started and row.started_at is None:
        row.started_at = utcnow()
    if finished:
        row.finished_at = utcnow()
        row.started_at = row.started_at or row.finished_at


def start_job(db: Session, job: Job) -> Job:
    _open_job(job)
    _stamp(db, job, started=True)
    return set_job_status(db, job.id, "In progress")


def set_checked(db: Session, job: Job, item_key: str, checked: bool, login_id: uuid.UUID) -> None:
    _open_job(job)
    if item_key not in {i.key for i in items_for_job(db, job)}:
        raise ApiError("not_found", "This checklist item was not found.", 404)
    row = db.scalar(
        select(JobChecklistProgress).where(
            JobChecklistProgress.job_id == job.id, JobChecklistProgress.item_key == item_key
        )
    )
    # Ticking again keeps the first time. A Member and their Trainee see the
    # same ticks (CRW-SCH-12).
    if checked and row is None:
        db.add(JobChecklistProgress(job_id=job.id, item_key=item_key, checked_by=login_id))
    elif not checked and row is not None:
        db.delete(row)
    if job.status == "Scheduled":
        _stamp(db, job, started=True)
        # Commits the tick with the new status.
        set_job_status(db, job.id, "In progress")
    else:
        db.commit()


def complete_job(db: Session, job: Job) -> Job:
    """CRW-SVC-08: every item checked, the minimum proof confirmed, and no
    upload left waiting."""
    _open_job(job)
    missing = _missing(db, job, _progress(db, job), proof_counts(db, job.id))
    if missing:
        raise ApiError(
            "job_not_ready",
            "This job cannot be completed yet.",
            409,
            {f"missing_{i + 1}": m for i, m in enumerate(missing)},
        )
    _stamp(db, job, finished=True)
    return set_job_status(db, job.id, "Completed")


def _check_reason(db: Session, body: s.CouldNotComplete, job: Job) -> uuid.UUID | None:
    if body.reason_key not in lookup.reason_keys(db):
        raise ApiError(
            "validation_failed",
            "Please choose a reason.",
            422,
            {"reason_key": "Choose a reason from the list."},
        )
    if body.upload_id is None:
        return None
    try:
        upload = db.get(MediaUpload, uuid.UUID(body.upload_id))
    except ValueError:
        upload = None
    if (
        upload is None
        or upload.job_id != job.id
        or upload.purpose != "reason"
        or upload.status != STATUS_CONFIRMED
    ):
        raise ApiError(
            "validation_failed",
            "The photo is not ready.",
            422,
            {"upload_id": "Upload the photo first."},
        )
    return upload.id


def could_not_complete(db: Session, job: Job, body: s.CouldNotComplete, by: uuid.UUID) -> Job:
    """CRW-CNC-01 to CRW-CNC-04. The other jobs of the visit are not affected."""
    _open_job(job)
    if not body.note.strip():
        # A remark is required for every Not Completed outcome.
        raise ApiError(
            "validation_failed", "Enter a remark.", 422, {"note": "Enter a remark."}
        )
    upload_id = _check_reason(db, body, job)
    db.add(
        JobOutcome(
            job_id=job.id,
            kind="could_not_complete",
            reason_key=body.reason_key,
            note=body.note.strip(),
            upload_id=upload_id,
            by_login_id=by,
        )
    )
    _stamp(db, job, finished=True)
    return set_job_status(db, job.id, "Could not complete")


# ---- Manager --------------------------------------------------------------------


def manager_schedule(db: Session, manager: SchedulingCrew, day: date) -> s.ManagerSchedule:
    """CRW-MGR-01: the whole society's schedule, read-only, by crew member."""
    cards = _cards(
        db, _jobs_where(db, Schedule.society_id == manager.society_id, Visit.date == day)
    )
    team = list(
        db.execute(
            select(SchedulingCrew, Login.display_name)
            .join(Login, Login.id == SchedulingCrew.login_id)
            .where(SchedulingCrew.society_id == manager.society_id, SchedulingCrew.active)
            .order_by(Login.display_name)
        ).all()
    )
    by_owner: dict[str, list[s.CrewJobCard]] = {}
    unassigned = []
    for card in cards:
        if card.assigned_to is None:
            unassigned.append(card)
        else:
            by_owner.setdefault(card.assigned_to.id, []).append(card)
    crew = [
        s.TeamMember(id=str(c.id), name=name, role=c.role, jobs=by_owner.pop(str(c.id), []))
        for c, name in team
    ]
    society = db.scalar(select(Society.name).where(Society.id == manager.society_id)) or ""
    return s.ManagerSchedule(date=day, society=society, crew=crew, unassigned=unassigned)


def manager_skip(db: Session, job: Job, by: uuid.UUID) -> Job:
    """CRW-MGR-02: skipped by operations. The customer notification and the
    plan extension belong to other modules."""
    from app.visits.operations import Resolution, skip_job

    if job.status != "Could not complete":
        _open_job(job)
    return skip_job(db, job, Resolution(action="Skip"), by)


def manager_reschedule(db: Session, job: Job, by: uuid.UUID) -> Job:
    """D-02: the admin's next-day retry, for a missed Interior or Spa job. The
    audit row carries the manager's login."""
    from app.visits.operations import Resolution, locked_job, reschedule

    job = locked_job(db, job.id)
    try:
        return reschedule(
            db, job, Resolution(action="Reschedule", reason="Crew manager", note=""), by)
    except ApiError:
        db.rollback()
        raise


def manager_reassign(
    db: Session, job: Job, manager: SchedulingCrew, crew_id: str, by: uuid.UUID
) -> Job:
    """CRW-MGR-03: to another Member or Manager of the same society who is
    working that day, within their hours and with no other job at that time.
    A Trainee follows their Member without any change here."""
    _open_job(job)
    try:
        target = db.get(SchedulingCrew, uuid.UUID(crew_id))
    except ValueError:
        target = None
    manager_checks.check_assignable(db, manager, target)
    if job.status != "Scheduled":
        raise ApiError("job_in_progress", "This job has already started.", 409)
    visit = db.get(Visit, job.visit_id)
    problem = manager_checks.reassign_problem(db, job, visit, target)
    if problem is not None:
        raise ApiError(problem[0], problem[1], 409)
    manager_checks.apply_start(db, job, visit, target)
    db.add(
        JobReassignment(
            job_id=job.id, from_crew_id=job.crew_id, to_crew_id=target.id, by_login_id=by
        )
    )
    previous_crew_id = job.crew_id
    job.crew_id = target.id
    job.manual = True
    job.queue_unlocked = False
    queue.resequence_all(db, {(target.id, visit.date), (previous_crew_id, visit.date)})
    db.commit()
    emit.job_reassigned(db, job)  # notify hook
    return job


def crew_options(db: Session, manager: SchedulingCrew) -> list[s.CrewRef]:
    rows = db.execute(
        select(SchedulingCrew.id, Login.display_name)
        .join(Login, Login.id == SchedulingCrew.login_id)
        .where(
            SchedulingCrew.society_id == manager.society_id,
            SchedulingCrew.active,
            SchedulingCrew.role.in_(("Member", "Manager")),
        )
        .order_by(Login.display_name)
    ).all()
    return [s.CrewRef(id=str(i), name=n) for i, n in rows]


# ---- Profile photo ----------------------------------------------------------------
# The profile itself (name, society, role, hours) is GET /v1/crew/profile of the
# crew module. This adds the photo (CRW-PRF-02).


def photo_state(db: Session, login_id: uuid.UUID) -> s.PhotoState:
    row = db.get(CrewPhoto, login_id)
    if row is None:
        return s.PhotoState(upload_id=None, url=None)
    # A signed read URL for the profile screen (CRW-PRF-01).
    return s.PhotoState(
        upload_id=str(row.upload_id), url=profile_photo_url(db, get_object_store(), row.upload_id)
    )


def set_profile_photo(db: Session, login_id: uuid.UUID, upload_id: str) -> s.PhotoState:
    try:
        upload = db.get(MediaUpload, uuid.UUID(upload_id))
    except ValueError:
        upload = None
    if (
        upload is None
        or upload.owner_login_id != login_id
        or upload.purpose != "profile"
        or upload.status != STATUS_CONFIRMED
    ):
        raise ApiError(
            "validation_failed",
            "The photo is not ready.",
            422,
            {"upload_id": "Upload the photo first."},
        )
    row = db.get(CrewPhoto, login_id)
    if row is None:
        db.add(CrewPhoto(login_id=login_id, upload_id=upload.id))
    else:
        row.upload_id = upload.id
    db.commit()
    return photo_state(db, login_id)
