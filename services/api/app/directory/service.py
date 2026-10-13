"""Admin changes to the reference data. Every change is audited in
`directory_audit` with the admin and the time."""
import re
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
from app.customers.models import Customer, Subscription, Vehicle
from app.directory import defaults, lookup, settings_registry
from app.directory.models import (
    DEFAULT_BASEMENTS,
    AddonCatalogueItem,
    ChecklistItem,
    CncReason,
    DirectoryAudit,
    DirectoryService,
    Plan,
    Society,
    SystemSetting,
    VehicleCatalogueEntry,
    WorkingSlot,
)
from app.directory.seed import add_default_slots
from app.identity.models import Login
from app.platform.db import utcnow
from app.platform.errors import ApiError

LIVE_SUBSCRIPTION = ("Active", "Activating")


def invalid(field: str, message: str) -> ApiError:
    return ApiError("validation_failed", "Please check the details.", 422, {field: message})


def audit(db: Session, admin_id: uuid.UUID | None, entity: str, entity_id: Any,
          action: str, detail: dict | None = None) -> None:
    db.add(DirectoryAudit(admin_login_id=admin_id, entity=entity, entity_id=str(entity_id),
                          action=action, detail=detail or {}))


def apply(db: Session, admin_id, entity: str, row, changes: dict[str, Any]) -> dict:
    """Set the fields that differ and audit them as {field: [old, new]}."""
    diff = {}
    for field, new in changes.items():
        old = getattr(row, field)
        if old != new:
            diff[field] = [old, new]
            setattr(row, field, new)
    if diff:
        audit(db, admin_id, entity, row.id, "update", diff)
    return diff


def _get(db: Session, model, row_id: uuid.UUID, what: str):
    row = db.get(model, row_id)
    if row is None:
        raise ApiError("not_found", f"This {what} was not found.", 404)
    return row


def _duplicate(what: str, field: str = "name") -> ApiError:
    return ApiError("duplicate", f"This {what} already exists.", 409,
                    {field: f"This {what} already exists."})


# ---- societies -------------------------------------------------------------------

def clean_basements(values: list[str]) -> list[str]:
    out = []
    for raw in values:
        value = raw.strip()
        if not value or len(value) > 20:
            raise invalid("parking_basements", "Each basement needs 1 to 20 characters.")
        if value.lower() in (o.lower() for o in out):
            raise invalid("parking_basements", "A basement is listed twice.")
        out.append(value)
    if not 1 <= len(out) <= 12:
        raise invalid("parking_basements", "Give 1 to 12 basements.")
    return out


def society_counts(db: Session, society_id: uuid.UUID) -> tuple[int, int, int]:
    """(cars serviced, live subscriptions, active crew)."""
    cars = db.scalar(
        select(func.count()).select_from(Vehicle).join(Customer, Customer.id == Vehicle.customer_id)
        .where(func.coalesce(Vehicle.society_id, Customer.society_id) == society_id,
               Vehicle.active.is_(True))) or 0
    subs = db.scalar(
        select(func.count()).select_from(Subscription)
        .join(Vehicle, Vehicle.id == Subscription.vehicle_id)
        .join(Customer, Customer.id == Vehicle.customer_id)
        .where(func.coalesce(Vehicle.society_id, Customer.society_id) == society_id,
               Subscription.status.in_(LIVE_SUBSCRIPTION))) or 0
    crew = db.scalar(
        select(func.count()).select_from(CrewMember)
        .join(Login, Login.id == CrewMember.login_id)
        .where(CrewMember.society_id == society_id, Login.active.is_(True))) or 0
    return cars, subs, crew


def society_out(db: Session, s: Society) -> dict:
    cars, subs, crew = society_counts(db, s.id)
    return {"id": s.id, "name": s.name, "sector": s.sector, "city": s.city, "active": s.active,
            "parking_basements": list(s.parking_basements or []), "cars_serviced": cars,
            "active_subscriptions": subs, "active_crew": crew}


