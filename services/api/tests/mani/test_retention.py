"""D11: conversations are deleted 90 days after they were last used. Usage stays."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.identity.models import Login
from app.mani.config import get_mani_settings
from app.mani.models import ManiConversation, ManiMessage, ManiModelUsage, ManiRun
from app.mani.retention import delete_old_conversations
from app.notifications.cron import get_cron_settings

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
CRON = "/v1/internal/cron/mani-retention"


@pytest.fixture
def founder_id(db, client):
    return db.scalars(select(Login.id).where(Login.login_id == "priveopapa")).one()


def conversation(db, login_id, age_days, with_content=True):
    c = ManiConversation(login_id=login_id, title=f"{age_days} days old")
    c.created_at = c.updated_at = NOW - timedelta(days=age_days)
    db.add(c)
    db.commit()
    if with_content:
        run = ManiRun(conversation_id=c.id, status="succeeded")
        db.add(run)
        db.commit()
        db.add(ManiMessage(conversation_id=c.id, run_id=run.id, role="user", content="hello"))
        db.add(ManiModelUsage(run_id=run.id, kind="chat", backend="local", model="m", cost_usd=Decimal("0.02"),
                              created_at=NOW - timedelta(days=age_days)))
        db.commit()
    return c


def test_89_days_are_kept_and_91_are_deleted(db, founder_id):
    keep = conversation(db, founder_id, 89)
    old = conversation(db, founder_id, 91)
    assert delete_old_conversations(db, NOW, 90) == 1
    db.expire_all()
    assert db.get(ManiConversation, keep.id) is not None and db.get(ManiConversation, old.id) is None
    assert [m.conversation_id for m in db.scalars(select(ManiMessage))] == [keep.id]
    assert [r.conversation_id for r in db.scalars(select(ManiRun))] == [keep.id]
    # Usage is counts and cost, not content: all of it stays, the deleted run's link is cleared.
    usage = db.scalars(select(ManiModelUsage)).all()
    assert len(usage) == 2 and sum(u.run_id is None for u in usage) == 1


def test_the_boundary_and_a_repeat_run(db, founder_id):
    exactly = conversation(db, founder_id, 90, with_content=False)  # not older than 90 days
    assert delete_old_conversations(db, NOW, 90) == 0
    assert db.get(ManiConversation, exactly.id) is not None
    assert delete_old_conversations(db, NOW + timedelta(seconds=1), 90) == 1
    assert delete_old_conversations(db, NOW + timedelta(seconds=1), 90) == 0


def test_the_days_come_from_the_setting(db, founder_id):
    conversation(db, founder_id, 40, with_content=False)
    assert delete_old_conversations(db, NOW, 30) == 1


def test_the_default_is_90_days():
    assert get_mani_settings().conversation_retention_days == 90


@pytest.fixture
def cron_secret(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "cron-test-secret")
    get_cron_settings.cache_clear()
    yield "cron-test-secret"
    get_cron_settings.cache_clear()


def test_the_cron_route_needs_the_secret(client, db, founder_id, cron_secret):
    old_id = conversation(db, founder_id, 200).id
    assert client.post(CRON).status_code == 401
    assert client.post(CRON, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get(CRON).status_code == 401
    db.expire_all()
    assert db.get(ManiConversation, old_id) is not None  # nothing happened

    r = client.post(CRON, headers={"Authorization": f"Bearer {cron_secret}"})
    assert r.status_code == 200, r.text
    assert r.json()["job"] == "mani-retention" and r.json()["result"] == {"deleted": 1}
    db.expire_all()
    assert db.get(ManiConversation, old_id) is None


def test_the_cron_route_is_off_without_a_secret(client, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "")
    get_cron_settings.cache_clear()
    assert client.post(CRON, headers={"Authorization": "Bearer x"}).status_code == 503
    get_cron_settings.cache_clear()


def test_the_cron_route_is_not_in_the_public_contract(client):
    assert not any("/internal" in p for p in client.app.openapi()["paths"])
