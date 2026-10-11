import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.identity.service import User
from app.notifications.push import PushSender, get_default_sender
from app.notifications.service import (
    Inbox,
    NotificationPreferencesOut,
    NotificationService,
)
from app.platform.db import get_db
from app.platform.deps import require_role

router = APIRouter(prefix="/v1/customer", tags=["notifications"])
crew_router = APIRouter(prefix="/v1/crew", tags=["notifications"])
admin_router = APIRouter(prefix="/v1/admin", tags=["notifications"])
customer = require_role("customer")
crew = require_role("crew")
admin = require_role("admin")


def get_push_sender() -> PushSender:
    """The logging fake until FCM is set up. Override to bind the real one."""
    return get_default_sender()


def get_notifications(db: Session = Depends(get_db),
                      push: PushSender = Depends(get_push_sender)) -> NotificationService:
    return NotificationService(db, push)


class DeviceBody(BaseModel):
    token: str = Field(min_length=8, max_length=512)
    platform: Literal["android", "ios"]


class NotificationPreferenceIn(BaseModel):
    event: str
    enabled: bool


class NotificationPreferencesIn(BaseModel):
    """Only the events listed change; the others keep their switch."""
    items: list[NotificationPreferenceIn]


# The customer ----------------------------------------------------------------

@router.get("/notifications", response_model=Inbox)
def inbox(unread_only: bool = False, limit: int = Query(50, ge=1, le=100),
          offset: int = Query(0, ge=0), user: User = Depends(customer),
          service: NotificationService = Depends(get_notifications)):
    return service.inbox(user.id, unread_only, limit, offset)


@router.post("/notifications/read-all", status_code=204)
def read_all(user: User = Depends(customer),
             service: NotificationService = Depends(get_notifications)):
    service.mark_all_read(user.id)


@router.post("/notifications/{notification_id}/read", status_code=204)
def read_one(notification_id: uuid.UUID, user: User = Depends(customer),
             service: NotificationService = Depends(get_notifications)):
    service.mark_read(user.id, notification_id)


@router.put("/devices", status_code=204)
def register_device(body: DeviceBody, user: User = Depends(customer),
                    service: NotificationService = Depends(get_notifications)):
    service.register_token(user.id, body.token, body.platform)


@router.delete("/devices/{token}", status_code=204)
def remove_device(token: str, user: User = Depends(customer),
                  service: NotificationService = Depends(get_notifications)):
    service.remove_token(user.id, token)


@router.get("/notification-preferences", response_model=NotificationPreferencesOut)
def get_preferences(user: User = Depends(customer),
                    service: NotificationService = Depends(get_notifications)):
    """SET-02, SET-03: one switch for each event, all on until changed."""
    return service.preferences(user.id)


@router.put("/notification-preferences", response_model=NotificationPreferencesOut)
def put_preferences(body: NotificationPreferencesIn, user: User = Depends(customer),
                    service: NotificationService = Depends(get_notifications)):
    return service.set_preferences(user.id, {i.event: i.enabled for i in body.items})


# The crew: an inbox and a phone, no switches (CRW-NOT-03) ----------------------

@crew_router.get("/notifications", response_model=Inbox)
def crew_inbox(unread_only: bool = False, limit: int = Query(50, ge=1, le=100),
               offset: int = Query(0, ge=0), user: User = Depends(crew),
               service: NotificationService = Depends(get_notifications)):
    return service.inbox(user.id, unread_only, limit, offset)


@crew_router.post("/notifications/read-all", status_code=204)
def crew_read_all(user: User = Depends(crew),
                  service: NotificationService = Depends(get_notifications)):
    service.mark_all_read(user.id)


@crew_router.post("/notifications/{notification_id}/read", status_code=204)
def crew_read_one(notification_id: uuid.UUID, user: User = Depends(crew),
                  service: NotificationService = Depends(get_notifications)):
    service.mark_read(user.id, notification_id)


@crew_router.put("/devices", status_code=204)
def crew_register_device(body: DeviceBody, user: User = Depends(crew),
                         service: NotificationService = Depends(get_notifications)):
    service.register_token(user.id, body.token, body.platform)


@crew_router.delete("/devices/{token}", status_code=204)
def crew_remove_device(token: str, user: User = Depends(crew),
                       service: NotificationService = Depends(get_notifications)):
    service.remove_token(user.id, token)


# The admin's phone, for the alert push (ADM-ACC-09) ------------------------------

@admin_router.put("/devices", status_code=204)
def admin_register_device(body: DeviceBody, user: User = Depends(admin),
                          service: NotificationService = Depends(get_notifications)):
    service.register_token(user.id, body.token, body.platform)


@admin_router.delete("/devices/{token}", status_code=204)
def admin_remove_device(token: str, user: User = Depends(admin),
                        service: NotificationService = Depends(get_notifications)):
    service.remove_token(user.id, token)