def _society_name_free(db: Session, name: str, except_id: uuid.UUID | None = None) -> None:
    query = select(Society.id).where(func.lower(Society.name) == name.lower())
    if except_id:
        query = query.where(Society.id != except_id)
    if db.scalar(query) is not None:
        raise _duplicate("society")


def create_society(db: Session, admin_id, body) -> Society:
    name = body.name.strip()
    if not name:
        raise invalid("name", "Enter the society name.")
    _society_name_free(db, name)
    society = Society(
        name=name, sector=body.sector.strip(), city=body.city.strip(), active=True,
        parking_basements=clean_basements(body.parking_basements)
        if body.parking_basements is not None else list(DEFAULT_BASEMENTS))
    db.add(society)
    db.flush()
    add_default_slots(db, society)  # ADM-SVS-06
    audit(db, admin_id, "society", society.id, "create", {"name": name})
    db.commit()
    return society


def update_society(db: Session, admin_id, society_id: uuid.UUID, body) -> Society:
    society = _get(db, Society, society_id, "society")
    changes: dict[str, Any] = {}
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise invalid("name", "Enter the society name.")
        _society_name_free(db, name, society.id)
        changes["name"] = name
    if body.sector is not None:
        changes["sector"] = body.sector.strip()
    if body.city is not None:
        changes["city"] = body.city.strip()
    if body.parking_basements is not None:
        changes["parking_basements"] = clean_basements(body.parking_basements)
    apply(db, admin_id, "society", society, changes)
    db.commit()
    return society


def set_society_active(db: Session, admin_id, society_id: uuid.UUID, active: bool) -> Society:
    society = _get(db, Society, society_id, "society")
    if not active:
        _, subs, crew = society_counts(db, society.id)
        if subs or crew:
            # ADM-REF-06.
            raise ApiError(
                "in_use", "This society has active subscriptions or active crew. "
                          "Deactivate those first.", 409,
                {"active_subscriptions": str(subs), "active_crew": str(crew)})
    if apply(db, admin_id, "society", society, {"active": active}):
        db.commit()
    return society


# ---- plans -----------------------------------------------------------------------

def plan_out(db: Session, p: Plan) -> dict:
    subs = db.scalar(select(func.count()).select_from(Subscription).where(
        Subscription.plan_id == p.id, Subscription.status != "Inactive")) or 0
    return {"id": p.id, "name": p.name, "monthly_price_rupees": p.monthly_price_rupees,
            "list_price_rupees": p.list_price_rupees, "includes_interior": p.includes_interior,
            "inclusions": list(p.inclusions or []), "badge": p.badge,
            "sort_order": p.sort_order, "active": p.active, "active_subscriptions": subs}


def _clean_inclusions(values: list[str]) -> list[str]:
    out = [v.strip() for v in values]
    if any(not v or len(v) > 200 for v in out):
        raise invalid("inclusions", "Each inclusion needs 1 to 200 characters.")
    return out


def _plan_name_free(db: Session, name: str, except_id: uuid.UUID | None = None) -> None:
    query = select(Plan.id).where(func.lower(Plan.name) == name.lower())
    if except_id:
        query = query.where(Plan.id != except_id)
    if db.scalar(query) is not None:
        raise _duplicate("plan")


def create_plan(db: Session, admin_id, body) -> Plan:
    name = body.name.strip()
    if not name:
        raise invalid("name", "Enter the plan name.")
    _plan_name_free(db, name)
    if body.list_price_rupees is not None and body.list_price_rupees < body.monthly_price_rupees:
        raise invalid("list_price_rupees", "The list price cannot be below the price.")
    plan = Plan(name=name, monthly_price_rupees=body.monthly_price_rupees,
                list_price_rupees=body.list_price_rupees,
                includes_interior=body.includes_interior,
                inclusions=_clean_inclusions(body.inclusions), badge=body.badge.strip(),
                sort_order=body.sort_order, active=True)
    db.add(plan)
    db.flush()
    audit(db, admin_id, "plan", plan.id, "create",
          {"name": name, "monthly_price_rupees": plan.monthly_price_rupees})
    db.commit()
    return plan


