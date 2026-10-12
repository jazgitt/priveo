"""The customer's profile, email change, password, vehicle edits and uploads
(ACC-01, ACC-06, ACC-08, VEH-01, VEH-03, VEH-04, ONB-22, ISS-02, ISS-04)."""
import pytest

from app.media.store import LocalObjectStore, get_object_store
from app.platform.email import EmailSendError, FakeEmailSender, get_email_sender
from tests.test_api import auth, login


@pytest.fixture
def store(tmp_path):
    return LocalObjectStore(root=tmp_path / "media", secret="test-signing-secret")


@pytest.fixture
def me(client, store):
    client.app.dependency_overrides[get_object_store] = lambda: store
    return auth(login(client, "customer")["access_token"])


def vehicle_id(client, me):
    return client.get("/v1/customer/vehicles", headers=me).json()[0]["id"]


def upload(client, me, purpose, content_type="image/jpeg", data=b"x" * 500, **extra):
    r = client.post("/v1/customer/uploads", headers=me, json={
        "purpose": purpose, "content_type": content_type, "size_bytes": len(data), **extra})
    assert r.status_code == 201, r.text
    t = r.json()
    assert client.put(t["upload_url"], content=data).status_code == 204
    done = client.post(f"/v1/customer/uploads/{t['id']}/confirm", headers=me)
    assert done.status_code == 200, done.text
    return done.json()


def test_profile_read_and_edit(client, me):
    p = client.get("/v1/customer/profile", headers=me).json()
    assert "email" in p, p
    assert p["email"] == "customer@priveo.test" and p["pending_email"] is None
    assert len(p["initials"]) == 2
    r = client.patch("/v1/customer/profile", headers=me, json={
        "first_name": "Asha", "last_name": "Rao", "mobile": "9876543210"})
    assert r.status_code == 200 and r.json()["mobile"] == "9876543210"
    bad = client.patch("/v1/customer/profile", headers=me, json={
        "first_name": "A1", "last_name": "", "mobile": "12"})
    assert bad.status_code == 422
    assert set(bad.json()["fields"]) == {"first_name", "last_name", "mobile"}


def test_failed_email_change_preserves_the_previous_pending_code(client, me, monkeypatch):
    first = client.post("/v1/customer/profile/email", headers=me,
                        json={"email": "first@example.com"})
    assert first.status_code == 200
    code = get_email_sender().sent[-1].code

    def fail_send(self, to, code, purpose):
        raise EmailSendError("Provider unavailable")

    monkeypatch.setattr(FakeEmailSender, "send_code", fail_send)
    failed = client.post("/v1/customer/profile/email", headers=me,
                         json={"email": "second@example.com"})
    assert failed.status_code == 502 and failed.json()["code"] == "email_failed"
    profile = client.get("/v1/customer/profile", headers=me).json()
    assert profile["pending_email"] == "first@example.com"
    verified = client.post("/v1/customer/profile/email/verify", headers=me,
                           json={"code": code})
    assert verified.status_code == 200 and verified.json()["email"] == "first@example.com"


def test_prod_email_change_requires_a_delivery_provider(client, me, monkeypatch):
    from app.platform.config import get_settings

    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("RESEND_API_KEY", "")
    get_settings.cache_clear()
    result = client.post("/v1/customer/profile/email", headers=me,
                         json={"email": "new@example.com"})
    assert result.status_code == 503 and result.json()["code"] == "not_configured"
    assert client.get("/v1/customer/profile", headers=me).json()["pending_email"] is None


def test_email_change_needs_the_code_and_keeps_the_old_email_until_then(client, me):
    sender = get_email_sender()
    before = len(sender.sent)
    r = client.post("/v1/customer/profile/email", headers=me,
                    json={"email": "New.Mail@Example.com"})
    assert r.status_code == 200 and r.json()["email"] == "new.mail@example.com"
    assert sender.sent[before].to == "new.mail@example.com"
    code = sender.sent[before].code
    p = client.get("/v1/customer/profile", headers=me).json()
    assert p["email"] == "customer@priveo.test" and p["pending_email"] == "new.mail@example.com"

    wrong_code = "000000" if code != "000000" else "111111"
    wrong = client.post("/v1/customer/profile/email/verify", headers=me,
                        json={"code": wrong_code})
    assert wrong.status_code == 400
    ok = client.post("/v1/customer/profile/email/verify", headers=me, json={"code": code})
    assert ok.status_code == 200 and ok.json()["email"] == "new.mail@example.com"
    r = client.post("/v1/auth/login", json={
        "login_id": "new.mail@example.com", "password": "pw-customer1"})
    assert r.status_code == 200


def test_email_change_rejects_a_bad_or_used_email(client, me):
    assert client.post("/v1/customer/profile/email", headers=me,
                       json={"email": "not-an-email"}).status_code == 422
    r = client.post("/v1/customer/profile/email", headers=me,
                    json={"email": "customer@priveo.test"})
    assert r.status_code == 409 and r.json()["code"] == "email_in_use"


