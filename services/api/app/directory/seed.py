"""`seed_defaults` inserts the starting reference data. It is idempotent and
safe to run at every deploy: a table that already has rows is left alone, so
anything the admin added, edited or removed stays that way.

The starter plan, add-ons and vehicle catalogue are sample data. They are
seeded only when `starter_data` is true (everywhere except prod), and the
admin creates the real ones on prod."""
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


def seed_defaults(db: Session, starter_data: bool = True) -> dict[str, int]:
    """Returns how many rows of each kind were added."""
    added = {"services": 0, "checklist_items": 0, "reasons": 0, "settings": 0,
             "plans": 0, "addons": 0, "catalogue": 0, "slots": 0}

    if not db.scalar(select(func.count()).select_from(DirectoryService)):
        for order, name in enumerate(defaults.SERVICES):
            photos, videos = defaults.PROOF_MINIMUMS[name]
            db.add(DirectoryService(name=name, duration_minutes=defaults.DURATIONS[name],
                                    min_photos=photos, min_videos=videos, sort_order=order))
            added["services"] += 1

    # Checklists: only when there are no items at all, so an admin's removed
    # or deactivated item is not brought back.
    if not db.scalar(select(func.count()).select_from(ChecklistItem)):
        for service, items in defaults.CHECKLISTS.items():
            for order, (key, label) in enumerate(items):
                db.add(ChecklistItem(service=service, key=key, label=label, sort_order=order))
                added["checklist_items"] += 1

    if not db.scalar(select(func.count()).select_from(CncReason)):
        for order, (key, label) in enumerate(defaults.REASONS):
            db.add(CncReason(key=key, label=label, sort_order=order))
            added["reasons"] += 1

    # Settings: only when the table is empty. A key with no row reads as its
    # default (lookup.setting), so a later release's new key still works.
    if not db.scalar(select(func.count()).select_from(SystemSetting)):
        for definition in settings_registry.DEFINITIONS:
            db.add(SystemSetting(key=definition.key,
                                 value=settings_registry.default_for(definition.key)))
            added["settings"] += 1

    # The invoice seller values belong to the admin (ADM-SET-04). Seed one only
    # while it has no value; a value that is there is never replaced.
    for definition in settings_registry.DEFINITIONS:
        if definition.group != "invoice":
            continue
        row = db.get(SystemSetting, definition.key)
        configured = settings_registry.default_for(definition.key)
        if row is None:
            db.add(SystemSetting(key=definition.key, value=configured))
            added["settings"] += 1
        elif not row.value.strip() and configured.strip():
            row.value = configured

    if starter_data:
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
    # Societies get their default slots (ADM-SVS-06) only while no slots exist
    # at all, so slots an admin removed are not brought back.
    if not db.scalar(select(func.count()).select_from(WorkingSlot)):
        for society in db.scalars(select(Society)):
            added["slots"] += add_default_slots(db, society)

    db.commit()
    lookup.invalidate(db)
    return added
