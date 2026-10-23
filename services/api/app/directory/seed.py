"""`seed_defaults` inserts the starting reference data. It is idempotent: it
adds only what is missing and never changes a row the admin has edited, so it
is safe to run at every start."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.directory import defaults, lookup, settings_registry
from app.directory.models import (
    AddonCatalogueItem,
    ChecklistItem,
    CncReason,
    DirectoryService,
    Plan,
    Society,
    SystemSetting,
    VehicleCatalogueEntry,
    WorkingSlot,
)


def add_default_slots(db: Session, society: Society) -> int:
    """The default working slots of a new society (ADM-SVS-05, ADM-SVS-06)."""
    for service, (start, end) in defaults.DEFAULT_SLOT_WINDOWS.items():
        db.add(WorkingSlot(society_id=society.id, service=service, start_minute=start,
                           end_minute=end, days=list(range(7))))
    return len(defaults.DEFAULT_SLOT_WINDOWS)


def seed_defaults(db: Session) -> dict[str, int]:
    """Returns how many rows of each kind were added."""
    added = {"services": 0, "checklist_items": 0, "reasons": 0, "settings": 0,
             "plans": 0, "addons": 0, "catalogue": 0, "slots": 0}

    existing = set(db.scalars(select(DirectoryService.name)))
    for order, name in enumerate(defaults.SERVICES):
        if name not in existing:
            photos, videos = defaults.PROOF_MINIMUMS[name]
            db.add(DirectoryService(name=name, duration_minutes=defaults.DURATIONS[name],
                                    min_photos=photos, min_videos=videos, sort_order=order))
            added["services"] += 1

    # Checklists: only a service with no items at all, so an admin's
    # deactivated item is not brought back.
    for service, items in defaults.CHECKLISTS.items():
        has_any = db.scalar(select(func.count()).select_from(ChecklistItem)
                            .where(ChecklistItem.service == service))
        if not has_any:
            for order, (key, label) in enumerate(items):
                db.add(ChecklistItem(service=service, key=key, label=label, sort_order=order))
                added["checklist_items"] += 1

    if not db.scalar(select(func.count()).select_from(CncReason)):
        for order, (key, label) in enumerate(defaults.REASONS):
            db.add(CncReason(key=key, label=label, sort_order=order))
            added["reasons"] += 1

    stored = set(db.scalars(select(SystemSetting.key)))
    for definition in settings_registry.DEFINITIONS:
        if definition.key not in stored:
            db.add(SystemSetting(key=definition.key,
                                 value=settings_registry.default_for(definition.key)))
            added["settings"] += 1
        elif definition.group == "invoice":
            row = db.get(SystemSetting, definition.key)
            configured = settings_registry.default_for(definition.key)
            if "placeholder" in row.value.lower() and "placeholder" not in configured.lower():
                row.value = configured  # Explicit seed replaces mock supplier configuration only.

    if db.scalar(select(Plan).where(Plan.name == defaults.PLAN["name"])) is None:
        db.add(Plan(code="PLN-0001", **defaults.PLAN))
        added["plans"] += 1

    if db.scalar(select(AddonCatalogueItem).where(
            AddonCatalogueItem.name == defaults.ADDON["name"])) is None:
        db.add(AddonCatalogueItem(code="ADN-0001", **defaults.ADDON))
        added["addons"] += 1

    # S-08: priced and activated by the admin later; never touched once present.
    from app.directory.service import next_code
    for extra in defaults.EXTRA_ADDONS:
        if db.scalar(select(AddonCatalogueItem).where(
                func.lower(AddonCatalogueItem.name) == extra["name"].lower())) is None:
            db.add(AddonCatalogueItem(
                code=next_code(db, AddonCatalogueItem, "ADN"), **extra))
            db.flush()
            added["addons"] += 1

    have = {(e.make.lower(), e.model.lower(), e.variant.lower())
            for e in db.scalars(select(VehicleCatalogueEntry))}
    for make, model, category in defaults.CATALOGUE_MODELS:
        for variant in defaults.CATALOGUE_VARIANTS:
            if (make.lower(), model.lower(), variant.lower()) not in have:
                db.add(VehicleCatalogueEntry(make=make, model=model, variant=variant,
                                             category=category))
                added["catalogue"] += 1

    db.flush()
    # A society that has no slots at all gets the defaults (ADM-SVS-06).
    with_slots = set(db.scalars(select(WorkingSlot.society_id).distinct()))
    for society in db.scalars(select(Society)):
        if society.id not in with_slots:
            added["slots"] += add_default_slots(db, society)

    db.commit()
    lookup.invalidate(db)
    return added
