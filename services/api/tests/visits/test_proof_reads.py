"""Proof reaches the customer: signed read URLs, the checklist and the crew card
on the visit details, vehicle and profile photos (SVC-01 to SVC-06, HIST-01,
HOME-03, CRW-SCH-03, CRW-PRF-01, CRW-SVC-12)."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.customer_reads as customer_reads
import app.media.store as store_module
import app.notifications as notifications
import app.support as support
from app import media, visits
from app.identity.models import Login
from app.identity.service import hash_password
from app.main import create_app
from app.media.models import MediaUpload
from app.media.store import get_object_store
from app.platform.db import get_db, utcnow
from app.support.models import VisitRating
from tests.visits.conftest import PASSWORD, upload_file
from tests.visits.test_crew_jobs import tick_all


@pytest.fixture
def client(settings, engine, store, monkeypatch) -> TestClient:
    # The services build read URLs with the process store: use the test one.
    monkeypatch.setattr(store_module, "_store", store)

    def _get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app = create_app()
    visits.register(app)
    media.register(app)
    notifications.register(app)
    support.register(app)
    customer_reads.register(app)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_object_store] = lambda: store
    return TestClient(app)


def _login(client, login_id):
    r = client.post("/v1/auth/login", json={"login_id": login_id, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def crew_headers(client, make_crew):
    return lambda member: _login(client, "9000000010")


@pytest.fixture
def owner_headers(client, db):
    login = db.query(Login).filter_by(login_id="owner@priveo.test").one()
    login.password_hash = hash_password(PASSWORD)
    db.commit()
    return _login(client, "owner@priveo.test")


def finish_job(client, headers, jid):
    tick_all(client, headers, jid)
    for kind, stage in (("photo", "Before"), ("photo", "After"), ("video", "During")):
        upload_file(client, headers, jid, kind=kind, stage=stage)
    done = client.post(f"/v1/crew/jobs/{jid}/complete", headers=headers)
    assert done.status_code == 200, done.text


def test_customer_sees_proof_checklist_crew_and_finish_time(
        client, make_crew, crew_headers, owner_headers, new_visit):
    ravi = make_crew("9000000010", "Ravi Kumar")
    visit, (job,) = new_visit(assigned=ravi)
    finish_job(client, crew_headers(ravi), str(job.id))

    r = client.get(f"/v1/customer/visits/{visit.id}", headers=owner_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "Completed"
    assert body["finished_at"] is not None
    j = body["jobs"][0]
    assert j["crew_name"] == "Ravi"
    assert j["crew_society"] == "Green Meadows"
    assert j["checklist_total"] == 5 and j["checklist_done"] == 5
    assert all(c["checked_at"] for c in j["checklist"])
    # Before, During, After, in that order.
    assert [(p["kind"], p["stage"]) for p in j["proof"]] == [
        ("photo", "Before"), ("video", "During"), ("photo", "After")]
    assert "9000000010" not in r.text

    # The signed URL serves the stored bytes, with range support for video.
    url = j["proof"][0]["url"]
    got = client.get(url)
    assert got.status_code == 200
    assert got.content == b"x" * 2048
    assert got.headers["content-type"].startswith("image/jpeg")
    part = client.get(url, headers={"Range": "bytes=0-9"})
    assert part.status_code == 206 and len(part.content) == 10


def test_read_url_is_signed_expiring_and_not_an_upload_link(
        client, make_crew, crew_headers, new_visit, store):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = crew_headers(ravi)
    upload_id = upload_file(client, headers, str(job.id))
    ok = store.presign_download(upload_id, "k", "image/jpeg", utcnow() + timedelta(hours=1))
    assert client.get(ok).status_code == 200
    assert client.get(ok[:-4] + "0000").status_code == 403
    expired = store.presign_download(upload_id, "k", "image/jpeg",
                                    utcnow() - timedelta(seconds=5))
    assert client.get(expired).status_code == 403
    up = store.presign_upload(upload_id, "k", "image/jpeg", utcnow() + timedelta(hours=1))
    assert client.get(up.url).status_code == 403


def test_an_unconfirmed_upload_is_not_shown_to_the_customer(
        client, make_crew, crew_headers, owner_headers, new_visit, store):
    ravi = make_crew("9000000010", "Ravi")
    visit, (job,) = new_visit(assigned=ravi)
    headers = crew_headers(ravi)
    r = client.post("/v1/media/uploads", headers=headers, json={
        "job_id": str(job.id), "kind": "photo", "stage": "Before",
        "content_type": "image/jpeg", "size_bytes": 100})
    assert r.status_code == 201
    body = client.get(f"/v1/customer/visits/{visit.id}", headers=owner_headers).json()
    assert body["jobs"][0]["proof"] == []
    link = store.presign_download(r.json()["id"], "k", "image/jpeg",
                                  utcnow() + timedelta(hours=1))
    assert client.get(link).status_code == 404


def test_upload_for_a_closed_job_is_refused(client, make_crew, crew_headers, new_visit):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = crew_headers(ravi)
    finish_job(client, headers, str(job.id))
    r = client.post("/v1/media/uploads", headers=headers, json={
        "job_id": str(job.id), "kind": "photo", "stage": "After",
        "content_type": "image/jpeg", "size_bytes": 100})
    assert r.status_code == 409
    assert r.json()["code"] == "job_closed"


def test_history_and_today_carry_finish_time_rating_and_counts(
        client, make_crew, crew_headers, owner_headers, new_visit, db, world):
    ravi = make_crew("9000000010", "Ravi")
    visit, (job,) = new_visit(assigned=ravi)
    finish_job(client, crew_headers(ravi), str(job.id))
    db.add(VisitRating(customer_id=world.vehicles[0].customer_id, visit_id=str(visit.id),
                       rating=4, tags=["Late"]))
    db.commit()

    items = client.get("/v1/customer/history", headers=owner_headers).json()
    assert items[0]["rating"] == 4
    assert items[0]["finished_at"] is not None
    assert items[0]["photo_count"] == 2
    month = visit.date.strftime("%Y-%m")
    assert len(client.get(f"/v1/customer/history?month={month}",
                          headers=owner_headers).json()) == 1
    assert client.get("/v1/customer/history?month=1999-01",
                      headers=owner_headers).json() == []
    meta = client.get("/v1/customer/history/meta", headers=owner_headers).json()
    assert meta["latest_month"] == month and meta["earliest_month"] == month
    assert meta["member_since"] == "2026-11-07"

    detail = client.get(f"/v1/customer/visits/{visit.id}", headers=owner_headers).json()
    assert detail["rating"] == {"rating": 4, "tags": ["Late"]}
    assert client.get("/v1/customer/today", headers=owner_headers).status_code == 200


def test_another_customers_visit_proof_is_not_readable(
        client, make_crew, crew_headers, new_visit, db):
    ravi = make_crew("9000000010", "Ravi")
    visit, _ = new_visit(assigned=ravi)
    db.add(Login(role="customer", login_id="other@priveo.test", display_name="Other",
                 password_hash=hash_password(PASSWORD)))
    db.commit()
    headers = _login(client, "other@priveo.test")
    # The login has no customer record, so it reads as not set up.
    assert client.get(f"/v1/customer/visits/{visit.id}", headers=headers).status_code == 404


def test_vehicle_photo_shows_on_the_crew_card_and_customer_vehicle(
        client, make_crew, crew_headers, owner_headers, new_visit, db, world, store):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = crew_headers(ravi)
    vehicle = world.vehicles[0]
    owner = db.query(Login).filter_by(login_id="owner@priveo.test").one()
    key = f"vehicle/{vehicle.id}/photo1"
    db.add(MediaUpload(owner_login_id=owner.id, purpose="proof", kind="photo",
                       content_type="image/jpeg", declared_size_bytes=4, object_key=key,
                       status="confirmed", size_bytes=4, confirmed_at=utcnow()))
    db.commit()
    store.put(key, b"JPEG")

    card = client.get(f"/v1/crew/jobs/{job.id}", headers=headers).json()["job"]
    url = card["vehicle"]["photo_url"]
    assert url and client.get(url).content == b"JPEG"
    mine = client.get(f"/v1/customer/vehicles/{vehicle.id}", headers=owner_headers).json()
    assert mine["photo_url"]
    other = client.get(f"/v1/customer/vehicles/{world.vehicles[1].id}",
                       headers=owner_headers).json()
    assert other["photo_url"] is None


def test_profile_photo_has_a_read_url(client, make_crew, crew_headers):
    ravi = make_crew("9000000010", "Ravi")
    headers = crew_headers(ravi)
    assert client.get("/v1/crew/profile/photo", headers=headers).json()["url"] is None
    r = client.post("/v1/media/uploads", headers=headers, json={
        "purpose": "profile", "kind": "photo", "content_type": "image/jpeg",
        "size_bytes": 10})
    ticket = r.json()
    client.put(ticket["upload_url"], content=b"z" * 10, headers=ticket["headers"])
    client.post(f"/v1/media/uploads/{ticket['id']}/confirm", headers=headers)
    saved = client.put("/v1/crew/profile/photo", headers=headers,
                       json={"upload_id": ticket["id"]}).json()
    assert client.get(saved["url"]).content == b"z" * 10
