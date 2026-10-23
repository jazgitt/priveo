"""Migration 0034 adds the new exception reasons without touching admin edits."""
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.directory import defaults
from app.directory.models import CncReason

PATH = next(Path("migrations/versions").glob("*_0034_exception_reasons.py"))
spec = importlib.util.spec_from_file_location("m0034", PATH)
m0034 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m0034)

NEW = {k for k, _ in m0034.NEW_REASONS}


def _old(db):
    for order, (key, label) in enumerate(defaults.REASONS[:5]):
        db.add(CncReason(key=key, label=label, sort_order=order))
    db.commit()


def test_defaults_include_every_new_reason_and_keep_the_old_ones():
    keys = {k for k, _ in defaults.REASONS}
    assert NEW <= keys
    assert {"car_not_in_spot", "car_locked", "customer_did_not_allow", "bad_weather",
            "other"} <= keys


def test_revision_chain():
    assert (m0034.revision, m0034.down_revision) == ("0034", "0033")


def test_inserts_missing_reasons_once_and_is_idempotent(db: Session):
    _old(db)
    assert m0034.add_missing_reasons(db.connection()) == 5
    assert m0034.add_missing_reasons(db.connection()) == 0
    db.commit()
    rows = list(db.scalars(sa.select(CncReason).order_by(CncReason.sort_order)))
    assert len(rows) == 10 and {r.key for r in rows} >= NEW
    assert [r.sort_order for r in rows] == list(range(10))
    assert all(r.active for r in rows)


def test_leaves_admin_edits_untouched(db: Session):
    _old(db)
    other = db.scalar(sa.select(CncReason).where(CncReason.key == "other"))
    other.label, other.active, other.sort_order = "Something else", False, 40
    db.add(CncReason(key="access_restricted", label="Gate blocked", sort_order=3, active=False))
    db.commit()
    assert m0034.add_missing_reasons(db.connection()) == 4
    db.commit()
    db.expire_all()
    other = db.scalar(sa.select(CncReason).where(CncReason.key == "other"))
    assert (other.label, other.active, other.sort_order) == ("Something else", False, 40)
    kept = db.scalar(sa.select(CncReason).where(CncReason.key == "access_restricted"))
    assert (kept.label, kept.active, kept.sort_order) == ("Gate blocked", False, 3)
    assert db.scalar(sa.select(sa.func.count()).select_from(CncReason)) == 10
    added = db.scalar(sa.select(CncReason).where(CncReason.key == "keys_customer_unavailable"))
    assert added.sort_order > 40


def test_does_nothing_on_an_empty_table(db: Session):
    assert m0034.add_missing_reasons(db.connection()) == 0
