"""P3-3 (ADM-SVS-12): the working-slot exception endpoints. Validation, the
one-exception-per-weekday rule, and the audit trail."""
import uuid

from app.directory.models import DirectoryAudit

BASE = "/v1/admin/directory"
EXCEPTION = {
    "service": "Cleaning-External", "start_date": "2026-11-11", "end_date": "2026-11-17",
    "days": ["Wednesday"], "windows": [{"start": "05:00", "end": "11:00"}], "note": "Festival week",
}


def _society(client, admin):
    r = client.post(f"{BASE}/societies", headers=admin, json={"name": "Lake View"})
    assert r.status_code == 201, r.text
    return r.json()


def test_an_exception_is_created_listed_changed_and_deleted(client, admin):
    made = _society(client, admin)
    url = f"{BASE}/societies/{made['id']}/slot-exceptions"
    r = client.post(url, headers=admin, json=EXCEPTION)
    assert r.status_code == 201, r.text
    ex = r.json()
    assert ex["days"] == ["Wednesday"] and ex["start_date"] == "2026-11-11"
    assert ex["windows"] == [{"start": "05:00", "end": "11:00"}] and ex["note"] == "Festival week"

    listed = client.get(f"{url}?service=Cleaning-External", headers=admin).json()
    assert [row["id"] for row in listed] == [ex["id"]]
    assert client.get(f"{url}?service=Deep Spa", headers=admin).json() == []

    up = client.patch(f"{BASE}/slot-exceptions/{ex['id']}", headers=admin,
                      json={"windows": [], "days": ["Wednesday", "Sunday"]})
    assert up.status_code == 200, up.text
    assert up.json()["windows"] == [] and up.json()["days"] == ["Wednesday", "Sunday"]

    assert client.delete(f"{BASE}/slot-exceptions/{ex['id']}", headers=admin).status_code == 204
    assert client.delete(f"{BASE}/slot-exceptions/{ex['id']}", headers=admin).status_code == 404


def test_an_exception_for_the_same_weekday_and_dates_is_refused(client, admin):
    url = f"{BASE}/societies/{_society(client, admin)['id']}/slot-exceptions"
    assert client.post(url, headers=admin, json=EXCEPTION).status_code == 201
    clash = client.post(url, headers=admin, json=EXCEPTION | {"start_date": "2026-11-15"})
    assert clash.status_code == 409 and clash.json()["code"] == "overlap"
    # Another weekday on the same dates, or another service, is allowed.
    assert client.post(url, headers=admin,
                       json=EXCEPTION | {"days": ["Monday"]}).status_code == 201
    assert client.post(url, headers=admin,
                       json=EXCEPTION | {"service": "Deep Spa"}).status_code == 201


def test_exception_rules_are_checked(client, admin):
    url = f"{BASE}/societies/{_society(client, admin)['id']}/slot-exceptions"
    backwards_dates = client.post(url, headers=admin,
                                  json=EXCEPTION | {"start_date": "2026-11-20", "end_date": "2026-11-18"})
    assert backwards_dates.status_code == 422 and "end_date" in backwards_dates.json()["fields"]
    backwards_window = client.post(url, headers=admin, json=EXCEPTION | {
        "windows": [{"start": "11:00", "end": "05:00"}]})
    assert backwards_window.status_code == 422 and "windows" in backwards_window.json()["fields"]
    overlapping = client.post(url, headers=admin, json=EXCEPTION | {
        "windows": [{"start": "05:00", "end": "09:00"}, {"start": "08:00", "end": "10:00"}]})
    assert overlapping.status_code == 409 and overlapping.json()["code"] == "overlap"
    bad_day = client.post(url, headers=admin, json=EXCEPTION | {"days": ["Funday"]})
    assert bad_day.status_code == 422
    bad_service = client.post(url, headers=admin, json=EXCEPTION | {"service": "Window"})
    assert bad_service.status_code == 422


def test_no_window_is_allowed_and_means_closed(client, admin):
    url = f"{BASE}/societies/{_society(client, admin)['id']}/slot-exceptions"
    closed = client.post(url, headers=admin, json=EXCEPTION | {"windows": []})
    assert closed.status_code == 201, closed.text
    assert closed.json()["windows"] == []


def test_an_unknown_society_or_exception_is_not_found(client, admin):
    assert client.get(f"{BASE}/societies/{uuid.uuid4()}/slot-exceptions",
                      headers=admin).status_code == 404
    assert client.patch(f"{BASE}/slot-exceptions/{uuid.uuid4()}", headers=admin,
                        json={"note": "x"}).status_code == 404


def test_exception_changes_are_audited_with_json_safe_detail(client, admin, engine):
    from sqlalchemy.orm import Session

    url = f"{BASE}/societies/{_society(client, admin)['id']}/slot-exceptions"
    ex = client.post(url, headers=admin, json=EXCEPTION).json()
    client.patch(f"{BASE}/slot-exceptions/{ex['id']}", headers=admin, json={"note": "Diwali"})
    client.delete(f"{BASE}/slot-exceptions/{ex['id']}", headers=admin)
    with Session(engine) as db:
        rows = db.query(DirectoryAudit).filter(DirectoryAudit.entity == "slot_exception",
                                               DirectoryAudit.entity_id == ex["id"]).all()
        assert sorted(r.action for r in rows) == ["create", "delete", "update"]
        created = next(r for r in rows if r.action == "create")
        assert created.detail["start_date"] == "2026-11-11" and created.detail["days"] == ["Wednesday"]
