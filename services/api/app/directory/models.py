import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UtcDateTime, utcnow

DEFAULT_BASEMENTS = ["B1", "B2", "B3", "B4"]  # ONB-13


class Society(Base):
    """A housing society that Priveo serves (ADM-REF-01)."""

    __tablename__ = "societies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    sector: Mapped[str] = mapped_column(String(80), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # The basements a customer can choose from (ONB-13).
    parking_basements: Mapped[list] = mapped_column(
        JSON, default=lambda: list(DEFAULT_BASEMENTS))


class Plan(Base):
    """A subscription plan (ADM-SET-01). Prices are whole rupees, GST included."""

    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    monthly_price_rupees: Mapped[int] = mapped_column(Integer)
    list_price_rupees: Mapped[int | None] = mapped_column(Integer)
    includes_interior: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # The inclusions shown on the review screen (PAY-01, PAY-02).
    inclusions: Mapped[list] = mapped_column(JSON, default=list)
    # A short badge such as "Founding member" (PAY-01). Empty for none.
    badge: Mapped[str] = mapped_column(String(40), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class VehicleCatalogueEntry(Base):
    """One make, model and variant with its category (ADM-REF-03)."""

    __tablename__ = "vehicle_catalogue"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    make: Mapped[str] = mapped_column(String(60), index=True)
    model: Mapped[str] = mapped_column(String(80))
    variant: Mapped[str] = mapped_column(String(80), default="")
    category: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DirectoryService(Base):
    """One of the three services (ADM-SVS-01). The set is fixed. The admin
    edits the duration (ADM-SVS-09) and the proof minimums (ADM-CHK-06)."""

    __tablename__ = "directory_services"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(24), unique=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    min_photos: Mapped[int] = mapped_column(Integer, default=2)
    min_videos: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class WorkingSlot(Base):
    """A start and an end time on chosen weekdays for one service in one
    society (ADM-SVS-02, ADM-SVS-03). Minutes after midnight; the end may be
    1440 (midnight)."""

    __tablename__ = "working_slots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    society_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("societies.id"), index=True)
    service: Mapped[str] = mapped_column(String(24))
    start_minute: Mapped[int] = mapped_column(Integer)
    end_minute: Mapped[int] = mapped_column(Integer)
    # Weekday numbers, 0 is Monday.
    days: Mapped[list] = mapped_column(JSON)


class ChecklistItem(Base):
    """An item of a service's checklist (ADM-CHK-01 to ADM-CHK-05). `key` is
    what a visit stores and never changes when the label is renamed."""

    __tablename__ = "checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    service: Mapped[str] = mapped_column(String(24), index=True)
    key: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CncReason(Base):
    """A could-not-complete reason (ADM-CNC-01). Past records keep the key."""

    __tablename__ = "cnc_reasons"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SystemSetting(Base):
    """A setting by key. The value is text; its type and rules are in
    `app.directory.settings_registry`."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))


class AddonCatalogueItem(Base):
    """An add-on the customer can buy (ADM-ADD-01). Prices are whole rupees,
    GST included."""

    __tablename__ = "addon_catalogue"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # The service whose job this add-on creates (a name in `directory_services`).
    service: Mapped[str] = mapped_column(String(24))
    price_rupees: Mapped[int] = mapped_column(Integer)
    list_price_rupees: Mapped[int | None] = mapped_column(Integer)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class DirectoryAudit(Base):
    """Who changed what in the reference data, and when."""

    __tablename__ = "directory_audit"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    at: Mapped[datetime] = mapped_column(UtcDateTime, default=utcnow, index=True)
    admin_login_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("logins.id"))
    entity: Mapped[str] = mapped_column(String(24), index=True)
    entity_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))
    # {field: [old, new]} for an update, the new row for a create.
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