def update_plan(db: Session, admin_id, plan_id: uuid.UUID, body) -> Plan:
    plan = _get(db, Plan, plan_id, "plan")
    changes: dict[str, Any] = {}
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise invalid("name", "Enter the plan name.")
        _plan_name_free(db, name, plan.id)
        changes["name"] = name
    if body.monthly_price_rupees is not None:
        changes["monthly_price_rupees"] = body.monthly_price_rupees
    if body.list_price_rupees is not None:
        changes["list_price_rupees"] = body.list_price_rupees
    if body.clear_list_price:
        changes["list_price_rupees"] = None
    if body.includes_interior is not None:
        changes["includes_interior"] = body.includes_interior
    if body.inclusions is not None:
        changes["inclusions"] = _clean_inclusions(body.inclusions)
    if body.badge is not None:
        changes["badge"] = body.badge.strip()
    if body.sort_order is not None:
        changes["sort_order"] = body.sort_order
    price = changes.get("monthly_price_rupees", plan.monthly_price_rupees)
    listed = changes.get("list_price_rupees", plan.list_price_rupees)
    if listed is not None and listed < price:
        raise invalid("list_price_rupees", "The list price cannot be below the price.")
    apply(db, admin_id, "plan", plan, changes)
    db.commit()
    return plan


def set_plan_active(db: Session, admin_id, plan_id: uuid.UUID, active: bool) -> Plan:
    # A deactivated plan is no longer offered and subscriptions on it
    # continue (ADM-SET-01), so there is no guard.
    plan = _get(db, Plan, plan_id, "plan")
    if apply(db, admin_id, "plan", plan, {"active": active}):
        db.commit()
    return plan


# ---- vehicle catalogue -----------------------------------------------------------

def _catalogue_free(db: Session, make: str, model: str, variant: str,
                    except_id: uuid.UUID | None = None) -> None:
    query = select(VehicleCatalogueEntry.id).where(
        func.lower(VehicleCatalogueEntry.make) == make.lower(),
        func.lower(VehicleCatalogueEntry.model) == model.lower(),
        func.lower(VehicleCatalogueEntry.variant) == variant.lower())
    if except_id:
        query = query.where(VehicleCatalogueEntry.id != except_id)
    if db.scalar(query) is not None:
        raise _duplicate("vehicle entry", "model")


def create_vehicle(db: Session, admin_id, body) -> VehicleCatalogueEntry:
    make, model, variant = body.make.strip(), body.model.strip(), body.variant.strip()
    category = body.category.strip()
    if not make or not model or not category:
        raise invalid("make", "Make, model and category are required.")
    _catalogue_free(db, make, model, variant)
    entry = VehicleCatalogueEntry(make=make, model=model, variant=variant, category=category)
    db.add(entry)
    db.flush()
    audit(db, admin_id, "vehicle", entry.id, "create",
          {"make": make, "model": model, "variant": variant, "category": category})
    db.commit()
    return entry


def update_vehicle(db: Session, admin_id, entry_id: uuid.UUID, body) -> VehicleCatalogueEntry:
    entry = _get(db, VehicleCatalogueEntry, entry_id, "vehicle entry")
    changes = {k: v.strip() for k, v in body.model_dump(exclude_none=True).items()}
    if any(k in changes and not changes[k] for k in ("make", "model", "category")):
        raise invalid("make", "Make, model and category cannot be empty.")
    _catalogue_free(db, changes.get("make", entry.make), changes.get("model", entry.model),
                    changes.get("variant", entry.variant), entry.id)
    apply(db, admin_id, "vehicle", entry, changes)
    db.commit()
    return entry


