from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.changes.access import any_vehicle, owned_vehicle
from app.changes.gateway import ScheduleChangeGateway, get_schedule_gateway
from app.changes.rules import Clock, get_now
from app.changes.schemas import (
    ChangeOut,
    ChangesOut,
    CutoffChangeIn,
    PauseIn,
    PreferencesIn,
    PreferencesOut,
    SkipIn,
    UpcomingDay,
)
from app.changes.service import Actor, ChangesService
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role

customer = APIRouter(prefix="/v1/customer", tags=["changes"])
admin = APIRouter(prefix="/v1/admin", tags=["changes"])


def get_changes_service(db: Session = Depends(get_db),
                        gateway: ScheduleChangeGateway = Depends(get_schedule_gateway),
                        now: Clock = Depends(get_now)) -> ChangesService:
    return ChangesService(db, gateway, now)


# --- the customer -------------------------------------------------------------

@customer.get("/vehicles/{vehicle_id}/changes", response_model=ChangesOut)
def my_changes(vehicle_id: str, user: User = Depends(require_role("customer")),
               db: Session = Depends(get_db),
               svc: ChangesService = Depends(get_changes_service)):
    _, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.overview(vehicle, sub)


@customer.get("/vehicles/{vehicle_id}/upcoming", response_model=list[UpcomingDay])
def upcoming(vehicle_id: str, user: User = Depends(require_role("customer")),
             db: Session = Depends(get_db),
             svc: ChangesService = Depends(get_changes_service)):
    _, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.upcoming(vehicle, sub=sub)


@customer.post("/vehicles/{vehicle_id}/skips", response_model=ChangeOut, status_code=201)
def skip(vehicle_id: str, body: SkipIn, user: User = Depends(require_role("customer")),
         idempotency_key: str | None = Header(default=None),
         db: Session = Depends(get_db), svc: ChangesService = Depends(get_changes_service)):
    c, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.skip(Actor("customer", user.id), c, vehicle, sub, body.date, idempotency_key)


@customer.delete("/vehicles/{vehicle_id}/skips/{skip_id}", status_code=204)
def unskip(vehicle_id: str, skip_id: str, user: User = Depends(require_role("customer")),
           db: Session = Depends(get_db), svc: ChangesService = Depends(get_changes_service)):
    _, vehicle, _ = owned_vehicle(db, user.id, vehicle_id)
    svc.unskip(Actor("customer", user.id), vehicle, skip_id)


@customer.post("/vehicles/{vehicle_id}/pauses", response_model=ChangeOut, status_code=201)
def pause(vehicle_id: str, body: PauseIn, user: User = Depends(require_role("customer")),
          idempotency_key: str | None = Header(default=None),
          db: Session = Depends(get_db), svc: ChangesService = Depends(get_changes_service)):
    c, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.pause(Actor("customer", user.id), c, vehicle, sub, body.from_date,
                     body.to_date, idempotency_key)


@customer.delete("/vehicles/{vehicle_id}/pauses/{pause_id}", response_model=ChangeOut)
def end_pause(vehicle_id: str, pause_id: str, user: User = Depends(require_role("customer")),
              db: Session = Depends(get_db),
              svc: ChangesService = Depends(get_changes_service)):
    _, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.end_pause(Actor("customer", user.id), vehicle, sub, pause_id)


@customer.post("/vehicles/{vehicle_id}/cutoff-changes", response_model=ChangeOut,
               status_code=201)
def cutoff_change(vehicle_id: str, body: CutoffChangeIn,
                  user: User = Depends(require_role("customer")),
                  idempotency_key: str | None = Header(default=None),
                  db: Session = Depends(get_db),
                  svc: ChangesService = Depends(get_changes_service)):
    c, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.change_cutoff(Actor("customer", user.id), c, vehicle, sub, body.date,
                             body.cutoff_time, idempotency_key)


@customer.patch("/vehicles/{vehicle_id}/preferences", response_model=PreferencesOut)
def update_preferences(vehicle_id: str, body: PreferencesIn,
                       user: User = Depends(require_role("customer")),
                       db: Session = Depends(get_db),
                       svc: ChangesService = Depends(get_changes_service)):
    """The default service cutoff time and interior care day (SUB-08)."""
    _, vehicle, sub = owned_vehicle(db, user.id, vehicle_id)
    return svc.update_preferences(Actor("customer", user.id), vehicle, sub,
                                  body.cutoff_time, body.interior_day)


# --- the admin, on behalf of a customer (ADM-ACC-07 e, ADM-CUS-09) -------------

@admin.get("/vehicles/{vehicle_id}/changes", response_model=ChangesOut)
def admin_changes(vehicle_id: str, user: User = Depends(require_role("admin")),
                  db: Session = Depends(get_db),
                  svc: ChangesService = Depends(get_changes_service)):
    _, vehicle, sub = any_vehicle(db, vehicle_id)
    return svc.overview(vehicle, sub)


@admin.post("/vehicles/{vehicle_id}/skips", response_model=ChangeOut, status_code=201)
def admin_skip(vehicle_id: str, body: SkipIn, user: User = Depends(require_role("admin")),
               idempotency_key: str | None = Header(default=None),
               db: Session = Depends(get_db),
               svc: ChangesService = Depends(get_changes_service)):
    c, vehicle, sub = any_vehicle(db, vehicle_id)
    return svc.skip(Actor("admin", user.id), c, vehicle, sub, body.date, idempotency_key)


@admin.delete("/vehicles/{vehicle_id}/skips/{skip_id}", status_code=204)
def admin_unskip(vehicle_id: str, skip_id: str, user: User = Depends(require_role("admin")),
                 db: Session = Depends(get_db),
                 svc: ChangesService = Depends(get_changes_service)):
    _, vehicle, _ = any_vehicle(db, vehicle_id)
    svc.unskip(Actor("admin", user.id), vehicle, skip_id)


@admin.post("/vehicles/{vehicle_id}/pauses", response_model=ChangeOut, status_code=201)
def admin_pause(vehicle_id: str, body: PauseIn, user: User = Depends(require_role("admin")),
                idempotency_key: str | None = Header(default=None),
                db: Session = Depends(get_db),
                svc: ChangesService = Depends(get_changes_service)):
    c, vehicle, sub = any_vehicle(db, vehicle_id)
    return svc.pause(Actor("admin", user.id), c, vehicle, sub, body.from_date,
                     body.to_date, idempotency_key)


@admin.delete("/vehicles/{vehicle_id}/pauses/{pause_id}", response_model=ChangeOut)
def admin_end_pause(vehicle_id: str, pause_id: str,
                    user: User = Depends(require_role("admin")),
                    db: Session = Depends(get_db),
                    svc: ChangesService = Depends(get_changes_service)):
    _, vehicle, sub = any_vehicle(db, vehicle_id)
    return svc.end_pause(Actor("admin", user.id), vehicle, sub, pause_id)
