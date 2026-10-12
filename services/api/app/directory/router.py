import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.directory import defaults, lookup, service
from app.directory import schemas as s
from app.directory.models import (
    AddonCatalogueItem,
    DirectoryAudit,
    DirectoryService,
    Plan,
    Society,
    VehicleCatalogueEntry,
)
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError

admin = APIRouter(prefix="/v1/admin/directory", tags=["directory"])
customer = APIRouter(prefix="/v1/customer/directory", tags=["directory"])

AdminUser = Annotated[User, Depends(require_role("admin"))]
CustomerUser = Annotated[User, Depends(require_role("customer"))]
Db = Annotated[Session, Depends(get_db)]


def _only_active(query, model, include_inactive: bool):
    return query if include_inactive else query.where(model.active.is_(True))


# ---- societies -------------------------------------------------------------------

@admin.get("/societies", response_model=list[s.DirectorySocietyOut])
def list_societies(user: AdminUser, db: Db, include_inactive: bool = True):
    rows = db.scalars(_only_active(select(Society).order_by(Society.name), Society,
                                   include_inactive))
    return [service.society_out(db, r) for r in rows]


@admin.post("/societies", response_model=s.DirectorySocietyOut, status_code=201)
def create_society(body: s.DirectorySocietyCreate, user: AdminUser, db: Db):
    return service.society_out(db, service.create_society(db, user.id, body))


@admin.get("/societies/{society_id}", response_model=s.DirectorySocietyOut)
def get_society(society_id: uuid.UUID, user: AdminUser, db: Db):
    return service.society_out(db, service._get(db, Society, society_id, "society"))


@admin.patch("/societies/{society_id}", response_model=s.DirectorySocietyOut)
def update_society(society_id: uuid.UUID, body: s.DirectorySocietyUpdate,
                   user: AdminUser, db: Db):
    return service.society_out(db, service.update_society(db, user.id, society_id, body))


@admin.post("/societies/{society_id}/deactivate", response_model=s.DirectorySocietyOut)
def deactivate_society(society_id: uuid.UUID, user: AdminUser, db: Db):
    return service.society_out(db, service.set_society_active(db, user.id, society_id, False))


@admin.post("/societies/{society_id}/reactivate", response_model=s.DirectorySocietyOut)
def reactivate_society(society_id: uuid.UUID, user: AdminUser, db: Db):
    return service.society_out(db, service.set_society_active(db, user.id, society_id, True))


# ---- working slots ---------------------------------------------------------------

@admin.get("/societies/{society_id}/slots", response_model=list[s.DirectorySlotOut])
def list_slots(society_id: uuid.UUID, user: AdminUser, db: Db, service_name: Annotated[
        str | None, Query(alias="service")] = None):
    service._get(db, Society, society_id, "society")
    return [service.slot_out(r) for r in lookup.working_slots(db, society_id, service_name)]


@admin.post("/societies/{society_id}/slots", response_model=s.DirectorySlotOut,
            status_code=201)
def create_slot(society_id: uuid.UUID, body: s.DirectorySlotCreate, user: AdminUser, db: Db):
    return service.slot_out(service.create_slot(db, user.id, society_id, body))


@admin.patch("/slots/{slot_id}", response_model=s.DirectorySlotOut)
def update_slot(slot_id: uuid.UUID, body: s.DirectorySlotUpdate, user: AdminUser, db: Db):
    return service.slot_out(service.update_slot(db, user.id, slot_id, body))


@admin.delete("/slots/{slot_id}", status_code=204)
def delete_slot(slot_id: uuid.UUID, user: AdminUser, db: Db):
    service.delete_slot(db, user.id, slot_id)
    return Response(status_code=204)


# ---- plans -----------------------------------------------------------------------

@admin.get("/plans", response_model=list[s.DirectoryPlanOut])
def list_plans(user: AdminUser, db: Db, include_inactive: bool = True):
    rows = db.scalars(_only_active(select(Plan).order_by(Plan.sort_order, Plan.name), Plan,
                                   include_inactive))
    return [service.plan_out(db, r) for r in rows]


@admin.post("/plans", response_model=s.DirectoryPlanOut, status_code=201)
def create_plan(body: s.DirectoryPlanCreate, user: AdminUser, db: Db):
    return service.plan_out(db, service.create_plan(db, user.id, body))


@admin.patch("/plans/{plan_id}", response_model=s.DirectoryPlanOut)
def update_plan(plan_id: uuid.UUID, body: s.DirectoryPlanUpdate, user: AdminUser, db: Db):
    return service.plan_out(db, service.update_plan(db, user.id, plan_id, body))


