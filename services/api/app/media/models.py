import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

import app.visits.models  # noqa: F401  (the jobs table this one links to)
from app.platform.db import Base, UtcDateTime, utcnow

PURPOSES = ("proof", "reason", "profile")
KINDS = ("photo", "video")
STAGES = ("Before", "During", "After")

STATUS_REQUESTED = "requested"
STATUS_CONFIRMED = "confirmed"


class MediaUpload(Base):
    """A photo or video the crew member sent, or is about to send. It becomes
    `confirmed` once the file is in the store and its size is checked."""

    __tablename__ = "media_uploads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_login_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("logins.id"), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("jobs.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(10))  # proof | reason | profile
    kind: Mapped[str] = mapped_column(String(8))  # photo | video
    stage: Mapped[str | None] = mapped_column(String(8))  # Before | During | After
    content_type: Mapped[str] = mapped_column(String(60))
    declared_size_bytes: Mapped[int] = mapped_column(Integer)
    object_key: Mapped[str] = mapped_column(String(200), unique=True)
    status: Mapped[str] = mapped_column(String(10), default=STATUS_REQUESTED)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
