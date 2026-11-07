"""Helpers for tests that change reference data and expect other modules to
follow it (the directory wiring)."""
from sqlalchemy.orm import Session

from app.directory import lookup
from app.directory.models import SystemSetting


def set_setting(engine, key: str, value) -> None:
    with Session(engine) as db:
        row = db.get(SystemSetting, key)
        if row is None:
            db.add(SystemSetting(key=key, value=str(value)))
        else:
            row.value = str(value)
        db.commit()
    lookup.invalidate()


def set_feature(engine, key: str, enabled: bool) -> None:
    """Switch a feature flag (app.features) on or off, as the admin Features page does."""
    from app.features import service as features
    from app.features.models import FeatureFlag

    with Session(engine) as db:
        row = db.get(FeatureFlag, key)
        if row is None:
            db.add(FeatureFlag(key=key, enabled=enabled))
        else:
            row.enabled = enabled
        db.commit()
        features.invalidate(db)