@admin.post("/plans/{plan_id}/deactivate", response_model=s.DirectoryPlanOut)
def deactivate_plan(plan_id: uuid.UUID, user: AdminUser, db: Db):
    return service.plan_out(db, service.set_plan_active(db, user.id, plan_id, False))


@admin.post("/plans/{plan_id}/reactivate", response_model=s.DirectoryPlanOut)
def reactivate_plan(plan_id: uuid.UUID, user: AdminUser, db: Db):
    return service.plan_out(db, service.set_plan_active(db, user.id, plan_id, True))


# ---- vehicle catalogue -----------------------------------------------------------

@admin.get("/vehicle-catalogue", response_model=list[s.DirectoryVehicleOut])
def list_vehicles(user: AdminUser, db: Db, include_inactive: bool = True,
                  make: str | None = None, q: str | None = None):
    query = select(VehicleCatalogueEntry).order_by(
        VehicleCatalogueEntry.make, VehicleCatalogueEntry.model, VehicleCatalogueEntry.variant)
    query = _only_active(query, VehicleCatalogueEntry, include_inactive)
    if make:
        query = query.where(func.lower(VehicleCatalogueEntry.make) == make.lower())
    if q:
        like = f"%{q.lower()}%"
        query = query.where(func.lower(VehicleCatalogueEntry.model).like(like)
                            | func.lower(VehicleCatalogueEntry.make).like(like))
    return list(db.scalars(query))


@admin.get("/vehicle-catalogue/categories", response_model=list[str])
def list_categories(user: AdminUser, db: Db):
    return list(db.scalars(select(VehicleCatalogueEntry.category).distinct()
                           .order_by(VehicleCatalogueEntry.category)))


@admin.post("/vehicle-catalogue", response_model=s.DirectoryVehicleOut, status_code=201)
def create_vehicle(body: s.DirectoryVehicleCreate, user: AdminUser, db: Db):
    return service.create_vehicle(db, user.id, body)


@admin.patch("/vehicle-catalogue/{entry_id}", response_model=s.DirectoryVehicleOut)
def update_vehicle(entry_id: uuid.UUID, body: s.DirectoryVehicleUpdate, user: AdminUser,
                   db: Db):
    return service.update_vehicle(db, user.id, entry_id, body)


@admin.post("/vehicle-catalogue/{entry_id}/deactivate", response_model=s.DirectoryVehicleOut)
def deactivate_vehicle(entry_id: uuid.UUID, user: AdminUser, db: Db):
    return service.set_vehicle_active(db, user.id, entry_id, False)


@admin.post("/vehicle-catalogue/{entry_id}/reactivate", response_model=s.DirectoryVehicleOut)
def reactivate_vehicle(entry_id: uuid.UUID, user: AdminUser, db: Db):
    return service.set_vehicle_active(db, user.id, entry_id, True)


# ---- services --------------------------------------------------------------------

@admin.get("/services", response_model=list[s.DirectoryServiceOut])
def list_services(user: AdminUser, db: Db):
    rows = {r.name: r for r in db.scalars(select(DirectoryService))}
    out = []
    for name in defaults.SERVICES:
        row = rows.get(name)
        photos, videos = lookup.proof_minimums(db, name)
        out.append(s.DirectoryServiceOut(
            name=name, duration_minutes=row.duration_minutes if row
            else defaults.DURATIONS[name], min_photos=photos, min_videos=videos))
    return out


@admin.patch("/services/{name}", response_model=s.DirectoryServiceOut)
def update_service(name: str, body: s.DirectoryServiceUpdate, user: AdminUser, db: Db):
    service.check_service_name(name)
    row = service.update_service(db, user.id, name, body)
    return s.DirectoryServiceOut(name=row.name, duration_minutes=row.duration_minutes,
                                 min_photos=row.min_photos, min_videos=row.min_videos)


# ---- checklists ------------------------------------------------------------------

def _checklist(db: Session, name: str) -> s.DirectoryChecklistOut:
    service.check_service_name(name)
    photos, videos = lookup.proof_minimums(db, name)
    items = service.checklist_items(db, name)
    return s.DirectoryChecklistOut(
        service=name, min_photos=photos, min_videos=videos,
        items=[s.DirectoryChecklistItemOut.model_validate(i, from_attributes=True)
               for i in items])


@admin.get("/checklists", response_model=list[s.DirectoryChecklistOut])
def list_checklists(user: AdminUser, db: Db):
    return [_checklist(db, name) for name in defaults.SERVICES]


