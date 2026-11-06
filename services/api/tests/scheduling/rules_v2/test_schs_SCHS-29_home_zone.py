"""SCHS-29: the admin sets one home zone for each cleaner."""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory.models import Society, Zone
from app.scheduling import home_zone
from app.scheduling.models import SchedulingCrew
from tests.test_api import auth, login

CREW = "/v1/admin/crew"
DAYS = [{"day": d, "working": True, "start": "06:00", "end": "11:00"} for d in
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]]


def _hire(api, admin, world, name, mobile):
    r = api.post(CREW, headers=admin, json={
        "name": name, "mobile": mobile, "role": "Member",
        "society_id": str(world.society.id), "working_hours": DAYS})
    assert r.status_code == 201, r.text
    return r.json()["crew"]["id"] if "crew" in r.json() else r.json()["id"]


def _row(engine, crew_id):
    from app.crew.models import CrewMember
    with Session(engine) as s:
        m = s.get(CrewMember, uuid.UUID(crew_id))
        return s.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == m.login_id))


@pytest.fixture
def two(world, api, admin, engine):
    a = _hire(api, admin, world, "Asha", "9800000011")
    b = _hire(api, admin, world, "Bala", "9800000012")
    t = _hire(api, admin, world, "Tara", "9800000013")
    with Session(engine) as s:
        row_a, row_t = _row(engine, a), _row(engine, t)
        trainee = s.get(SchedulingCrew, row_t.id)
        trainee.role, trainee.paired_member_id = "Trainee", row_a.id
        z1 = Zone(society_id=world.society.id, name="Zone 1")
        z2 = Zone(society_id=world.society.id, name="Zone 2")
        s.add_all([z1, z2])
        s.commit()
        return a, b, t, z1.id, z2.id


def test_schr_zone_07_admin_sets_and_clears_a_home_zone(api, admin, two):
    a, _b, _t, z1, _z2 = two
    r = api.put(f"{CREW}/{a}/home-zone", headers=admin, json={"home_zone_id": str(z1)})
    assert r.status_code == 200, r.text
    assert r.json()["home_zone_id"] == str(z1)
    assert {z["name"] for z in r.json()["zones"]} >= {"Zone 1", "Zone 2"}
    assert api.get(f"{CREW}/{a}/home-zone", headers=admin).json()["home_zone_id"] == str(z1)
    r = api.put(f"{CREW}/{a}/home-zone", headers=admin, json={"home_zone_id": None})
    assert r.json()["home_zone_id"] is None


def test_schr_zone_07_several_cleaners_may_share_a_zone(api, admin, two, engine):
    a, b, _t, z1, _z2 = two
    for c in (a, b):
        r = api.put(f"{CREW}/{c}/home-zone", headers=admin, json={"home_zone_id": str(z1)})
        assert r.status_code == 200, r.text
    assert {_row(engine, c).home_zone_id for c in (a, b)} == {z1}


def test_schr_zone_01_only_a_zone_of_the_cleaners_society_can_be_chosen(api, admin, two, engine):
    a = two[0]
    with Session(engine) as s:
        other = Society(name="Elsewhere", city="Pune")
        s.add(other)
        s.flush()
        foreign = Zone(society_id=other.id, name="Far")
        s.add(foreign)
        s.commit()
        foreign_id = foreign.id
    r = api.put(f"{CREW}/{a}/home-zone", headers=admin, json={"home_zone_id": str(foreign_id)})
    assert r.status_code == 422 and "home_zone_id" in r.json()["fields"]
    r = api.put(f"{CREW}/{a}/home-zone", headers=admin, json={"home_zone_id": str(uuid.uuid4())})
    assert r.status_code == 422


def test_schr_zone_09_a_trainee_shows_the_members_zone_and_cannot_set_one(api, admin, two):
    a, _b, t, z1, z2 = two
    api.put(f"{CREW}/{a}/home-zone", headers=admin, json={"home_zone_id": str(z1)})
    r = api.get(f"{CREW}/{t}/home-zone", headers=admin)
    assert r.json()["home_zone_id"] == str(z1)
    assert r.json()["follows_member"] == "Asha" and r.json()["editable"] is False
    assert api.put(f"{CREW}/{t}/home-zone", headers=admin,
                   json={"home_zone_id": str(z2)}).status_code == 422


def test_schr_zone_09_effective_zone_follows_the_member(two, engine):
    a, _b, t, z1, _z2 = two
    with Session(engine) as s:
        s.get(SchedulingCrew, _row(engine, a).id).home_zone_id = z1
        s.commit()
        assert home_zone.effective_zone_id(s, s.get(SchedulingCrew, _row(engine, t).id)) == z1


def test_only_an_admin_may_use_it(api, two):
    token = login(api, "customer")["access_token"]
    assert api.get(f"{CREW}/{two[0]}/home-zone", headers=auth(token)).status_code == 403
    assert api.get(f"{CREW}/{two[0]}/home-zone").status_code == 401
