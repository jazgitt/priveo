"""General search of the Audit trail (ADM-SET-09)."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.directory.models import DirectoryAudit
from app.identity.models import Login
from tests.test_api import auth, login

URL = "/v1/admin/directory/audit"


def _row(db, **kw):
    base = dict(entity="plan", entity_id="rec-0001", action="update", detail={}, society_id=None)
    base.update(kw)
    db.add(DirectoryAudit(**base))
    db.commit()


def _get(client, h, **params):
    r = client.get(URL, params=params, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _setup(client, db):
    h = auth(login(client, "admin")["access_token"])
    # Rows written by the sign-in are not wanted here.
    for r in db.scalars(select(DirectoryAudit)).all():
        db.delete(r)
    db.commit()
    actor = db.scalar(select(Login).where(Login.role == "admin"))
    _row(db, entity="feature_flag", entity_id="flag-zeta", action="toggle", admin_login_id=actor.id,
         detail={"enabled": [False, True]}, at=datetime(2026, 10, 10, 5, 0, tzinfo=UTC))
    _row(db, entity="plan", entity_id="plan-alpha", action="create", detail={"name": "Gold Wash"},
         at=datetime(2026, 10, 11, 5, 0, tzinfo=UTC))
    _row(db, entity="setting", entity_id="100%_done", action="update", detail={"note": "50% off"},
         at=datetime(2026, 10, 12, 5, 0, tzinfo=UTC))
    return h, actor


def test_search_needs_three_characters_ADM_SET_09(client, db):
    h, _ = _setup(client, db)
    for q in ("ab", "  a ", ""):
        r = client.get(URL, params={"q": q}, headers=h)
        assert r.status_code == 422 and r.json()["code"] == "validation_failed", q


def test_search_matches_each_column_ADM_SET_09(client, db):
    h, actor = _setup(client, db)
    for q, expected in [
        ("2026-10-10", "flag-zeta"),      # when (ISO date)
        ("10-Oct-26", "flag-zeta"),       # when (as shown)
        ("feature flag", "flag-zeta"),    # entity, underscore as space
        ("feature_flag", "flag-zeta"),
        ("toggle", "flag-zeta"),          # action
        (str(actor.id), "flag-zeta"),     # admin login id, with dashes
        (str(actor.id).replace("-", ""), "flag-zeta"),
        ("enabled", "flag-zeta"),         # detail field name
        ("gold wash", "plan-alpha"),      # detail value
        ("plan-alp", "plan-alpha"),       # record id
    ]:
        items = _get(client, h, q=q)["items"]
        assert [i["entity_id"] for i in items] == [expected], q


def test_search_is_case_insensitive_ADM_SET_09(client, db):
    h, _ = _setup(client, db)
    assert [i["entity_id"] for i in _get(client, h, q="GOLD wASh")["items"]] == ["plan-alpha"]


def test_search_wildcards_are_literal_ADM_SET_09(client, db):
    h, _ = _setup(client, db)
    assert _get(client, h, q="%%%")["total"] == 0
    assert _get(client, h, q="___")["total"] == 0
    assert [i["entity_id"] for i in _get(client, h, q="0%_d")["items"]] == ["100%_done"]
    assert [i["entity_id"] for i in _get(client, h, q="50% off")["items"]] == ["100%_done"]


def test_search_combines_with_filters_and_paging_ADM_SET_09(client, db):
    h, _ = _setup(client, db)
    for i in range(5):
        _row(db, entity="plan", entity_id=f"bulk-{i}", at=datetime(2026, 10, 20 + i, 5, 0, tzinfo=UTC))
    body = _get(client, h, q="bulk", limit=2, offset=2)
    assert body["total"] == 5 and len(body["items"]) == 2
    assert _get(client, h, q="bulk", entity="setting")["total"] == 0
    assert _get(client, h, q="bulk", date_from="2026-10-22", date_to="2026-10-23")["total"] == 2
    assert _get(client, h, q="plan", entity="plan")["total"] == 6
    assert _get(client, h, q="nothing-like-this-xyz")["items"] == []


def test_search_keeps_site_rule_and_actor_filter_ADM_SET_09(client, db):
    h, actor = _setup(client, db)
    assert _get(client, h, q="flag", actor_id=str(actor.id))["total"] == 1
    assert _get(client, h, q="flag", actor_id=str(uuid.uuid4()))["total"] == 0
    # A site that owns no rows still sees the rows that apply to all sites.
    assert _get(client, h, q="flag", society_id=str(uuid.uuid4()))["total"] == 1