@admin.get("/checklists/{name}", response_model=s.DirectoryChecklistOut)
def get_checklist(name: str, user: AdminUser, db: Db):
    return _checklist(db, name)


@admin.post("/checklists/{name}/items", response_model=s.DirectoryChecklistItemOut,
            status_code=201)
def add_item(name: str, body: s.DirectoryChecklistItemCreate, user: AdminUser, db: Db):
    return service.add_checklist_item(db, user.id, name, body.label)


@admin.put("/checklists/{name}/order", response_model=s.DirectoryChecklistOut)
def reorder_items(name: str, body: s.DirectoryOrder, user: AdminUser, db: Db):
    service.reorder_checklist(db, user.id, name, body.ids)
    return _checklist(db, name)


@admin.patch("/checklist-items/{item_id}", response_model=s.DirectoryChecklistItemRenamed)
def rename_item(item_id: uuid.UUID, body: s.DirectoryChecklistItemUpdate, user: AdminUser,
                db: Db):
    item, replaced = service.rename_checklist_item(db, user.id, item_id, body.label)
    return s.DirectoryChecklistItemRenamed(
        item=s.DirectoryChecklistItemOut.model_validate(item, from_attributes=True),
        replaced_id=replaced)


@admin.post("/checklist-items/{item_id}/deactivate",
            response_model=s.DirectoryChecklistItemOut)
def deactivate_item(item_id: uuid.UUID, user: AdminUser, db: Db):
    return service.set_item_active(db, user.id, item_id, False)


@admin.post("/checklist-items/{item_id}/reactivate",
            response_model=s.DirectoryChecklistItemOut)
def reactivate_item(item_id: uuid.UUID, user: AdminUser, db: Db):
    return service.set_item_active(db, user.id, item_id, True)


# ---- could-not-complete reasons --------------------------------------------------

@admin.get("/reasons", response_model=list[s.DirectoryReasonOut])
def list_reasons(user: AdminUser, db: Db):
    return service.all_reasons(db)


@admin.post("/reasons", response_model=s.DirectoryReasonOut, status_code=201)
def add_reason(body: s.DirectoryReasonCreate, user: AdminUser, db: Db):
    return service.add_reason(db, user.id, body.label)


@admin.put("/reasons/order", response_model=list[s.DirectoryReasonOut])
def reorder_reasons(body: s.DirectoryOrder, user: AdminUser, db: Db):
    service.reorder_reasons(db, user.id, body.ids)
    return service.all_reasons(db)


@admin.patch("/reasons/{reason_id}", response_model=s.DirectoryReasonOut)
def rename_reason(reason_id: uuid.UUID, body: s.DirectoryReasonUpdate, user: AdminUser,
                  db: Db):
    return service.rename_reason(db, user.id, reason_id, body.label)


@admin.post("/reasons/{reason_id}/deactivate", response_model=s.DirectoryReasonOut)
def deactivate_reason(reason_id: uuid.UUID, user: AdminUser, db: Db):
    return service.set_reason_active(db, user.id, reason_id, False)


@admin.post("/reasons/{reason_id}/reactivate", response_model=s.DirectoryReasonOut)
def reactivate_reason(reason_id: uuid.UUID, user: AdminUser, db: Db):
    return service.set_reason_active(db, user.id, reason_id, True)


# ---- settings --------------------------------------------------------------------

@admin.get("/settings", response_model=list[s.DirectorySettingOut])
def list_settings(user: AdminUser, db: Db):
    return service.list_settings(db)


@admin.patch("/settings", response_model=list[s.DirectorySettingOut])
def patch_settings(body: s.DirectorySettingsPatch, user: AdminUser, db: Db):
    return service.save_settings(db, user.id, body.values)


@admin.get("/settings/{key}", response_model=s.DirectorySettingOut)
def get_setting(key: str, user: AdminUser, db: Db):
    return service.get_setting(db, key)


@admin.put("/settings/{key}", response_model=s.DirectorySettingOut)
def put_setting(key: str, body: s.DirectorySettingPut, user: AdminUser, db: Db):
    if key not in service.settings_registry.BY_KEY:
        raise ApiError("not_found", "This setting was not found.", 404)
    try:
        return service.save_settings(db, user.id, {key: body.value})[0]
    except ApiError as exc:
        if exc.status == 422 and key in exc.fields:
            raise ApiError(exc.code, exc.message, 422, {"value": exc.fields[key]}) from exc
        raise


# ---- add-on catalogue ------------------------------------------------------------

