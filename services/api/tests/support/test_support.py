import os
from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select

import app.support.models  # noqa: F401  (registers the tables)
from app.customers.models import Subscription
from app.identity.models import Login
from app.identity.service import hash_password
from app.platform.clock import today_ist
from app.platform.db import Base, make_engine, utcnow
from app.support import alerts
from app.support.models import Complaint
from app.support.service import SupportService, cycle_for, display_id
from tests.test_api import auth


def raise_complaint(client, headers, **changes):
    body = {"category": "Cleaning quality", "description": "Streaks on the glass", **changes}
    return client.post("/v1/customer/complaints", json=body, headers=headers)


# Complaints -----------------------------------------------------------

def test_complaint_goes_from_customer_to_admin_and_back(client, customer, admin):
    r = raise_complaint(client, customer)
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["display_id"] == "#C-0001"
    assert c["status"] == "Raised"
    assert c["visit_id"] is None

    # The admin is alerted (ADM-CMP-08), in the list, by push and by email.
    a = client.get("/v1/admin/alerts", headers=admin).json()
    assert a["unread_count"] == 1
    assert a["items"][0]["kind"] == "complaint_raised"
    assert a["items"][0]["ref_id"] == c["id"]
    assert len(client.push.admin) == 1 and len(client.email.sent) == 1

    listed = client.get("/v1/admin/complaints", headers=admin).json()
    assert [x["number"] for x in listed] == [1]
    assert listed[0]["customer_name"] == "Aarav Mehta"
    assert listed[0]["society"] == "Priveo Demo Society"
    assert listed[0]["overdue"] is False

    # Status change, with a note. The customer is pushed (CMP-04).
    r = client.post(f"/v1/admin/complaints/{c['id']}/status", headers=admin,
                    json={"status": "In progress", "note": "Supervisor visit booked"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "In progress"
    assert len(client.push.customer) == 1
    assert client.push.customer[0][1] == "Complaint update"
    assert "Supervisor visit booked" in client.push.customer[0][2]

    mine = client.get("/v1/customer/complaints", headers=customer).json()
    assert mine[0]["status"] == "In progress"
    assert mine[0]["latest_note"] == "Supervisor visit booked"

    # A note on its own, then the customer's reply.
    client.post(f"/v1/admin/complaints/{c['id']}/notes", headers=admin,
                json={"note": "Re-cleaned same day"})
    assert len(client.push.customer) == 2
    r = client.post(f"/v1/customer/complaints/{c['id']}/messages", headers=customer,
                    json={"note": "Thank you, it looks good"})
    assert r.status_code == 200
    thread = r.json()["updates"]
    assert [(u["author_role"], u["note"]) for u in thread] == [
        ("admin", "Supervisor visit booked"), ("admin", "Re-cleaned same day"),
        ("customer", "Thank you, it looks good")]
    assert thread[0]["status"] == "In progress"
    assert client.get("/v1/admin/alerts", headers=admin).json()["unread_count"] == 2

    # Resolved. The customer can no longer reply.
    client.post(f"/v1/admin/complaints/{c['id']}/status", headers=admin,
                json={"status": "Resolved"})
    r = client.post(f"/v1/customer/complaints/{c['id']}/messages", headers=customer,
                    json={"note": "One more thing"})
    assert r.status_code == 409 and r.json()["code"] == "complaint_resolved"
    assert client.get("/v1/customer/support/contact", headers=customer
                      ).json()["complaints_in_progress"] == 0


def test_complaint_validation(client, customer):
    r = raise_complaint(client, customer, category="Weather")
    assert r.status_code == 422 and r.json()["fields"]["category"] == "Choose what went wrong."
    assert raise_complaint(client, customer, description="   ").status_code == 422
    assert client.post("/v1/customer/complaints", headers=customer,
                       json={"description": "x"}).status_code == 422


def test_numbers_count_up_and_newest_is_first(client, customer):
    raise_complaint(client, customer, description="first")
    raise_complaint(client, customer, description="second")
    mine = client.get("/v1/customer/complaints", headers=customer).json()
    assert [c["display_id"] for c in mine] == ["#C-0002", "#C-0001"]


def test_a_customer_sees_only_their_own_complaints(client, customer, db):
    c = raise_complaint(client, customer).json()
    db.add(Login(role="customer", login_id="nobody@example.com", display_name="Nobody",
                 password_hash=hash_password("pw-nobody1")))
    db.commit()
    other = auth(client.post("/v1/auth/login", json={
        "login_id": "nobody@example.com", "password": "pw-nobody1"}).json()["access_token"])
    # No customer record behind that login.
    assert client.get("/v1/customer/complaints", headers=other).status_code == 404
    assert client.get(f"/v1/customer/complaints/{c['id']}", headers=other).status_code == 404


def test_roles_are_enforced(client, customer, admin, crew):
    assert client.get("/v1/admin/complaints", headers=customer).status_code == 403
    assert client.get("/v1/admin/alerts", headers=crew).status_code == 403
    assert client.get("/v1/customer/complaints", headers=admin).status_code == 403
    assert client.get("/v1/crew/ratings", headers=crew).status_code == 404
    assert client.get("/v1/customer/complaints").status_code == 401


def test_overdue_complaint_is_highlighted_and_alerted_once(client, customer, admin, db):
    raise_complaint(client, customer)
    complaint = db.scalar(select(Complaint))
    complaint.created_at = utcnow() - timedelta(hours=5)
    db.commit()
    assert client.get("/v1/admin/complaints", headers=admin).json()[0]["overdue"] is True

    service = SupportService(db, client.push, client.email)
    assert service.alert_overdue_complaints() == 1
    assert service.alert_overdue_complaints() == 0
    kinds = [a["kind"] for a in client.get("/v1/admin/alerts", headers=admin).json()["items"]]
    assert sorted(kinds) == ["complaint_overdue", "complaint_raised"]


def test_admin_filters_complaints(client, customer, admin):
    a = raise_complaint(client, customer).json()
    raise_complaint(client, customer, category="Billing")
    client.post(f"/v1/admin/complaints/{a['id']}/status", headers=admin,
                json={"status": "Resolved"})
    by_status = client.get("/v1/admin/complaints?status=Resolved", headers=admin).json()
    assert [c["id"] for c in by_status] == [a["id"]]
    by_cat = client.get("/v1/admin/complaints?category=Billing", headers=admin).json()
    assert len(by_cat) == 1 and by_cat[0]["category"] == "Billing"
    bad = client.post(f"/v1/admin/complaints/{a['id']}/status", headers=admin,
                      json={"status": "Closed"})
    assert bad.status_code == 422


def test_a_status_change_without_a_change_sends_nothing(client, customer, admin):
    c = raise_complaint(client, customer).json()
    client.post(f"/v1/admin/complaints/{c['id']}/status", headers=admin,
                json={"status": "Raised"})
    assert client.push.customer == []


# Contact and lists ----------------------------------------------------

def test_contact_comes_from_settings(client, customer, monkeypatch):
    from app.support.config import get_support_settings
    monkeypatch.setenv("SUPPORT_HELPLINE", "+911234567890")
    get_support_settings.cache_clear()
    try:
        r = client.get("/v1/customer/support/contact", headers=customer).json()
        assert r["helpline"] == "+911234567890"
        assert r["hours"] == "6 AM to 10 PM"
        assert r["whatsapp"]
    finally:
        monkeypatch.delenv("SUPPORT_HELPLINE")
        get_support_settings.cache_clear()


def test_a_saved_helpline_and_checkin_window_win_over_the_environment(
        client, customer, engine):
    from tests.directory_helpers import set_setting
    set_setting(engine, "support.helpline", "+919999999999")
    set_setting(engine, "support.hours", "8 AM to 8 PM")
    r = client.get("/v1/customer/support/contact", headers=customer).json()
    assert r["helpline"] == "+919999999999" and r["hours"] == "8 AM to 8 PM"


def test_options_start_with_the_owner_lists_and_admin_edits_them(client, customer, admin):
    o = client.get("/v1/customer/support/options", headers=customer).json()
    assert len(o["issue_categories"]) == 6
    assert len(o["feedback_categories"]) == 9
    assert [t["name"] for t in o["positive_tags"]] == ["Spotless", "On time", "Great tyre finish"]
    assert [c["name"] for c in o["checkin_categories"]][0] == "Likelihood to recommend"

    added = client.post("/v1/admin/support/options", headers=admin, json={
        "kind": "positive_tag", "name": "Friendly crew"})
    assert added.status_code == 201
    assert client.post("/v1/admin/support/options", headers=admin, json={
        "kind": "positive_tag", "name": "Friendly crew"}).status_code == 409
    spotless = next(t for t in o["positive_tags"] if t["name"] == "Spotless")
    client.patch(f"/v1/admin/support/options/{spotless['id']}", headers=admin,
                 json={"active": False})
    names = [t["name"] for t in client.get(
        "/v1/customer/support/options", headers=customer).json()["positive_tags"]]
    assert names == ["On time", "Great tyre finish", "Friendly crew"]
    # A deactivated entry stays in the admin's list (ADM-FDB-07).
    assert any(x["name"] == "Spotless" and not x["active"] for x in client.get(
        "/v1/admin/support/options", headers=admin).json())


# Feedback and ratings -------------------------------------------------


def test_renaming_an_option_keeps_earlier_feedback_under_its_original_name(client, customer, admin):
    original = client.get('/v1/customer/support/options', headers=customer).json()['feedback_categories'][0]
    assert client.post('/v1/customer/feedback', headers=customer,
        json={'category': original['name'], 'rating': 4}).status_code == 201
    assert client.patch(f"/v1/admin/support/options/{original['id']}", headers=admin,
                        json={'name': 'Renamed category'}).status_code == 200
    earlier = client.get('/v1/admin/feedback', headers=admin).json()
    assert earlier[0]['category'] == original['name']
    current = client.get('/v1/customer/support/options', headers=customer).json()['feedback_categories']
    assert any(entry['name'] == 'Renamed category' for entry in current)

def test_feedback_needs_a_rating_or_a_comment(client, customer, admin):
    r = client.post("/v1/customer/feedback", headers=customer, json={"category": "Glass"})
    assert r.status_code == 422  # FDBK-07
    r = client.post("/v1/customer/feedback", headers=customer, json={
        "category": "Glass", "rating": 4, "comment": "Mostly good",
        "testimonial_permission": True})
    assert r.status_code == 201
    r = client.post("/v1/customer/feedback", headers=customer, json={"comment": "Hello"})
    assert r.status_code == 201
    assert client.post("/v1/customer/feedback", headers=customer, json={
        "category": "Nonsense", "rating": 3}).status_code == 422

    items = client.get("/v1/admin/feedback", headers=admin).json()
    assert len(items) == 2
    marked = [i for i in items if i["testimonial_permission"]]
    assert marked[0]["customer_name"] == "Aarav Mehta"
    assert len(client.get("/v1/admin/feedback?rating=4", headers=admin).json()) == 1
    assert len(client.get("/v1/admin/feedback?category=Glass", headers=admin).json()) == 1


def test_visit_rating_tags_follow_the_stars(client, customer, admin, crew, rating_visit):
    put = f"/v1/customer/visits/{rating_visit.id}/rating"
    ok = client.put(put, headers=customer, json={"rating": 5, "tags": ["Spotless"]})
    assert ok.status_code == 200 and ok.json()["tags"] == ["Spotless"]
    # Issue tags are not allowed at 5 stars, and positive tags are not allowed below.
    assert client.put(put, headers=customer, json={"rating": 5, "tags": ["Glass"]}
                      ).status_code == 422
    assert client.put(put, headers=customer, json={"rating": 3, "tags": ["Spotless"]}
                      ).status_code == 422
    # A new rating replaces the old one.
    r = client.put(put, headers=customer, json={
        "rating": 3, "tags": ["Glass", "Timing"], "comment": "Late and streaky"})
    assert r.status_code == 200
    assert client.put(put, headers=customer, json={"rating": 6}).status_code == 422

    report = client.get("/v1/admin/ratings", headers=admin).json()
    assert report["count"] == 1 and report["average"] == 3.0
    assert report["tag_counts"] == {"Glass": 1, "Timing": 1}
    assert report["items"][0]["visit_id"] == str(rating_visit.id)

    # The crew app shows no ratings (CRW-RAT-01): there is no crew route.
    assert client.get("/v1/crew/ratings", headers=crew).status_code == 404


def test_admin_complaint_lists_vehicle_and_opens_owned_linked_visit(client, customer, admin, rating_visit):
    result = raise_complaint(client, customer, visit_id=str(rating_visit.id))
    assert result.status_code == 201, result.text
    cid = result.json()["id"]
    listed = client.get("/v1/admin/complaints", headers=admin).json()
    assert listed[0]["vehicle"] and " · " in listed[0]["vehicle"]
    visit = client.get(f"/v1/admin/complaints/{cid}/visit", headers=admin)
    assert visit.status_code == 200 and visit.json()["id"] == str(rating_visit.id)
    assert client.get(f"/v1/admin/complaints/{cid}/visit", headers=customer).status_code == 403


# Check-in -------------------------------------------------------------

def make_due(db, days_to_renewal=3):
    """Moves the demo customer's first subscription so its renewal is near."""
    sub = db.scalars(select(Subscription).order_by(Subscription.monthly_price_rupees.desc())
                     ).first()
    sub.first_service_date = today_ist() - timedelta(days=30 - days_to_renewal)
    db.commit()
    return sub


def test_cycle_for():
    first = today_ist() - timedelta(days=65)
    start, renewal = cycle_for(first, today_ist())
    assert start == first + timedelta(days=60) and renewal == start + timedelta(days=30)
    assert cycle_for(today_ist() + timedelta(days=1), today_ist()) is None


def test_checkin_is_due_in_the_last_four_days_and_saved_once(client, customer, admin, db):
    assert client.get("/v1/customer/checkins/pending", headers=customer).json() == []
    sub = make_due(db, 3)
    pending = client.get("/v1/customer/checkins/pending", headers=customer).json()
    assert len(pending) == 1 and pending[0]["subscription_id"] == str(sub.id)
    assert "Hyundai Creta" in pending[0]["vehicle_label"]

    r = client.post("/v1/customer/checkins", headers=customer, json={
        "subscription_id": str(sub.id), "comment": "All good",
        "answers": [{"category": "Value for money", "rating": 4},
                    {"category": "Schedule fit", "rating": 5}]})
    assert r.status_code == 201, r.text
    # Given for this cycle, so the Home card goes away (CHK-08).
    assert client.get("/v1/customer/checkins/pending", headers=customer).json() == []
    again = client.post("/v1/customer/checkins", headers=customer, json={
        "subscription_id": str(sub.id), "answers": [{"category": "Value for money", "rating": 4}]})
    assert again.status_code == 409 and again.json()["code"] == "checkin_not_due"

    report = client.get("/v1/admin/checkins", headers=admin).json()
    assert report["category_averages"] == {"Value for money": 4.0, "Schedule fit": 5.0}
    assert report["items"][0]["customer_name"] == "Aarav Mehta"


def test_a_changed_checkin_window_is_the_one_used(client, customer, db, engine):
    from tests.directory_helpers import set_setting
    make_due(db, 10)
    assert client.get("/v1/customer/checkins/pending", headers=customer).json() == []
    set_setting(engine, "support.checkin_days_before", 12)
    assert len(client.get("/v1/customer/checkins/pending", headers=customer).json()) == 1


def test_checkin_rules(client, customer, db):
    sub = make_due(db, 10)  # Not yet in the last four days.
    assert client.get("/v1/customer/checkins/pending", headers=customer).json() == []
    body = {"subscription_id": str(sub.id),
            "answers": [{"category": "Value for money", "rating": 4}]}
    assert client.post("/v1/customer/checkins", headers=customer, json=body).status_code == 409
    make_due(db, 2)
    bad = {**body, "answers": [{"category": "Made up", "rating": 4}]}
    assert client.post("/v1/customer/checkins", headers=customer, json=bad).status_code == 422
    empty = {**body, "answers": []}  # CHK-07
    assert client.post("/v1/customer/checkins", headers=customer, json=empty).status_code == 422
    assert client.post("/v1/customer/checkins", headers=customer, json=body).status_code == 201


def test_checkin_push_goes_out_four_days_before_renewal(client, db):
    service = SupportService(db, client.push, client.email)
    assert service.notify_due_checkins() == 0
    make_due(db, 4)
    assert service.notify_due_checkins() == 1
    assert client.push.customer[0][1] == "Monthly check-in"


# Alerts ---------------------------------------------------------------

def test_alert_list_and_read_state(client, admin, db):
    first = alerts.raise_alert(db, "payment_initiated", "Payment marked paid", "Flat A-101",
                               push=client.push, email=client.email)
    alerts.raise_alert(db, "skip_after_freeze", "Skip after freeze", push=client.push,
                       email=client.email)
    r = client.get("/v1/admin/alerts", headers=admin).json()
    assert r["unread_count"] == 2 and r["items"][0]["title"] == "Skip after freeze"

    assert client.post(f"/v1/admin/alerts/{first.id}/read", headers=admin).status_code == 204
    r = client.get("/v1/admin/alerts?unread_only=true", headers=admin).json()
    assert r["unread_count"] == 1 and len(r["items"]) == 1
    assert client.post("/v1/admin/alerts/read-all", headers=admin).status_code == 204
    assert client.get("/v1/admin/alerts", headers=admin).json()["unread_count"] == 0
    missing = client.post("/v1/admin/alerts/00000000-0000-0000-0000-000000000000/read",
                          headers=admin)
    assert missing.status_code == 404


def test_a_failing_notifier_does_not_lose_the_alert(db):
    class Broken:
        def push_admin(self, title, body):
            raise RuntimeError("no network")

    alerts.raise_alert(db, "x", "Title", push=Broken())
    assert alerts.unread_count(db) == 1


def test_display_id():
    assert display_id(7) == "#C-0007"


# Migration ------------------------------------------------------------

def test_migration_builds_the_support_tables(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 's.db'}"
    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    command.upgrade(config, "head")
    built = inspect(engine)
    mine = [t for t in Base.metadata.sorted_tables
            if t.name in {"support_options", "complaints", "complaint_updates", "feedback",
                          "visit_ratings", "checkins", "admin_alerts"}]
    assert len(mine) == 7
    for table in mine:
        columns = {c["name"] for c in built.get_columns(table.name)}
        assert columns == {c.name for c in table.columns}, table.name
    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()


@pytest.mark.parametrize("rating", [0, 6])
def test_rating_bounds(client, customer, rating):
    r = client.put("/v1/customer/visits/v/rating", headers=customer, json={"rating": rating})
    assert r.status_code == 422