def set_vehicle_active(db: Session, admin_id, entry_id: uuid.UUID,
                       active: bool) -> VehicleCatalogueEntry:
    entry = _get(db, VehicleCatalogueEntry, entry_id, "vehicle entry")
    if apply(db, admin_id, "vehicle", entry, {"active": active}):
        db.commit()
    return entry


# ---- services --------------------------------------------------------------------

def get_service(db: Session, name: str) -> DirectoryService:
    if name not in defaults.SERVICES:
        raise ApiError("not_found", "This service was not found.", 404)
    row = db.scalar(select(DirectoryService).where(DirectoryService.name == name))
    if row is None:  # before the seed has run
        photos, videos = defaults.PROOF_MINIMUMS[name]
        row = DirectoryService(name=name, duration_minutes=defaults.DURATIONS[name],
                               min_photos=photos, min_videos=videos,
                               sort_order=defaults.SERVICES.index(name))
        db.add(row)
        db.flush()
    return row


def update_service(db: Session, admin_id, name: str, body) -> DirectoryService:
    row = get_service(db, name)
    apply(db, admin_id, "service", row, body.model_dump(exclude_none=True))
    db.commit()
    return row


# ---- working slots ---------------------------------------------------------------

_TIME = re.compile(r"^(\d{1,2}):([0-5]\d)$")


def minute_of(text: str, field: str, allow_midnight: bool = False) -> int:
    m = _TIME.match(text.strip())
    if not m:
        raise invalid(field, "Enter a time as HH:MM.")
    h, mi = int(m.group(1)), int(m.group(2))
    if h == 24 and mi == 0 and allow_midnight:
        return 1440
    if h > 23:
        raise invalid(field, "Enter a time as HH:MM.")
    return h * 60 + mi


def show_minute(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def slot_out(slot: WorkingSlot) -> dict:
    return {"id": slot.id, "society_id": slot.society_id, "service": slot.service,
            "start": show_minute(slot.start_minute), "end": show_minute(slot.end_minute),
            "days": [defaults.WEEKDAYS[d] for d in sorted(slot.days)]}


def _day_numbers(names: list[str]) -> list[int]:
    out = set()
    for name in names:
        match = [i for i, d in enumerate(defaults.WEEKDAYS) if d.lower() == name.strip().lower()]
        if not match:
            raise invalid("days", f"{name} is not a day of the week.")
        out.add(match[0])
    return sorted(out)


def _check_slot(db: Session, society_id: uuid.UUID, service: str, start: int, end: int,
                days: list[int], except_id: uuid.UUID | None = None) -> None:
    if end <= start:
        raise invalid("end", "The end time must be after the start time.")  # ADM-SVS-07
    others = db.scalars(select(WorkingSlot).where(
        WorkingSlot.society_id == society_id, WorkingSlot.service == service))
    for other in others:
        if other.id == except_id or not set(other.days) & set(days):
            continue
        if start < other.end_minute and other.start_minute < end:
            raise ApiError(
                "overlap", "This slot overlaps another slot of the same service.", 409,
                {"start": "This slot overlaps another slot of the same service."})


def create_slot(db: Session, admin_id, society_id: uuid.UUID, body) -> WorkingSlot:
    _get(db, Society, society_id, "society")
    if body.service not in defaults.SERVICES:
        raise invalid("service", "Choose one of the three services.")
    start = minute_of(body.start, "start")
    end = minute_of(body.end, "end", allow_midnight=True)
    days = _day_numbers(body.days)
    _check_slot(db, society_id, body.service, start, end, days)
    slot = WorkingSlot(society_id=society_id, service=body.service, start_minute=start,
                       end_minute=end, days=days)
    db.add(slot)
    db.flush()
    audit(db, admin_id, "slot", slot.id, "create", slot_out(slot) | {
        "id": str(slot.id), "society_id": str(society_id)})
    db.commit()
    return slot


def update_slot(db: Session, admin_id, slot_id: uuid.UUID, body) -> WorkingSlot:
    slot = _get(db, WorkingSlot, slot_id, "working slot")
    start = minute_of(body.start, "start") if body.start is not None else slot.start_minute
    end = (minute_of(body.end, "end", allow_midnight=True) if body.end is not None
           else slot.end_minute)
    days = _day_numbers(body.days) if body.days is not None else list(slot.days)
    _check_slot(db, slot.society_id, slot.service, start, end, days, slot.id)
    apply(db, admin_id, "slot", slot,
          {"start_minute": start, "end_minute": end, "days": days})
    db.commit()
    return slot


def delete_slot(db: Session, admin_id, slot_id: uuid.UUID) -> None:
    slot = _get(db, WorkingSlot, slot_id, "working slot")
    audit(db, admin_id, "slot", slot.id, "delete", {
        "society_id": str(slot.society_id), "service": slot.service,
        "start": show_minute(slot.start_minute), "end": show_minute(slot.end_minute)})
    db.delete(slot)
    db.commit()


# ---- checklists ------------------------------------------------------------------

def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:30] or "item"


