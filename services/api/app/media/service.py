import uuid
from collections.abc import Iterable
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
# ONB-12: an RC document keeps its own 5 MB limit and its own kind.
MAX_BYTES = {"photo": 10 * MB, "video": 25 * MB, "document": 5 * MB}


def valid_size(kind: str, size: int) -> bool:
    """Photos/videos are strictly under the limit; RC documents allow 5 MB."""
    limit = MAX_BYTES[kind]
    return size > 0 and (size <= limit if kind == "document" else size < limit)
CONTENT_TYPES = {
    "photo": ("image/jpeg", "image/png", "image/heic", "image/heif", "image/webp"),
    "video": ("video/mp4", "video/quicktime", "video/3gpp", "video/x-m4v"),
    "document": ("image/jpeg", "image/png", "application/pdf"),
}
# What a customer may upload (VEH-01, ISS-04, ONB-12) and the kind each stores.
CUSTOMER_PURPOSES = {"vehicle": "photo", "complaint": "photo", "rc": "document"}
UPLOAD_WINDOW = timedelta(minutes=30)
# How long a read URL works. The screens ask again each time they load.
DOWNLOAD_WINDOW = timedelta(hours=1)
# A customer's vehicle photo is stored under this key prefix, then the vehicle
# ID. The customer upload route (WP5) follows this key shape.
VEHICLE_PHOTO_PREFIX = "vehicle"
STAGE_ORDER = {stage: i for i, stage in enumerate(STAGES)}


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
    elif not valid_size(kind, size_bytes):
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


def request_customer_upload(db: Session, store: ObjectStore, *, owner_id: uuid.UUID,
                            purpose: str, subject_id: uuid.UUID | None, content_type: str,
                            size_bytes: int) -> tuple[MediaUpload, SignedUpload]:
    """A customer's vehicle photo, complaint photo or RC document. The key
    holds the vehicle (or the login, for a complaint photo) so a read can
    find it: `vehicle/<vehicle_id>/<upload_id>` (VEHICLE_PHOTO_PREFIX)."""
    kind = CUSTOMER_PURPOSES.get(purpose)
    fields: dict[str, str] = {}
    if kind is None:
        fields["purpose"] = "Use vehicle, complaint or rc."
    elif content_type.lower() not in CONTENT_TYPES[kind]:
        fields["content_type"] = "This file format is not accepted."
    elif not valid_size(kind, size_bytes):
        fields["size_bytes"] = f"The file must be under {MAX_BYTES[kind] // MB} MB."
    if fields or kind is None:
        raise ApiError("validation_failed", "Please check the file.", 422, fields)
    upload_id = uuid.uuid4()
    upload = MediaUpload(
        id=upload_id, owner_login_id=owner_id, job_id=None, purpose=purpose, kind=kind,
        stage=None, content_type=content_type.lower(), declared_size_bytes=size_bytes,
        object_key=f"{purpose}/{subject_id or owner_id}/{upload_id}")
    db.add(upload)
    db.commit()
    signed = store.presign_upload(str(upload_id), upload.object_key, upload.content_type,
                                  utcnow() + UPLOAD_WINDOW)
    return upload, signed


def upload_urls(db: Session, store: ObjectStore, upload_ids: Iterable[str]) -> list[str]:
    """Read URLs of confirmed uploads, in the order given. Unknown ones are left out."""
    out = []
    for raw in upload_ids:
        try:
            upload = db.get(MediaUpload, uuid.UUID(str(raw)))
        except ValueError:
            continue
        if upload is not None and upload.status == STATUS_CONFIRMED:
            out.append(download_url(store, upload))
    return out


def has_confirmed(db: Session, prefix: str) -> bool:
    return db.scalar(select(MediaUpload.id).where(
        MediaUpload.object_key.like(f"{prefix}/%"),
        MediaUpload.status == STATUS_CONFIRMED).limit(1)) is not None


def confirm_upload(db: Session, store: ObjectStore, upload: MediaUpload) -> MediaUpload:
    if upload.status == STATUS_CONFIRMED:
        return upload
    size = store.size_of(upload.object_key)
    if size is None:
        raise ApiError("upload_missing", "The file has not arrived yet.", 409)
    if not valid_size(upload.kind, size):
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


# ---- Read URLs -------------------------------------------------------------------

def download_url(store: ObjectStore, upload: MediaUpload) -> str:
    """A signed, expiring URL to read a confirmed upload."""
    return store.presign_download(str(upload.id), upload.object_key, upload.content_type,
                                  utcnow() + DOWNLOAD_WINDOW)


def confirmed_proof(db: Session,
                    job_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[MediaUpload]]:
    """The confirmed proof photos and videos of these jobs: Before, During,
    then After, and by time inside a stage."""
    ids = list(job_ids)
    out: dict[uuid.UUID, list[MediaUpload]] = {i: [] for i in ids}
    if not ids:
        return out
    rows = db.scalars(
        select(MediaUpload)
        .where(MediaUpload.job_id.in_(ids), MediaUpload.purpose == "proof",
               MediaUpload.status == STATUS_CONFIRMED)
        .order_by(MediaUpload.confirmed_at, MediaUpload.id)).all()
    for row in sorted(rows, key=lambda r: STAGE_ORDER.get(r.stage or "", 9)):
        out[row.job_id].append(row)
    return out


def vehicle_photo_urls(db: Session, store: ObjectStore,
                       vehicle_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, str]:
    """The newest confirmed photo of each vehicle that has one, as a signed
    read URL. A vehicle with no photo is left out."""
    out: dict[uuid.UUID, str] = {}
    from app.customers.models import Vehicle
    for vehicle_id in set(vehicle_ids):
        vehicle = db.get(Vehicle, vehicle_id)
        explicit = db.get(MediaUpload, vehicle.photo_upload_id) \
            if vehicle and vehicle.photo_upload_id else None
        if explicit is not None and explicit.status == STATUS_CONFIRMED:
            out[vehicle_id] = download_url(store, explicit)
            continue
        row = db.scalar(
            select(MediaUpload)
            .where(MediaUpload.object_key.like(f"{VEHICLE_PHOTO_PREFIX}/{vehicle_id}/%"),
                   MediaUpload.status == STATUS_CONFIRMED)
            .order_by(MediaUpload.confirmed_at.desc()).limit(1))
        if row is not None:
            out[vehicle_id] = download_url(store, row)
    return out


def profile_photo_url(db: Session, store: ObjectStore, upload_id: uuid.UUID) -> str | None:
    upload = db.get(MediaUpload, upload_id)
    if upload is None or upload.status != STATUS_CONFIRMED:
        return None
    return download_url(store, upload)
