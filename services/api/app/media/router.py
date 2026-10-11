import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.identity.service import User
from app.media import service
from app.media.models import STATUS_REQUESTED, MediaUpload
from app.media.store import LocalObjectStore, ObjectStore, get_object_store
from app.platform.db import get_db, utcnow
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.visits.service import visible_job

router = APIRouter(prefix="/v1/media", tags=["media"])


class UploadRequest(BaseModel):
    # "proof" (a job's photos and video), "reason" (the photo of a could-not-
    # complete) or "profile" (the crew member's own photo).
    purpose: str = "proof"
    job_id: str | None = None
    kind: str  # photo | video
    stage: str | None = None  # Before | During | After, for proof
    content_type: str
    size_bytes: int


class UploadTicket(BaseModel):
    id: str
    upload_url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime


class UploadState(BaseModel):
    id: str
    status: str
    size_bytes: int | None


def _own_upload(db: Session, user: User, upload_id: str) -> MediaUpload:
    try:
        upload = db.get(MediaUpload, uuid.UUID(upload_id))
    except ValueError:
        upload = None
    if upload is None or upload.owner_login_id != user.id:
        raise ApiError("not_found", "This upload was not found.", 404)
    return upload


@router.post("/uploads", response_model=UploadTicket, status_code=201)
def request_upload(body: UploadRequest, user: User = Depends(require_role("crew")),
                   db: Session = Depends(get_db),
                   store: ObjectStore = Depends(get_object_store)):
    job_id = None
    if body.job_id is not None:
        job_id = visible_job(db, user.id, body.job_id).id
    upload, signed = service.request_upload(
        db, store, owner_id=user.id, job_id=job_id, purpose=body.purpose, kind=body.kind,
        stage=body.stage, content_type=body.content_type, size_bytes=body.size_bytes)
    return UploadTicket(id=str(upload.id), upload_url=signed.url, method=signed.method,
                        headers=signed.headers, expires_at=utcnow() + service.UPLOAD_WINDOW)


@router.put("/local/{upload_id}", status_code=204)
async def put_local(upload_id: str, expires: int, sig: str, request: Request,
                    db: Session = Depends(get_db),
                    store: ObjectStore = Depends(get_object_store)):
    """The signed URL of the local-disk store. The signature is the only
    credential, as with an S3 pre-signed URL."""
    if not isinstance(store, LocalObjectStore):
        raise ApiError("not_found", "Not found.", 404)
    if not store.verify(upload_id, expires, sig, utcnow()):
        raise ApiError("forbidden", "This upload link is not valid.", 403)
    try:
        upload = db.get(MediaUpload, uuid.UUID(upload_id))
    except ValueError:
        upload = None
    if upload is None or upload.status != STATUS_REQUESTED:
        raise ApiError("not_found", "This upload was not found.", 404)
    data = await request.body()
    if len(data) == 0 or len(data) > service.MAX_BYTES[upload.kind]:
        raise ApiError("upload_too_large", "The file is too large.", 422)
    store.put(upload.object_key, data)
    return Response(status_code=204)


@router.post("/uploads/{upload_id}/confirm", response_model=UploadState)
def confirm(upload_id: str, user: User = Depends(require_role("crew")),
            db: Session = Depends(get_db),
            store: ObjectStore = Depends(get_object_store)):
    upload = service.confirm_upload(db, store, _own_upload(db, user, upload_id))
    return UploadState(id=str(upload.id), status=upload.status, size_bytes=upload.size_bytes)


@router.get("/uploads/{upload_id}", response_model=UploadState)
def state(upload_id: str, user: User = Depends(require_role("crew")),
          db: Session = Depends(get_db)):
    upload = _own_upload(db, user, upload_id)
    return UploadState(id=str(upload.id), status=upload.status, size_bytes=upload.size_bytes)
