"""Adds the scheduler settings that have no row yet, with the defaults of the
registry (SCHR-CFG-03). Idempotent and safe at every deploy: a row that exists
is never changed, so an edited value stays."""
from sqlalchemy.orm import Session

from app.directory import settings_registry
from app.directory.models import SystemSetting


def seed_rule_keys(db: Session) -> int:
    """Returns how many rows were added."""
    added = 0
    for definition in settings_registry.RULE_DEFINITIONS:
        if db.get(SystemSetting, definition.key) is None:
            db.add(SystemSetting(key=definition.key,
                                 value=settings_registry.default_for(definition.key)))
            added += 1
    if added:
        db.flush()
    return added
