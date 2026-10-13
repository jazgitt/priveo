"""Small reads of the reference data for other modules. Each takes the
caller's database session. Until the admin has saved something, or the seed
has run, they return the same values the code used to hard-code, so a module
can switch to them with no change in behaviour.

Settings are cached for a short time for each database engine. A write
through the directory API clears the cache at once; `invalidate()` clears it
by hand (tests that change `system_settings` directly call it).
"""
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from weakref import WeakKeyDictionary

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory import defaults, settings_registry
from app.directory.models import (
    DEFAULT_BASEMENTS,
    AddonCatalogueItem,
    ChecklistItem,
    CncReason,
    DirectoryService,
    Society,
    SystemSetting,
    VehicleCatalogueEntry,
    WorkingSlot,
)

CACHE_SECONDS = 30.0
# Tests replace the clock to check the expiry.
_clock: Callable[[], float] = time.monotonic
_lock = threading.Lock()
# engine -> (loaded at, {key: stored text}). Keyed by engine so two databases
# (or two tests) never share values.
_cache: "WeakKeyDictionary[Any, tuple[float, dict[str, str]]]" = WeakKeyDictionary()


def _engine(db: Session):
    bind = db.get_bind()
    return getattr(bind, "engine", bind)


def invalidate(db: Session | None = None) -> None:
    """Forget cached settings: for one database, or for all."""
    with _lock:
        if db is None:
            _cache.clear()
        else:
            _cache.pop(_engine(db), None)


def _stored(db: Session) -> dict[str, str]:
    engine = _engine(db)
    now = _clock()
    with _lock:
        hit = _cache.get(engine)
        if hit is not None and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    values = {row.key: row.value for row in db.scalars(select(SystemSetting))}
    with _lock:
        _cache[engine] = (now, values)
    return values


def setting(db: Session, key: str) -> Any:
    """The typed value of a setting: an int for whole numbers, else text.
    Raises KeyError for a key that does not exist."""
    definition = settings_registry.BY_KEY[key]
    stored = _stored(db).get(key)
    if stored is None:
        stored = settings_registry.default_for(key)
    try:
        return settings_registry.typed(definition, stored)
    except ValueError:
        return settings_registry.typed(definition, str(definition.default))


def all_settings(db: Session) -> dict[str, Any]:
    return {d.key: setting(db, d.key) for d in settings_registry.DEFINITIONS}


def unfreeze_code(db: Session) -> str:
    return setting(db, "schedule.unfreeze_code")


# ---- services, checklists, reasons ---------------------------------------------

@dataclass(frozen=True)
class ChecklistEntry:
    key: str
    label: str


@dataclass(frozen=True)
class ReasonEntry:
    key: str
    label: str


def durations(db: Session) -> dict[str, int]:
    """Minutes of crew time for each service (ADM-SVS-09)."""
    out = dict(defaults.DURATIONS)
    for row in db.scalars(select(DirectoryService)):
        out[row.name] = row.duration_minutes
    return out


def duration_minutes(db: Session, service: str) -> int:
    return durations(db)[service]


def proof_minimums(db: Session, service: str) -> tuple[int, int]:
    """(photos, videos) the crew must upload for a service (ADM-CHK-06)."""
    row = db.scalar(select(DirectoryService).where(DirectoryService.name == service))
    if row is not None:
        return row.min_photos, row.min_videos
    return defaults.PROOF_MINIMUMS.get(service, (0, 0))


def checklist_for(db: Session, service: str) -> list[ChecklistEntry]:
    """The active items of a service's checklist, in order (ADM-CHK-01)."""
    rows = list(db.scalars(
        select(ChecklistItem).where(ChecklistItem.service == service)
        .order_by(ChecklistItem.sort_order, ChecklistItem.key)))
    if not rows:
        return [ChecklistEntry(k, label) for k, label in defaults.CHECKLISTS.get(service, ())]
    return [ChecklistEntry(r.key, r.label) for r in rows if r.active]


def checklist_label(db: Session, service: str, key: str) -> str | None:
    """The label of an item, active or not, so a finished visit stays
    readable (ADM-CHK-05)."""
    row = db.scalar(select(ChecklistItem).where(
        ChecklistItem.service == service, ChecklistItem.key == key))
    if row is not None:
        return row.label
    return dict(defaults.CHECKLISTS.get(service, ())).get(key)


def reasons(db: Session) -> list[ReasonEntry]:
    """The active could-not-complete reasons, in order (ADM-CNC-01)."""
    rows = list(db.scalars(select(CncReason).order_by(CncReason.sort_order, CncReason.key)))
    if not rows:
        return [ReasonEntry(k, label) for k, label in defaults.REASONS]
    return [ReasonEntry(r.key, r.label) for r in rows if r.active]


def reason_keys(db: Session) -> set[str]:
    return {r.key for r in reasons(db)}


def reason_label(db: Session, key: str) -> str | None:
    """The label of a reason, active or not (past records keep it)."""
    row = db.scalar(select(CncReason).where(CncReason.key == key))
    if row is not None:
        return row.label
    return dict(defaults.REASONS).get(key)


# ---- money, societies, catalogue ------------------------------------------------

def addon_price(db: Session, service: str = "Deep Spa") -> tuple[int, int | None]:
    """(price, struck-through list price) in rupees of the active add-on that
    books `service` (ADM-ADD-01). Falls back to the MONEY_* configuration."""
    row = db.scalar(
        select(AddonCatalogueItem).where(
            AddonCatalogueItem.service == service, AddonCatalogueItem.active.is_(True))
        .order_by(AddonCatalogueItem.sort_order, AddonCatalogueItem.name))
    if row is not None:
        return row.price_rupees, row.list_price_rupees
    from app.billing.config import get_money_settings
    money = get_money_settings()
    return money.deep_spa_price_rupees, money.deep_spa_list_price_rupees


def society_basements(db: Session, society_id: uuid.UUID) -> list[str]:
    society = db.get(Society, society_id)
    return list(society.parking_basements) if society else list(DEFAULT_BASEMENTS)


def working_slots(db: Session, society_id: uuid.UUID,
                  service: str | None = None) -> list[WorkingSlot]:
    query = select(WorkingSlot).where(WorkingSlot.society_id == society_id)
    if service:
        query = query.where(WorkingSlot.service == service)
    return list(db.scalars(query.order_by(
        WorkingSlot.service, WorkingSlot.start_minute)))


def category_for(db: Session, make: str, model: str, variant: str = "") -> str | None:
    """The vehicle category of an active catalogue entry (ONB-11)."""
    rows = db.scalars(select(VehicleCatalogueEntry).where(
        VehicleCatalogueEntry.active.is_(True))).all()
    make, model, variant = make.strip().lower(), model.strip().lower(), variant.strip().lower()
    best = None
    for r in rows:
        if r.make.lower() == make and r.model.lower() == model:
            if r.variant.lower() == variant:
                return r.category
            best = best or r.category
    return best
