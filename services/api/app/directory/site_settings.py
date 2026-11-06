"""Scheduler settings that a site (a society) can hold for itself (SCHR-PAR-01).

A value is found in this order: the site's own row in `society_settings`, then
the global value in `system_settings`. If neither exists the read raises
`SettingMissing`; no default from code is used (SCHR-CFG-04). The defaults are
written to `system_settings` by `rule_seed`.

A save is checked against the registry (type, range) and against the other
values of the site (SCHR-CFG-05), then written with an audit row that holds the
admin, the time, the old value, the new value and the site (SCHR-CFG-06).
"""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory import settings_registry
from app.directory.models import DirectoryAudit, Society, SystemSetting
from app.platform.db import utcnow
from app.scheduling.models import SocietySetting

AUDIT_ENTITY = "society_setting"


class SettingError(ValueError):
    """A key or value that cannot be used. The message says what to enter."""


class SettingMissing(LookupError):
    """A setting has no site value and no global value."""


def _definition(key: str) -> settings_registry.SettingDef:
    definition = settings_registry.BY_KEY.get(key)
    if definition is None:
        raise SettingError(f"The setting {key} does not exist.")
    return definition


def _stored(db: Session, society_id: uuid.UUID, key: str) -> str | None:
    row = db.scalar(select(SocietySetting).where(
        SocietySetting.society_id == society_id, SocietySetting.key == key))
    if row is not None:
        return row.value
    glob = db.get(SystemSetting, key)
    return glob.value if glob is not None else None


def read(db: Session, society_id: uuid.UUID, key: str) -> Any:
    """The typed value for a site: its own, else the global one. Raises
    SettingMissing when neither exists."""
    definition = _definition(key)
    stored = _stored(db, society_id, key)
    if stored is None:
        raise SettingMissing(
            f"The setting {key} has no value for this site and no global value. "
            "Run the seed tool to add the scheduler settings.")
    try:
        return settings_registry.typed(definition, stored)
    except ValueError:
        raise SettingMissing(f"The stored value of {key} is not valid: {stored!r}.") from None


def read_all(db: Session, society_id: uuid.UUID) -> dict[str, Any]:
    """Every scheduler key for a site. Raises SettingMissing on the first gap."""
    return {d.key: read(db, society_id, d.key) for d in settings_registry.RULE_DEFINITIONS}


def own_value(db: Session, society_id: uuid.UUID, key: str) -> Any | None:
    """The site's own value, or None when the site uses the global one."""
    definition = _definition(key)
    row = db.scalar(select(SocietySetting).where(
        SocietySetting.society_id == society_id, SocietySetting.key == key))
    return settings_registry.typed(definition, row.value) if row is not None else None


def _check_consistent(db: Session, society_id: uuid.UUID, key: str, text: str) -> None:
    """Pairs that must agree (SCHR-CFG-05), using the other value as it stands."""
    def value(other: str) -> int | None:
        if other == key:
            return int(text)
        stored = _stored(db, society_id, other)
        return int(stored) if stored is not None else None

    rules = (
        ("site.break_start_minute", "site.break_end_minute",
         "The break must start before it ends."),
        ("site.reporting_minute", "site.first_job_minute",
         "The first job cannot be before the reporting time."),
        ("site.first_job_minute", "site.interior_earliest_minute",
         "Interior cannot start before the first job."),
    )
    for low, high, message in rules:
        if key not in (low, high):
            continue
        a, b = value(low), value(high)
        if a is None or b is None:
            continue
        # Break: strictly before. Others: not before.
        if (low == "site.break_start_minute" and a >= b) or (low != "site.break_start_minute" and a > b):
            raise SettingError(message)


def write(db: Session, society_id: uuid.UUID, key: str, raw: Any,
          admin_id: uuid.UUID | None) -> Any:
    """Save a site's own value. Raises SettingError with a message for the admin."""
    definition = _definition(key)
    if not definition.site:
        raise SettingError(f"The setting {key} is the same for all sites and cannot be set for one.")
    if db.get(Society, society_id) is None:
        raise SettingError("This site was not found.")
    text = settings_registry.parse(definition, raw)  # ValueError with a message
    if definition.kind == "int":
        _check_consistent(db, society_id, key, text)
    before = _stored(db, society_id, key)
    row = db.scalar(select(SocietySetting).where(
        SocietySetting.society_id == society_id, SocietySetting.key == key))
    if row is None:
        db.add(SocietySetting(society_id=society_id, key=key, value=text,
                              updated_by=admin_id, updated_at=utcnow()))
    else:
        row.value, row.updated_by, row.updated_at = text, admin_id, utcnow()
    db.add(DirectoryAudit(admin_login_id=admin_id, entity=AUDIT_ENTITY, entity_id=key,
                          action="update", society_id=society_id,
                          detail={"value": [before, text]}))
    db.commit()
    return settings_registry.typed(definition, text)