def _unique_key(db: Session, service: str, label: str) -> str:
    base = _slug(label)
    taken = set(db.scalars(select(ChecklistItem.key).where(ChecklistItem.service == service)))
    key, n = base, 2
    while key in taken:
        key = f"{base}_{n}"
        n += 1
    return key


def checklist_items(db: Session, service: str) -> list[ChecklistItem]:
    return list(db.scalars(select(ChecklistItem).where(ChecklistItem.service == service)
                           .order_by(ChecklistItem.sort_order, ChecklistItem.key)))


def check_service_name(service: str) -> str:
    if service not in defaults.SERVICES:
        raise ApiError("not_found", "This service was not found.", 404)
    return service


def add_checklist_item(db: Session, admin_id, service: str, label: str) -> ChecklistItem:
    check_service_name(service)
    label = label.strip()
    if not label:
        raise invalid("label", "Enter the item.")
    existing = checklist_items(db, service)
    item = ChecklistItem(service=service, key=_unique_key(db, service, label), label=label,
                         sort_order=max((i.sort_order for i in existing), default=-1) + 1)
    db.add(item)
    db.flush()
    audit(db, admin_id, "checklist", item.id, "create", {"service": service, "label": label})
    db.commit()
    return item


def rename_checklist_item(db: Session, admin_id, item_id: uuid.UUID,
                          label: str) -> tuple[ChecklistItem, uuid.UUID | None]:
    """ADM-CHK-05: a visit already done keeps the label it had, so a rename
    deactivates the old item and adds a new one in the same place."""
    old = _get(db, ChecklistItem, item_id, "checklist item")
    label = label.strip()
    if not label:
        raise invalid("label", "Enter the item.")
    if label == old.label:
        return old, None
    new = ChecklistItem(service=old.service, key=_unique_key(db, old.service, label),
                        label=label, sort_order=old.sort_order, active=old.active)
    old.active = False
    db.add(new)
    db.flush()
    audit(db, admin_id, "checklist", old.id, "rename",
          {"label": [old.label, label], "new_id": str(new.id)})
    db.commit()
    return new, old.id


def set_item_active(db: Session, admin_id, item_id: uuid.UUID, active: bool) -> ChecklistItem:
    item = _get(db, ChecklistItem, item_id, "checklist item")
    if not active:
        others = [i for i in checklist_items(db, item.service) if i.active and i.id != item.id]
        if not others:
            raise ApiError("in_use", "A checklist needs at least one active item.", 409)
    if apply(db, admin_id, "checklist", item, {"active": active}):
        db.commit()
    return item


