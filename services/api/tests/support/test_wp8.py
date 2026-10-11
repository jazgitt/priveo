"""The FAQ (SUP-05) and the six check-in categories (CHK-02, CHK-03)."""
import os
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.platform.db import Base, make_engine
from app.support.defaults import CHECKIN_CATEGORIES

OWNER_CATEGORIES = [
    "Likelihood to recommend", "Value for money", "Schedule fit",
    "Crew professionalism", "App and support", "Interest in add-ons",
]


def test_faq_is_an_ordered_list_for_customers_only(client, customer, crew):
    r = client.get("/v1/customer/faq", headers=customer)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 5
    assert all(i["question"] and i["answer"] for i in items)
    topics = " ".join(i["question"].lower() for i in items)
    assert "billing" in topics and "skip" in topics and "damage" in topics
    assert client.get("/v1/customer/faq", headers=crew).status_code == 403
    assert client.get("/v1/customer/faq").status_code in (401, 403)


def test_checkin_categories_are_the_six_owner_categories(client, customer):
    o = client.get("/v1/customer/support/options", headers=customer).json()
    assert [c["name"] for c in o["checkin_categories"]] == OWNER_CATEGORIES
    assert [n for n, _ in CHECKIN_CATEGORIES] == OWNER_CATEGORIES


def test_migration_tops_up_an_existing_checkin_list(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'w.db'}"
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    command.upgrade(config, "0010")
    old = [("Likelihood to recommend",
            "How likely you are to recommend Priveo to your neighbours."),
           ("Value for money", "The admin edited this."),
           ("Schedule fit",
            "Whether the service cutoff time and the interior day still work for you.")]
    with engine.begin() as c:
        for order, (name, description) in enumerate(old):
            c.execute(text(
                "INSERT INTO support_options (id, kind, name, description, sort_order, active)"
                " VALUES (:i, 'checkin_category', :n, :d, :o, :a)"),
                {"i": uuid.uuid4().hex if url.startswith("sqlite") else str(uuid.uuid4()),
                 "n": name, "d": description, "o": order, "a": True})
    command.upgrade(config, "head")
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT name, description FROM support_options WHERE kind='checkin_category'"
            " ORDER BY sort_order")).all()
    assert [r[0] for r in rows] == OWNER_CATEGORIES
    descriptions = dict(rows)
    assert descriptions["Value for money"] == "The admin edited this."
    assert descriptions["Likelihood to recommend"] == CHECKIN_CATEGORIES[0][1]
    command.downgrade(config, "base")
    engine.dispose()
