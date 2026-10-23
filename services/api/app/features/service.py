"""Reads and writes of the feature flags. Reads are cached for a few seconds
for each database engine, so a flag check on a request costs no query. A write
clears the cache. With several API instances another instance sees a change
after at most CACHE_SECONDS."""
import hashlib
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any
from weakref import WeakKeyDictionary

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory.service import audit
from app.features import registry
from app.features.models import FeatureFlag
from app.platform.errors import ApiError

CACHE_SECONDS = 10.0
_clock: Callable[[], float] = time.monotonic
_lock = threading.Lock()
_cache: "WeakKeyDictionary[Any, tuple[float, dict[str, bool]]]" = WeakKeyDictionary()


def _engine(db: Session):
    bind = db.get_bind()
    return getattr(bind, "engine", bind)


def invalidate(db: Session | None = None) -> None:
    with _lock:
        if db is None:
            _cache.clear()
        else:
            _cache.pop(_engine(db), None)


def _stored(db: Session) -> dict[str, bool]:
    engine = _engine(db)
    now = _clock()
    with _lock:
        hit = _cache.get(engine)
        if hit is not None and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    values = {row.key: row.enabled for row in db.scalars(select(FeatureFlag))}
    with _lock:
        _cache[engine] = (now, values)
    return values


def is_enabled(db: Session, key: str) -> bool:
    """Unknown keys raise, so a typo in code fails in tests, not silently."""
    if key not in registry.BY_KEY:
        raise KeyError(key)
    return _stored(db).get(key, registry.BY_KEY[key].default)


def flags_for(db: Session, audience: str) -> dict[str, bool]:
    stored = _stored(db)
    return {f.key: stored.get(f.key, f.default) for f in registry.for_audience(audience)}


def version_of(flags: dict[str, bool]) -> str:
    """A short fingerprint of the flag values, used as the ETag."""
    text = ",".join(f"{k}={int(v)}" for k, v in sorted(flags.items()))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def admin_list(db: Session) -> list[dict]:
    stored = _stored(db)
    return [
        {"key": f.key, "label": f.label, "description": f.description, "group": f.group,
         "audience": f.audience, "enabled": stored.get(f.key, f.default)}
        for f in registry.FLAGS
    ]


def set_enabled(db: Session, admin_id: uuid.UUID, key: str, enabled: bool) -> dict:
    definition = registry.BY_KEY.get(key)
    if definition is None:
        raise ApiError("not_found", "This feature was not found.", 404)
    row = db.get(FeatureFlag, key)
    old = definition.default if row is None else row.enabled
    if row is None:
        db.add(FeatureFlag(key=key, enabled=enabled, updated_by=admin_id))
    else:
        row.enabled = enabled
        row.updated_by = admin_id
    if old != enabled:
        audit(db, admin_id, "feature_flag", key, "update", {"enabled": [old, enabled]})
    db.commit()
    invalidate(db)
    return next(r for r in admin_list(db) if r["key"] == key)
