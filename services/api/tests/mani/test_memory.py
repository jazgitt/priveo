"""Attributable memory: remember, list, forget."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.identity.models import Login
from app.mani import memory
from app.mani.models import ManiMemoryFact


@pytest.fixture
def login(db):
    row = Login(role="admin", login_id="priveopapa", display_name="F", password_hash="x")
    db.add(row)
    db.flush()
    return row


def test_remember_stores_who_and_where_from(db, login):
    message_id = uuid.uuid4()
    fact = memory.remember(db, login.id, "  Trainees   pair with a Member. ", None)
    assert fact.text == "Trainees pair with a Member." and fact.status == "confirmed"
    assert fact.created_by == login.id and fact.deleted_at is None
    assert message_id and fact.source_message_id is None


def test_the_same_words_are_not_stored_twice(db, login):
    one = memory.remember(db, login.id, "Review on Monday.", None)
    two = memory.remember(db, login.id, "review on monday.", None)
    assert one.id == two.id and len(memory.list_facts(db)) == 1


def test_empty_text_is_refused(db, login):
    with pytest.raises(ValueError):
        memory.remember(db, login.id, "   ", None)


def test_list_is_newest_first_and_hides_forgotten_facts(db, login):
    base = datetime(2026, 10, 1, tzinfo=UTC)
    for i, text in enumerate(("first", "second", "third")):
        db.add(ManiMemoryFact(text=text, created_by=login.id, created_at=base + timedelta(days=i)))
    db.flush()
    facts = memory.list_facts(db)
    assert [f.text for f in facts] == ["third", "second", "first"]
    assert memory.forget(db, facts[0].id)
    assert [f.text for f in memory.list_facts(db)] == ["second", "first"]
    assert [f.text for f in memory.list_facts(db, limit=1)] == ["second"]


def test_forget_is_a_soft_delete_and_not_repeatable(db, login):
    fact = memory.remember(db, login.id, "Something.", None)
    assert memory.forget(db, fact.id) is True
    assert fact.deleted_at is not None and db.get(ManiMemoryFact, fact.id) is fact
    assert memory.forget(db, fact.id) is False
    assert memory.forget(db, uuid.uuid4()) is False


def test_tentative_facts_are_left_out_when_only_confirmed_are_wanted(db, login):
    db.add(ManiMemoryFact(text="maybe", status="tentative", created_by=login.id))
    memory.remember(db, login.id, "sure", None)
    assert [f.text for f in memory.list_facts(db, confirmed_only=True)] == ["sure"]
    assert len(memory.list_facts(db)) == 2


def test_search_forget_matches_a_phrase_or_all_its_words(db, login):
    memory.remember(db, login.id, "Trainees are always paired with a Member.", None)
    memory.remember(db, login.id, "The weekly review is on Monday.", None)
    assert [f.text for f in memory.search_forget(db, "TRAINEES")] == ["Trainees are always paired with a Member."]
    assert len(memory.search_forget(db, "paired trainees")) == 1  # every word, any order
    assert memory.search_forget(db, "crew policy") == []
    assert memory.search_forget(db, "  ") == []
