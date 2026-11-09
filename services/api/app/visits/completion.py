"""Completion status for scheduled jobs, set by the admin (P1-3, ADM-OPS-10 to ADM-OPS-12).

The statuses are the ones the crew app sets in `app.visits.service`: Completed
(complete_job), Could not complete (could_not_complete) and Deferred (a
could-not-complete reason that defers). A not-completed status needs a reason
from the could-not-complete list and a remark (ADM-CNC-07). The reason decides
Deferred, as it does for the crew: a deferring reason gives Deferred and any
other reason gives Could not complete (SCHS-31).

Works on a Draft or a Frozen schedule. The job must still be open (Scheduled or
In progress). Each change writes one directory audit row, and the customer's
service history reads the job status, so it follows the change.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory import lookup
from app.directory.service import audit
from app.identity.service import User
from app.media.store import get_object_store
from app.notifications import emit
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import hooks as scheduling_hooks
from app.scheduling import service as scheduling
from app.scheduling.models import Job
from app.visits.models import JobOutcome
from app.visits.operations import job_out, locked_job

router = APIRouter(prefix="/v1/admin/operations", tags=["operations"])

# The values the crew app sets. Do not add to this list without the crew side.
COMPLETION_STATUSES = ("Completed", "Could not complete", "Deferred")
OPEN_STATUSES = ("Scheduled", "In progress")
NOT_COMPLETED = ("Could not complete", "Deferred")

CompletionStatus = Literal["Completed", "Could not complete", "Deferred"]


class CompletionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: CompletionStatus
    # Required for every status except Completed (ADM-OPS-11). A Completed job ignores both fields.
    reason_key: str | None = Field(default=None, max_length=60)
    note: str = Field(default="", max_length=2000)


class BulkCompletionIn(CompletionIn):
    job_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


def check_outcome(db: Session, body: CompletionIn) -> tuple[str | None, str]:
    """The reason key and remark to store, or (None, "") for Completed. Refuses a
    missing remark or reason, an unknown reason, and a reason that does not match
    the status (a deferring reason is Deferred, any other is Could not complete)."""
    if body.status == "Completed":
        return None, ""
    note = body.note.strip()
    if not note:
        raise ApiError("validation_failed", "Enter a remark.", 422, {"note": "Enter a remark."})
    if not body.reason_key:
        raise ApiError("validation_failed", "Choose a reason.", 422,
                       {"reason_key": "Choose a reason from the list."})
    if body.reason_key not in lookup.reason_keys(db):
        raise ApiError("validation_failed", "Please choose a reason.", 422,
                       {"reason_key": "Choose a reason from the list."})
    defers = lookup.reason_defers(db, body.reason_key)
    if body.status == "Deferred" and not defers:
        raise ApiError("validation_failed", "Choose a reason that puts the job off.", 422,
                       {"reason_key": "This reason does not defer the job. Choose Could not complete."})
    if body.status == "Could not complete" and defers:
        raise ApiError("validation_failed", "Choose a different reason.", 422,
                       {"reason_key": "This reason puts the job off. Choose Deferred."})
    return body.reason_key, note


def apply_completion(db: Session, job: Job, status: str, reason_key: str | None,
                     note: str, actor: uuid.UUID) -> None:
    """Sets the status without committing. Callers hold the locks and commit."""
    if job.status not in OPEN_STATUSES:
        raise ApiError("job_not_open", "Choose a scheduled job.", 409)
    old = job.status
    job.status = status
    if status in NOT_COMPLETED:
        db.add(JobOutcome(job_id=job.id, kind="could_not_complete", reason_key=reason_key,
                          note=note, by_login_id=actor))
    db.flush()
    scheduling.refresh_visit_status(db, job.visit_id)
    scheduling_hooks.job_status_changed(db, job, "admin_completion")
    # Reasons by key and remarks by length only: a remark can hold personal data.
    audit(db, actor, "job", job.id, "status_set",
          {"status": [old, status], "reason_key": reason_key, "remark_length": len(note)})


@router.get("/completion-options")
def completion_options(
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """The statuses an admin can set, and the reasons with whether each defers the job."""
    return {
        "statuses": list(COMPLETION_STATUSES),
        "reasons": [
            {"key": r.key, "label": r.label, "defers": lookup.reason_defers(db, r.key)}
            for r in lookup.reasons(db)
        ],
    }


@router.post("/jobs/{job_id}/completion")
def set_completion(
    job_id: uuid.UUID,
    body: CompletionIn,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store=Depends(get_object_store),
):
    job = locked_job(db, job_id)
    try:
        reason_key, note = check_outcome(db, body)
        apply_completion(db, job, body.status, reason_key, note, user.id)
        db.commit()
    except ApiError:
        db.rollback()
        raise
    emit.job_status_changed(db, job)
    return job_out(db, job, store)


@router.post("/bulk-completion")
def bulk_completion(
    body: BulkCompletionIn,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store=Depends(get_object_store),
):
    """One status for many jobs, in one transaction. If any job is missing or already
    closed, nothing changes and the answer lists those job ids."""
    ids = list(dict.fromkeys(body.job_ids))
    try:
        reason_key, note = check_outcome(db, body)
        rows = list(db.scalars(select(Job).where(Job.id.in_(ids)).with_for_update()))
        found = {j.id for j in rows}
        missing = [str(i) for i in ids if i not in found]
        if missing:
            raise ApiError("not_found", "Some jobs do not exist. Nothing was changed.", 404,
                           {"job_ids": ", ".join(missing)})
        closed = [str(j.id) for j in rows if j.status not in OPEN_STATUSES]
        if closed:
            raise ApiError("job_not_open", "Some jobs are already closed. Nothing was changed.", 409,
                           {"job_ids": ", ".join(closed)})
        for job in rows:
            apply_completion(db, job, body.status, reason_key, note, user.id)
        db.commit()
    except ApiError:
        db.rollback()
        raise
    for job in rows:
        emit.job_status_changed(db, job)
    return [job_out(db, j, store) for j in rows]