def _reorder(db: Session, admin_id, entity: str, rows: list, ids: list[uuid.UUID]) -> None:
    by_id = {r.id: r for r in rows}
    if len(set(ids)) != len(ids) or set(ids) != set(by_id):
        raise invalid("ids", "Send every item once, in the order you want.")
    for position, row_id in enumerate(ids):
        apply(db, admin_id, entity, by_id[row_id], {"sort_order": position})
    db.commit()


def reorder_checklist(db: Session, admin_id, service: str, ids: list[uuid.UUID]) -> None:
    check_service_name(service)
    _reorder(db, admin_id, "checklist", checklist_items(db, service), ids)


# ---- reasons ---------------------------------------------------------------------

def all_reasons(db: Session) -> list[CncReason]:
    return list(db.scalars(select(CncReason).order_by(CncReason.sort_order, CncReason.key)))


def add_reason(db: Session, admin_id, label: str) -> CncReason:
    label = label.strip()
    if not label:
        raise invalid("label", "Enter the reason.")
    rows = all_reasons(db)
    if any(r.label.lower() == label.lower() and r.active for r in rows):
        raise _duplicate("reason", "label")
    base = _slug(label)
    taken = {r.key for r in rows}
    key, n = base, 2
    while key in taken:
        key = f"{base}_{n}"
        n += 1
    reason = CncReason(key=key, label=label,
                       sort_order=max((r.sort_order for r in rows), default=-1) + 1)
    db.add(reason)
    db.flush()
    audit(db, admin_id, "reason", reason.id, "create", {"label": label})
    db.commit()
    return reason


def rename_reason(db: Session, admin_id, reason_id: uuid.UUID, label: str) -> CncReason:
    reason = _get(db, CncReason, reason_id, "reason")
    label = label.strip()
    if not label:
        raise invalid("label", "Enter the reason.")
    apply(db, admin_id, "reason", reason, {"label": label})
    db.commit()
    return reason


def set_reason_active(db: Session, admin_id, reason_id: uuid.UUID, active: bool) -> CncReason:
    reason = _get(db, CncReason, reason_id, "reason")
    if not active:
        others = [r for r in all_reasons(db) if r.active and r.id != reason.id]
        if not others:
            raise ApiError("in_use", "The crew need at least one active reason.", 409)
    if apply(db, admin_id, "reason", reason, {"active": active}):
        db.commit()
    return reason


def reorder_reasons(db: Session, admin_id, ids: list[uuid.UUID]) -> None:
    _reorder(db, admin_id, "reason", all_reasons(db), ids)


# ---- settings --------------------------------------------------------------------

def setting_out(db: Session, definition: settings_registry.SettingDef,
                row: SystemSetting | None) -> dict:
    stored = row.value if row is not None else settings_registry.default_for(definition.key)
    try:
        value = settings_registry.typed(definition, stored)
    except ValueError:
        value = stored
    return {"key": definition.key, "label": definition.label, "group": definition.group,
            "kind": definition.kind, "value": value, "is_default": row is None,
            "updated_at": row.updated_at if row else None,
            "updated_by": row.updated_by if row else None}


def list_settings(db: Session) -> list[dict]:
    rows = {r.key: r for r in db.scalars(select(SystemSetting))}
    return [setting_out(db, d, rows.get(d.key)) for d in settings_registry.DEFINITIONS]


def _definition(key: str) -> settings_registry.SettingDef:
    definition = settings_registry.BY_KEY.get(key)
    if definition is None:
        raise ApiError("not_found", "This setting was not found.", 404)
    return definition


def get_setting(db: Session, key: str) -> dict:
    definition = _definition(key)
    return setting_out(db, definition, db.get(SystemSetting, key))


