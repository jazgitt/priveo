import uuid
from datetime import date

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.addons.schemas import (
    AddonChangeIn,
    AddonOut,
    AddonRequestIn,
    AddonsOut,
    AdminAddonCreate,
    AdminAddonIn,
    AdminAddonOut,
    StandaloneIn,
)
from app.addons.service import AddonService
from app.billing.config import MoneySettings, get_money_settings
from app.billing.service import BillingService
from app.changes.access import customer_of, owned_vehicle, parse_id
from app.changes.rules import Clock, get_now
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role

customer = APIRouter(prefix="/v1/customer", tags=["addons"])
admin = APIRouter(prefix="/v1/admin", tags=["addons"])


def get_addon_service(
    db: Session = Depends(get_db),
    now: Clock = Depends(get_now),
    settings: MoneySettings = Depends(get_money_settings),
) -> AddonService:
    return AddonService(db, now, settings, BillingService(db, now, settings))


@customer.get("/addons", response_model=AddonsOut)
def my_addons(
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: AddonService = Depends(get_addon_service),
):
    return svc.mine(customer_of(db, user.id))


@customer.post("/vehicles/{vehicle_id}/addons", response_model=AddonOut, status_code=201)
def request_addon(
    vehicle_id: str,
    body: AddonRequestIn,
    user: User = Depends(require_role("customer")),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
    svc: AddonService = Depends(get_addon_service),
):
    c, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.request(c, vehicle, sub, body.service, body.date, body.finish_by, idempotency_key)


@customer.post("/addons/standalone", response_model=AddonOut, status_code=201)
def request_standalone(
    body: StandaloneIn,
    user: User = Depends(require_role("customer")),
    idempotency_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
    svc: AddonService = Depends(get_addon_service),
):
    return svc.standalone(customer_of(db, user.id), user.id, body, idempotency_key)


@customer.patch("/addons/{addon_id}", response_model=AddonOut)
def change_addon(
    addon_id: str,
    body: AddonChangeIn,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: AddonService = Depends(get_addon_service),
):
    return svc.change(customer_of(db, user.id), addon_id, body)


@customer.delete("/addons/{addon_id}", response_model=AddonOut)
def cancel_addon(
    addon_id: str,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    svc: AddonService = Depends(get_addon_service),
):
    return svc.cancel(customer_of(db, user.id), addon_id)


@admin.get("/addons", response_model=list[AdminAddonOut])
def list_addons(
    status: str | None = None,
    standalone: bool | None = None,
    society_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    service: str | None = None,
    user: User = Depends(require_role("admin")),
    svc: AddonService = Depends(get_addon_service),
):
    return svc.admin_list(status, standalone, society_id, date_from, date_to, service)


@admin.patch("/addons/{addon_id}", response_model=AdminAddonOut)
def update_addon(
    addon_id: str,
    body: AdminAddonIn,
    user: User = Depends(require_role("admin")),
    svc: AddonService = Depends(get_addon_service),
    db: Session = Depends(get_db),
):
    from app.customers.administration import audit

    result = svc.admin_update(addon_id, body)
    audit(db, user.id, "addon", addon_id, "update", body.model_dump(mode="json"))
    db.commit()
    return result


@admin.post("/addons", response_model=AdminAddonOut, status_code=201)
def admin_request_addon(
    body: AdminAddonCreate,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    svc: AddonService = Depends(get_addon_service),
):
    from app.addons.models import AddonBooking
    from app.changes.access import any_vehicle
    from app.customers.administration import audit

    c, vehicle, sub = any_vehicle(db, body.vehicle_id)
    if sub is None:
        result = svc.standalone(c, c.login_id, StandaloneIn(vehicle_id=str(vehicle.id),
            service=body.service, date=body.date, finish_by=body.finish_by), None, admin=True)
    else:
        result = svc.request(c, vehicle, sub, body.service, body.date, body.finish_by, None, admin=True)
    audit(db, user.id, "addon", result.id, "create", body.model_dump(mode="json"))
    db.commit()
    return svc._admin_out(db.get(AddonBooking, parse_id(result.id, "request")))
