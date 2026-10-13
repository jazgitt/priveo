"""Crew accounts: onboarding, the one-time password, reset, unlock and the
crew member's own profile (ADM-CRW-17, ADM-CRW-18, CRW-ACC-04 to CRW-ACC-11,
CRW-PRF-01)."""
import re

from sqlalchemy import select

from app.crew.service import generate_password
from app.identity.models import AuthSession, Login
from tests.test_api import auth, login

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOURS = [{"day": d, "working": d != "Sunday", "start": "07:00" if d != "Sunday" else "",
          "end": "15:00" if d != "Sunday" else ""} for d in DAYS]


def body(society, **over):
    data = {"name": "Raj Singh", "mobile": "9000000555", "society_id": str(society.id),
            "role": "Member", "working_hours": HOURS}
    return data | over


def create(client, society, **over):
    token = login(client, "admin")["access_token"]
    return client.post("/v1/admin/crew", json=body(society, **over), headers=auth(token))


def sign_in(client, mobile, password):
    return client.post("/v1/auth/login", json={"login_id": mobile, "password": password})


def test_password_format():
    assert re.fullmatch(r"Raj\d{4}\$", generate_password("raj singh"))
    assert re.fullmatch(r"Axx\d{4}\$", generate_password("A"))


def test_crew_registers_own_session_metadata(client, db, society):
    created = create(client, society).json()
    crew_token = sign_in(client, "9000000555", created["password"]).json()
    headers = auth(crew_token["access_token"])
    r = client.put("/v1/crew/session-device", headers=headers,
                   json={"device_name": "Crew phone", "platform": "android", "app_version": "1.2.3"})
    assert r.status_code == 204, r.text
    sessions = client.get(f"/v1/admin/crew/{created['crew']['id']}/sessions",
                          headers=auth(login(client, "admin")["access_token"])).json()
    assert any(s["device_name"] == "Crew phone" and s["platform"] == "android"
               and s["app_version"] == "1.2.3" for s in sessions)
    assert client.put("/v1/crew/session-device", headers=auth(login(client, "customer")["access_token"]),
                       json={"device_name": "Other", "platform": "android", "app_version": "1"}).status_code == 403


def test_admin_creates_crew_and_the_password_works_once_shown(client, society):
    r = create(client, society)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["login_id"] == "9000000555"
    assert re.fullmatch(r"Raj\d{4}\$", data["password"])
    assert data["crew"]["society"] == "Green Meadows" and data["crew"]["role"] == "Member"

    signed_in = sign_in(client, "9000000555", data["password"])
    assert signed_in.status_code == 200 and signed_in.json()["role"] == "crew"
    # The password is not in the list or anywhere else after creation.
    token = login(client, "admin")["access_token"]
    listed = client.get("/v1/admin/crew", headers=auth(token))
    assert [c["name"] for c in listed.json()] == ["Raj Singh"]
    assert "password" not in listed.text


def test_only_the_admin_manages_crew(client, society):
    for role in ("customer", "crew"):
        token = login(client, role)["access_token"]
        assert client.post("/v1/admin/crew", json=body(society),
                           headers=auth(token)).status_code == 403
        assert client.get("/v1/admin/crew", headers=auth(token)).status_code == 403
    assert client.get("/v1/admin/crew").status_code == 401


def test_checks_on_the_new_crew_member(client, society):
    assert create(client, society, mobile="12345").status_code == 422
    assert create(client, society, role="Boss").status_code == 422
    assert create(client, society, name="  ").status_code == 422
    assert create(client, society, working_hours=HOURS[:5]).status_code == 422
    bad = [dict(h) for h in HOURS]
    bad[0].update(start="16:00", end="08:00")
    assert create(client, society, working_hours=bad).status_code == 422
    unknown = create(client, society, society_id="00000000-0000-0000-0000-000000000000")
    assert unknown.status_code == 422