def save_settings(db: Session, admin_id, values: dict[str, Any]) -> list[dict]:
    """All or nothing: every value is checked before any is saved."""
    parsed: dict[str, str] = {}
    errors: dict[str, str] = {}
    for key, raw in values.items():
        if key.startswith("invoice."):
            raise ApiError("read_only", "Invoice seller values are seeded from environment configuration.", 409)
        definition = settings_registry.BY_KEY.get(key)
        if definition is None:
            errors[key] = "This setting does not exist."
            continue
        try:
            parsed[key] = settings_registry.parse(definition, raw)
        except ValueError as exc:
            errors[key] = str(exc)
    if errors:
        raise ApiError("validation_failed", "Please check the details.", 422, errors)
    enabled = parsed.get("schedule.auto_enabled", str(lookup.setting(db, "schedule.auto_enabled")))
    at = parsed.get("schedule.auto_time", lookup.setting(db, "schedule.auto_time"))
    if enabled == "1" and not at:
        raise invalid("schedule.auto_time", "Choose an IST time before enabling automatic planning.")
    out = []
    for key, text in parsed.items():
        row = db.get(SystemSetting, key)
        before = row.value if row else settings_registry.default_for(key)
        if row is None:
            row = SystemSetting(key=key, value=text, updated_at=utcnow(), updated_by=admin_id)
            db.add(row)
        else:
            row.value, row.updated_at, row.updated_by = text, utcnow(), admin_id
        if before != text:
            audit(db, admin_id, "setting", key, "update", {"value": [before, text]})
        out.append(row)
    db.commit()
    lookup.invalidate(db)
    return [setting_out(db, settings_registry.BY_KEY[r.key], r) for r in out]


# ---- add-on catalogue ------------------------------------------------------------

def _addon_name_free(db: Session, name: str, except_id: uuid.UUID | None = None) -> None:
    query = select(AddonCatalogueItem.id).where(
        func.lower(AddonCatalogueItem.name) == name.lower())
    if except_id:
        query = query.where(AddonCatalogueItem.id != except_id)
    if db.scalar(query) is not None:
        raise _duplicate("add-on")


def _addon_list_price(price: int, listed: int | None) -> None:
    if listed is not None and listed < price:
        raise invalid("list_price_rupees", "The list price cannot be below the price.")


def create_addon(db: Session, admin_id, body) -> AddonCatalogueItem:
    name = body.name.strip()
    if not name:
        raise invalid("name", "Enter the add-on name.")
    if body.service not in defaults.SERVICES:
        raise invalid("service", "Choose one of the three services.")
    _addon_name_free(db, name)
    _addon_list_price(body.price_rupees, body.list_price_rupees)
    duration = body.duration_minutes or lookup.duration_minutes(db, body.service)
    item = AddonCatalogueItem(
        name=name, description=body.description.strip(), service=body.service,
        price_rupees=body.price_rupees, list_price_rupees=body.list_price_rupees,
        duration_minutes=duration, sort_order=body.sort_order, active=True)
    db.add(item)
    db.flush()
    audit(db, admin_id, "addon", item.id, "create",
          {"name": name, "price_rupees": item.price_rupees})
    db.commit()
    return item


def update_addon(db: Session, admin_id, addon_id: uuid.UUID, body) -> AddonCatalogueItem:
    item = _get(db, AddonCatalogueItem, addon_id, "add-on")
    changes = body.model_dump(exclude_none=True)
    clear = changes.pop("clear_list_price", False)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise invalid("name", "Enter the add-on name.")
        _addon_name_free(db, changes["name"], item.id)
    if "description" in changes:
        changes["description"] = changes["description"].strip()
    if clear:
        changes["list_price_rupees"] = None
    _addon_list_price(changes.get("price_rupees", item.price_rupees),
                      changes.get("list_price_rupees", item.list_price_rupees))
    apply(db, admin_id, "addon", item, changes)
    db.commit()
    return item


def set_addon_active(db: Session, admin_id, addon_id: uuid.UUID,
                     active: bool) -> AddonCatalogueItem:
    # A deactivated add-on is no longer offered; requests already made
    # continue (ADM-ADD-01).
    item = _get(db, AddonCatalogueItem, addon_id, "add-on")
    if apply(db, admin_id, "addon", item, {"active": active}):
        db.commit()
    return item
