import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.identity.service import User
from app.notifications.push import LoggingPushSender, PushSender
from app.notifications.service import Inbox, NotificationService
from app.platform.db import get_db
from app.platform.deps import require_role

router = APIRouter(prefix="/v1/customer", tags=["notifications"])
customer = require_role("customer")

_push = LoggingPushSender()


def get_push_sender() -> PushSender:
    """The logging fake until FCM is set up. Override to bind the real one."""
    return _push


def get_notifications(db: Session = Depends(get_db),
                      push: PushSender = Depends(get_push_sender)) -> NotificationService:
    return NotificationService(db, push)


class DeviceBody(BaseModel):
    token: str = Field(min_length=8, max_length=512)
    platform: Literal["android", "ios"]


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
