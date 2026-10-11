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
