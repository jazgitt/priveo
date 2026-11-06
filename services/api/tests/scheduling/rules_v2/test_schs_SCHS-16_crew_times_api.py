"""SCHS-16: the admin reads and sets a cleaner's reporting and first-job times."""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
from app.directory import lookup, rule_seed
from app.directory.models import DirectoryAudit
from app.scheduling.models import SchedulingCrew
from tests.test_api import auth, login

CREW = "/v1/admin/crew"


@pytest.fixture
def member(api, admin, world):
    rule_seed.seed_rule_keys(world.db)
    world.db.commit()
    lookup.invalidate()
    days = [{"day": d, "working": True, "start": "06:00", "end": "11:00"} for d in
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]]
    r = api.post(CREW, headers=admin, json={
        "name": "Ravi Kumar", "mobile": "9800000001", "role": "Member",
        "society_id": str(world.society.id), "working_hours": days})
    assert r.status_code == 201, r.text
    return r.json()["crew"]["id"] if "crew" in r.json() else r.json()["id"]


def _row(engine, crew_id):
    with Session(engine) as s:
        m = s.get(CrewMember, uuid.UUID(crew_id))
        return s.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == m.login_id))


def test_get_shows_site_values_and_no_override(api, admin, member):
    r = api.get(f"{CREW}/{member}/times", headers=admin)
    assert r.status_code == 200, r.text
    assert r.json() == {"reporting_minute": None, "first_job_minute": None,
                        "site_reporting_minute": 300, "site_first_job_minute": 330}


def test_put_saves_an_override_and_an_audit_row(api, admin, member, engine):
    r = api.put(f"{CREW}/{member}/times", headers=admin,
                json={"reporting_minute": 310, "first_job_minute": 345})
    assert r.status_code == 200, r.text
    assert r.json()["reporting_minute"] == 310 and r.json()["first_job_minute"] == 345
    assert api.get(f"{CREW}/{member}/times", headers=admin).json()["first_job_minute"] == 345
    row = _row(engine, member)
    assert (row.reporting_minute, row.first_job_minute) == (310, 345)
    with Session(engine) as s:
        rows = s.scalars(select(DirectoryAudit).where(
            DirectoryAudit.entity == "crew", DirectoryAudit.entity_id == member,
            DirectoryAudit.action == "update")).all()
    assert any(a.detail == {"reporting_minute": [None, 310], "first_job_minute": [None, 345]}
               for a in rows)


def test_clear_returns_to_the_site_value(api, admin, member, engine):
    api.put(f"{CREW}/{member}/times", headers=admin,
            json={"reporting_minute": 310, "first_job_minute": 345})
    r = api.put(f"{CREW}/{member}/times", headers=admin,
                json={"reporting_minute": None, "first_job_minute": None})
    assert r.status_code == 200
    assert r.json()["reporting_minute"] is None and r.json()["site_first_job_minute"] == 330
    assert _row(engine, member).first_job_minute is None


def test_first_job_before_reporting_is_refused(api, admin, member, engine):
    r = api.put(f"{CREW}/{member}/times", headers=admin,
                json={"reporting_minute": 400, "first_job_minute": 390})
    assert r.status_code == 422 and "first_job_minute" in r.json()["fields"]
    assert _row(engine, member).reporting_minute is None


def test_validation_uses_the_site_value_for_a_cleared_side(api, admin, member):
    # Site first job is 05:30 (330); a reporting override of 06:00 would pass it.
    r = api.put(f"{CREW}/{member}/times", headers=admin,
                json={"reporting_minute": 360, "first_job_minute": None})
    assert r.status_code == 422


def test_only_an_admin_may_use_it(api, member):
    token = login(api, "customer")["access_token"]
    assert api.get(f"{CREW}/{member}/times", headers=auth(token)).status_code == 403
    assert api.put(f"{CREW}/{member}/times", headers=auth(token),
                   json={"reporting_minute": 300, "first_job_minute": 330}).status_code == 403
    assert api.get(f"{CREW}/{member}/times").status_code == 401


def test_unknown_crew_is_404(api, admin, member):
    assert api.get(f"{CREW}/{uuid.uuid4()}/times", headers=admin).status_code == 404