def test_a_mobile_number_belongs_to_one_login(client, society):
    assert create(client, society).status_code == 201
    again = create(client, society, name="Other Person")
    assert again.status_code == 409 and again.json()["code"] == "mobile_in_use"
    # The seeded demo crew login already uses this number.
    assert create(client, society, mobile="9000000002").status_code == 409


def test_reset_gives_a_new_password_and_signs_the_phone_out(client, society, db):
    created = create(client, society).json()
    old = created["password"]
    session = sign_in(client, "9000000555", old).json()
    admin = auth(login(client, "admin")["access_token"])

    r = client.post(f"/v1/admin/crew/{created['crew']['id']}/password", headers=admin)
    assert r.status_code == 200
    new = r.json()["password"]
    assert re.fullmatch(r"Raj\d{4}\$", new)

    assert sign_in(client, "9000000555", old).status_code in (401, 429)
    assert sign_in(client, "9000000555", new).status_code == 200
    # The phone that was signed in is signed out at once (CRW-ACC-11).
    assert client.get("/v1/crew/profile",
                      headers=auth(session["access_token"])).status_code == 401
    assert "password_reset" in db.scalars(select(AuthSession.ended_reason)).all()


def test_a_locked_login_is_unlocked_by_reset_and_by_unlock(client, society):
    created = create(client, society).json()
    crew_id = created["crew"]["id"]
    admin = auth(login(client, "admin")["access_token"])

    def lock():
        for _ in range(5):
            sign_in(client, "9000000555", "wrong-Pass1")
        r = sign_in(client, "9000000555", created["password"])
        assert r.status_code == 403 and r.json()["code"] == "account_locked"

    lock()
    listed = client.get("/v1/admin/crew", headers=admin).json()
    assert listed[0]["locked"] is True
    unlocked = client.post(f"/v1/admin/crew/{crew_id}/unlock", headers=admin)
    assert unlocked.status_code == 200 and unlocked.json()["locked"] is False
    # Same password after an unlock.
    assert sign_in(client, "9000000555", created["password"]).status_code == 200

    lock()
    reset = client.post(f"/v1/admin/crew/{crew_id}/password", headers=admin).json()
    assert sign_in(client, "9000000555", reset["password"]).status_code == 200


def test_unknown_crew_id_is_not_found(client, society):
    admin = auth(login(client, "admin")["access_token"])
    missing = "00000000-0000-0000-0000-000000000009"
    assert client.post(f"/v1/admin/crew/{missing}/password",
                       headers=admin).status_code == 404
    assert client.post(f"/v1/admin/crew/{missing}/unlock", headers=admin).status_code == 404


def test_a_deactivated_crew_member_cannot_sign_in(client, society, db):
    created = create(client, society).json()
    row = db.scalar(select(Login).where(Login.login_id == "9000000555"))
    row.active = False
    db.commit()
    assert sign_in(client, "9000000555", created["password"]).status_code == 401


def test_crew_profile_is_the_members_own_and_has_no_customer_data(client, society):
    created = create(client, society).json()
    token = sign_in(client, "9000000555", created["password"]).json()["access_token"]
    r = client.get("/v1/crew/profile", headers=auth(token))
    assert r.status_code == 200
    profile = r.json()
    assert profile["name"] == "Raj Singh" and profile["mobile"] == "9000000555"
    assert profile["society"] == "Green Meadows" and profile["role"] == "Member"
    assert len(profile["working_hours"]) == 7
    assert set(profile) == {"name", "mobile", "society", "role", "working_hours"}


def test_profile_is_for_crew_only_and_needs_a_crew_record(client):
    assert client.get("/v1/crew/profile").status_code == 401
    customer = login(client, "customer")["access_token"]
    assert client.get("/v1/crew/profile", headers=auth(customer)).status_code == 403
    # The seeded demo crew login has no crew record yet.
    demo = login(client, "crew")["access_token"]
    r = client.get("/v1/crew/profile", headers=auth(demo))
    assert r.status_code == 404 and r.json()["code"] == "no_crew_record"
