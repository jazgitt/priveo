"""The Scheduling rules panel's API (SCHS-18): the per-site values, as the admin
reads and edits them. Any `site.*` key of the registry is listed from its
metadata, so a later story adds a key and no code here. Values travel as the
stored text ("300", "true", "5,6"); the registry checks type and range, and a
save writes an audit row (`directory.site_settings.write`)."""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.directory import settings_registry, site_settings
from app.directory.models import Society, SystemSetting
from app.directory.settings_registry import SettingDef
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError

router = APIRouter(prefix="/v1/admin/scheduling/site-settings", tags=["scheduling"])

PREFIX = "site."


class SiteSettingOut(BaseModel):
    key: str
    label: str
    kind: str  # int | bool | weekdays | time | text
    # The value every site starts from, and the site's own value (null: none).
    default_value: str
    site_value: str | None
    value: str  # what the site uses now
    minimum: int | None = None
    maximum: int | None = None


class SiteSettingIn(BaseModel):
    society_id: uuid.UUID
    value: str


def _panel_keys() -> list[SettingDef]:
    return [d for d in settings_registry.RULE_DEFINITIONS if d.site and d.key.startswith(PREFIX)]


def _text(db: Session, society_id: uuid.UUID, d: SettingDef) -> SiteSettingOut:
    glob = db.get(SystemSetting, d.key)
    default_value = glob.value if glob is not None else settings_registry.default_for(d.key)
    own = site_settings.own_value(db, society_id, d.key)
    stored_own = None if own is None else _to_text(d, own)
    return SiteSettingOut(
        key=d.key, label=d.label, kind=d.kind, default_value=default_value,
        site_value=stored_own, value=stored_own if stored_own is not None else default_value,
        minimum=d.minimum if d.kind == "int" else None,
        maximum=d.maximum if d.kind == "int" else None)


def _to_text(d: SettingDef, value) -> str:
    if d.kind == "bool":
        return "true" if value else "false"
    if d.kind == "weekdays":
        return ",".join(str(v) for v in value)
    return str(value)


def _society(db: Session, society_id: uuid.UUID) -> None:
    if db.get(Society, society_id) is None:
        raise ApiError("not_found", "This site was not found.", 404)


@router.get("", response_model=list[SiteSettingOut])
def list_site_settings(society_id: uuid.UUID, _: User = Depends(require_role("admin")),
                       db: Session = Depends(get_db)):
    """Every per-site scheduling value with its default, the site's own value and its range."""
    _society(db, society_id)
    return [_text(db, society_id, d) for d in _panel_keys()]


@router.put("/{key}", response_model=SiteSettingOut)
def put_site_setting(key: str, body: SiteSettingIn, user: User = Depends(require_role("admin")),
                     db: Session = Depends(get_db)):
    """Saves the site's own value. A value outside the rules is refused with the message to show."""
    d = next((x for x in _panel_keys() if x.key == key), None)
    if d is None:
        raise ApiError("not_found", "This setting does not exist.", 404)
    _society(db, body.society_id)
    try:
        site_settings.write(db, body.society_id, key, body.value, user.id)
    except (site_settings.SettingError, ValueError) as e:
        db.rollback()
        raise ApiError("validation_failed", str(e), 422, {"value": str(e)}) from None
    return _text(db, body.society_id, d)
