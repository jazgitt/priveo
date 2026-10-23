import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow


class FeatureFlag(Base):
    """Whether one feature (a key in `registry.FLAGS`) is on. A key with no row is on."""

    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(48), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, onupdate=utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("logins.id"))
