from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.features import registry, service
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role

admin = APIRouter(prefix="/v1/admin/features", tags=["features"])
customer = APIRouter(prefix="/v1/customer/features", tags=["features"])
crew = APIRouter(prefix="/v1/crew/features", tags=["features"])

AdminUser = Annotated[User, Depends(require_role("admin"))]
CustomerUser = Annotated[User, Depends(require_role("customer"))]
CrewUser = Annotated[User, Depends(require_role("crew"))]
Db = Annotated[Session, Depends(get_db)]


class FeatureOut(BaseModel):
    key: str
    label: str
    description: str
    group: str
    audience: str
    enabled: bool


class FeatureUpdate(BaseModel):
    enabled: bool


class AppFeaturesOut(BaseModel):
    version: str
    flags: dict[str, bool]


@admin.get("", response_model=list[FeatureOut])
def list_features(user: AdminUser, db: Db):
    return service.admin_list(db)


@admin.put("/{key}", response_model=FeatureOut)
def set_feature(key: str, body: FeatureUpdate, user: AdminUser, db: Db):
    return service.set_enabled(db, user.id, key, body.enabled)


def _app_flags(audience: str, db: Session, response: Response,
               if_none_match: str | None):
    """The flags for one audience. An unchanged set answers 304 with no body."""
    flags = service.flags_for(db, audience)
    version = service.version_of(flags)
    etag = f'"{version}"'
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    if if_none_match and etag in [t.strip() for t in if_none_match.split(",")]:
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return AppFeaturesOut(version=version, flags=flags)


@customer.get("", response_model=AppFeaturesOut, responses={304: {"description": "Unchanged"}})
def customer_features(user: CustomerUser, db: Db, response: Response,
                      if_none_match: Annotated[str | None, Header()] = None):
    return _app_flags(registry.CUSTOMER, db, response, if_none_match)


@crew.get("", response_model=AppFeaturesOut, responses={304: {"description": "Unchanged"}})
def crew_features(user: CrewUser, db: Db, response: Response,
                  if_none_match: Annotated[str | None, Header()] = None):
    return _app_flags(registry.CREW, db, response, if_none_match)
