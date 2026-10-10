import uuid

from sqlalchemy import Boolean, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base


class Society(Base):
    """A housing society that Priveo serves (ADM-REF-01)."""

    __tablename__ = "societies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    sector: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Plan(Base):
    """A subscription plan (ADM-SET-01). Prices are whole rupees, GST included."""

    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    monthly_price_rupees: Mapped[int] = mapped_column(Integer)
    list_price_rupees: Mapped[int | None] = mapped_column(Integer)
    includes_interior: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