def test_change_password(client, me):
    wrong = client.post("/v1/customer/password", headers=me, json={
        "current_password": "nope", "new_password": "fresh-pass-9"})
    assert wrong.status_code == 422
    weak = client.post("/v1/customer/password", headers=me, json={
        "current_password": "pw-customer1", "new_password": "short"})
    assert weak.status_code == 422
    ok = client.post("/v1/customer/password", headers=me, json={
        "current_password": "pw-customer1", "new_password": "fresh-pass-9"})
    assert ok.status_code == 204
    assert client.get("/v1/customer/profile", headers=me).status_code == 200
    assert client.post("/v1/auth/login", json={
        "login_id": "customer@priveo.test", "password": "fresh-pass-9"}).status_code == 200


def test_vehicle_photo_upload_becomes_the_vehicle_photo(client, me):
    vid = vehicle_id(client, me)
    before = client.get(f"/v1/customer/vehicles/{vid}", headers=me).json()
    assert before["rc_status"] == "Not uploaded" and before["photo_url"] is None
    state = upload(client, me, "vehicle", "image/heic", vehicle_id=vid)
    assert state["status"] == "confirmed" and state["url"]
    after = client.get(f"/v1/customer/vehicles/{vid}", headers=me).json()
    assert after["photo_url"]
    home = client.get("/v1/customer/home", headers=me).json()
    assert home["vehicles"][0]["photo_url"]
    assert client.get(after["photo_url"]).content == b"x" * 500
    # A newer photo replaces it.
    second = upload(client, me, "vehicle", vehicle_id=vid, data=b"y" * 10)
    assert client.get(second["url"]).content == b"y" * 10


def test_upload_rules(client, me):
    vid = vehicle_id(client, me)

    def req(**changes):
        body = {"purpose": "vehicle", "vehicle_id": vid, "content_type": "image/jpeg",
                "size_bytes": 100, **changes}
        return client.post("/v1/customer/uploads", headers=me, json=body)

    assert req(content_type="application/pdf").status_code == 422
    assert req(size_bytes=10 * 1024 * 1024 + 1).status_code == 422
    assert req(purpose="proof").status_code == 422
    # Staged photos are uploaded before a new vehicle has an ID.
    assert req(vehicle_id=None).status_code == 201
    assert req(vehicle_id="00000000-0000-0000-0000-000000000000").status_code == 404
    assert req(purpose="rc", content_type="application/pdf").status_code == 201
    assert req(purpose="rc", size_bytes=5 * 1024 * 1024 + 1).status_code == 422
    rc = upload(client, me, "rc", "application/pdf", vehicle_id=vid)
    assert rc["status"] == "confirmed"
    detail = client.get(f"/v1/customer/vehicles/{vid}", headers=me).json()
    assert detail["rc_status"] == "Uploaded"
    # The crew route stays closed to a customer.
    assert client.post("/v1/media/uploads", headers=me, json={
        "kind": "photo", "content_type": "image/jpeg", "size_bytes": 1}).status_code == 403


def test_parking_edit_checks_the_societys_basements(client, me):
    vid = vehicle_id(client, me)
    r = client.patch(f"/v1/customer/vehicles/{vid}", headers=me,
                     json={"parking_basement": "b3", "parking_number": "27"})
    assert r.status_code == 200
    assert (r.json()["parking_basement"], r.json()["parking_number"]) == ("B3", "27")
    bad = client.patch(f"/v1/customer/vehicles/{vid}", headers=me,
                       json={"parking_basement": "Z9", "parking_number": "x"})
    assert bad.status_code == 422
    assert set(bad.json()["fields"]) == {"parking_basement", "parking_number"}
    detail = client.get(f"/v1/customer/vehicles/{vid}", headers=me).json()
    assert detail["parking"] == "B3-27"


def test_complaint_photos_and_visit_must_be_the_customers_own(client, me):
    base = {"category": "Cleaning quality", "description": "Streaks"}
    bad = client.post("/v1/customer/complaints", headers=me,
                      json={**base, "photo_keys": ["not-an-id"]})
    assert bad.status_code == 422
    t = client.post("/v1/customer/uploads", headers=me, json={
        "purpose": "complaint", "content_type": "image/png", "size_bytes": 3}).json()
    unconfirmed = client.post("/v1/customer/complaints", headers=me,
                              json={**base, "photo_keys": [t["id"]]})
    assert unconfirmed.status_code == 422
    client.put(t["upload_url"], content=b"abc")
    client.post(f"/v1/customer/uploads/{t['id']}/confirm", headers=me)
    ok = client.post("/v1/customer/complaints", headers=me,
                     json={**base, "photo_keys": [t["id"]]})
    assert ok.status_code == 201, ok.text
    assert ok.json()["photo_keys"] == [t["id"]] and len(ok.json()["photo_urls"]) == 1
    bad_visit = client.post("/v1/customer/complaints", headers=me, json={
        **base, "visit_id": "00000000-0000-0000-0000-000000000001"})
    assert bad_visit.status_code == 422