@admin.get("/addons", response_model=list[s.DirectoryAddonOut])
def list_addons(user: AdminUser, db: Db, include_inactive: bool = True):
    query = select(AddonCatalogueItem).order_by(
        AddonCatalogueItem.sort_order, AddonCatalogueItem.name)
    return list(db.scalars(_only_active(query, AddonCatalogueItem, include_inactive)))


@admin.post("/addons", response_model=s.DirectoryAddonOut, status_code=201)
def create_addon(body: s.DirectoryAddonCreate, user: AdminUser, db: Db):
    return service.create_addon(db, user.id, body)


@admin.patch("/addons/{addon_id}", response_model=s.DirectoryAddonOut)
def update_addon(addon_id: uuid.UUID, body: s.DirectoryAddonUpdate, user: AdminUser, db: Db):
    return service.update_addon(db, user.id, addon_id, body)


@admin.post("/addons/{addon_id}/deactivate", response_model=s.DirectoryAddonOut)
def deactivate_addon(addon_id: uuid.UUID, user: AdminUser, db: Db):
    return service.set_addon_active(db, user.id, addon_id, False)


@admin.post("/addons/{addon_id}/reactivate", response_model=s.DirectoryAddonOut)
def reactivate_addon(addon_id: uuid.UUID, user: AdminUser, db: Db):
    return service.set_addon_active(db, user.id, addon_id, True)


# ---- audit -----------------------------------------------------------------------

@admin.get("/audit", response_model=list[s.DirectoryAuditOut])
def list_audit(user: AdminUser, db: Db, entity: str | None = None,
               limit: Annotated[int, Query(ge=1, le=500)] = 100):
    query = select(DirectoryAudit).order_by(DirectoryAudit.at.desc()).limit(limit)
    if entity:
        query = query.where(DirectoryAudit.entity == entity)
    return list(db.scalars(query))


# ---- reads for the customer app --------------------------------------------------

@customer.get("/societies", response_model=list[s.DirectoryCustomerSocietyOut])
def customer_societies(user: CustomerUser, db: Db):
    """Only active societies (ADM-REF-01, ONB-03)."""
    rows = db.scalars(select(Society).where(Society.active.is_(True)).order_by(Society.name))
    out = []
    for r in rows:
        cars, _, _ = service.society_counts(db, r.id)
        out.append(s.DirectoryCustomerSocietyOut(
            id=r.id, name=r.name, sector=r.sector, city=r.city, cars_serviced=cars,
            parking_basements=list(r.parking_basements or [])))
    return out


@customer.get("/plans", response_model=list[s.DirectoryCustomerPlanOut])
def customer_plans(user: CustomerUser, db: Db):
    """Only active plans (ADM-SET-01, PAY-12)."""
    rows = db.scalars(select(Plan).where(Plan.active.is_(True))
                      .order_by(Plan.sort_order, Plan.name))
    return [s.DirectoryCustomerPlanOut(
        id=r.id, name=r.name, monthly_price_rupees=r.monthly_price_rupees,
        list_price_rupees=r.list_price_rupees, includes_interior=r.includes_interior,
        inclusions=list(r.inclusions or []), badge=r.badge) for r in rows]


@customer.get("/vehicle-catalogue", response_model=list[s.DirectoryCustomerVehicleOut])
def customer_vehicles(user: CustomerUser, db: Db):
    """Active makes, models and variants with the category (ONB-09, ONB-11)."""
    rows = db.scalars(select(VehicleCatalogueEntry)
                      .where(VehicleCatalogueEntry.active.is_(True))
                      .order_by(VehicleCatalogueEntry.make, VehicleCatalogueEntry.model,
                                VehicleCatalogueEntry.variant))
    return [s.DirectoryCustomerVehicleOut(id=r.id, make=r.make, model=r.model, variant=r.variant,
                                          category=r.category) for r in rows]


@customer.get("/addons", response_model=list[s.DirectoryCustomerAddonOut])
def customer_addons(user: CustomerUser, db: Db):
    """Only active add-ons (ADM-ADD-01)."""
    rows = db.scalars(select(AddonCatalogueItem).where(AddonCatalogueItem.active.is_(True))
                      .order_by(AddonCatalogueItem.sort_order, AddonCatalogueItem.name))
    return [s.DirectoryCustomerAddonOut(
        id=r.id, name=r.name, description=r.description, service=r.service,
        price_rupees=r.price_rupees, list_price_rupees=r.list_price_rupees,
        duration_minutes=r.duration_minutes) for r in rows]

