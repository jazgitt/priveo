import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.media.models import (
    KINDS,
    PURPOSES,
    STAGES,
    STATUS_CONFIRMED,
    STATUS_REQUESTED,
    MediaUpload,
)
from app.media.store import ObjectStore, SignedUpload
from app.platform.db import utcnow
from app.platform.errors import ApiError

MB = 1024 * 1024
# CRW-SVC-06, rule 17 of the customer file: photos under 10 MB, videos under 25 MB.
MAX_BYTES = {"photo": 10 * MB, "video": 25 * MB}
CONTENT_TYPES = {
    "photo": ("image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"),
    "video": ("video/mp4", "video/quicktime", "video/3gpp", "video/x-m4v"),
}
UPLOAD_WINDOW = timedelta(minutes=30)


def request_upload(db: Session, store: ObjectStore, *, owner_id: uuid.UUID,
                   job_id: uuid.UUID | None, purpose: str, kind: str, stage: str | None,
                   content_type: str, size_bytes: int) -> tuple[MediaUpload, SignedUpload]:
    fields: dict[str, str] = {}
    if purpose not in PURPOSES:
        fields["purpose"] = "Use proof, reason or profile."
    if kind not in KINDS:
        fields["kind"] = "Use photo or video."
    elif content_type.lower() not in CONTENT_TYPES[kind]:
        fields["content_type"] = "This file format is not accepted."
    elif size_bytes <= 0 or size_bytes > MAX_BYTES[kind]:
        limit = MAX_BYTES[kind] // MB
        fields["size_bytes"] = f"A {kind} must be under {limit} MB."
    if purpose == "proof" and stage not in STAGES:
        fields["stage"] = "Use Before, During or After."
    if purpose == "profile" and kind != "photo":
        fields["kind"] = "A profile picture is a photo."
    if purpose in ("proof", "reason") and job_id is None:
        fields["job_id"] = "A job is needed."
    if fields:
        raise ApiError("validation_failed", "Please check the file.", 422, fields)

    upload_id = uuid.uuid4()
    upload = MediaUpload(
        id=upload_id, owner_login_id=owner_id, job_id=job_id, purpose=purpose, kind=kind,
        stage=stage if purpose == "proof" else None, content_type=content_type.lower(),
        declared_size_bytes=size_bytes, object_key=f"{purpose}/{upload_id}")
    db.add(upload)
    db.commit()
    signed = store.presign_upload(str(upload_id), upload.object_key, upload.content_type,
                                  utcnow() + UPLOAD_WINDOW)
    return upload, signed


def confirm_upload(db: Session, store: ObjectStore, upload: MediaUpload) -> MediaUpload:
    if upload.status == STATUS_CONFIRMED:
        return upload
    size = store.size_of(upload.object_key)
    if size is None:
        raise ApiError("upload_missing", "The file has not arrived yet.", 409)
    if size <= 0 or size > MAX_BYTES[upload.kind]:
        raise ApiError("upload_too_large", "The file is too large.", 422)
    upload.status = STATUS_CONFIRMED
    upload.size_bytes = size
    upload.confirmed_at = utcnow()
    db.commit()
    return upload


def proof_counts(db: Session, job_id: uuid.UUID) -> dict[str, int]:
    """Confirmed photos and videos of a job, and uploads asked for but not yet
    confirmed."""
    # A request older than its upload window can no longer be used, so it
    # does not hold the job back. The phone asks again.
    fresh = utcnow() - UPLOAD_WINDOW
    rows = db.execute(
        select(MediaUpload.kind, MediaUpload.status, func.count())
        .where(MediaUpload.job_id == job_id, MediaUpload.purpose == "proof",
               (MediaUpload.status == STATUS_CONFIRMED) | (MediaUpload.created_at > fresh))
        .group_by(MediaUpload.kind, MediaUpload.status)).all()
    counts = {"photos": 0, "videos": 0, "pending": 0}
    for kind, status, n in rows:
        if status == STATUS_CONFIRMED:
            counts["photos" if kind == "photo" else "videos"] += n
        elif status == STATUS_REQUESTED:
            counts["pending"] += n
    return counts
