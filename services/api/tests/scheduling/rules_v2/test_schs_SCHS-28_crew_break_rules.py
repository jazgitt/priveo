"""SCHS-28: the crew screen reads the break rules that reach one cleaner (SCHR-BRK-05, -06)."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
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


def _sched_id(engine, crew_id):
    with Session(engine) as s:
        m = s.get(CrewMember, uuid.UUID(crew_id))
        return s.scalar(select(SchedulingCrew.id).where(SchedulingCrew.login_id == m.login_id))


def test_schr_brk_06_returns_own_and_site_wide_rules_only(api, admin, world, engine):
    a = _hire(api, admin, world, "Asha", "9800000021")
    b = _hire(api, admin, world, "Bala", "9800000022")
    sa, sb = _sched_id(engine, a), _sched_id(engine, b)
    for crew_id, start in ((None, 1), (sa, 2), (sb, 3)):
        r = api.post("/v1/admin/scheduling/break-rules", headers=admin, json={
            "society_id": str(world.society.id), "crew_id": str(crew_id) if crew_id else None,
            "start_date": f"2026-12-0{start}", "end_date": f"2026-12-0{start}", "enabled": False})
        assert r.status_code == 201, r.text
    r = api.get(f"{CREW}/{a}/break-rules", headers=admin)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scheduling_crew_id"] == str(sa)
    assert sorted(x["start_date"] for x in body["rules"]) == ["2026-12-01", "2026-12-02"]


def test_schr_brk_05_no_break_is_a_rule_that_is_switched_off(api, admin, world, engine):
    a = _hire(api, admin, world, "Asha", "9800000023")
    r = api.post("/v1/admin/scheduling/break-rules", headers=admin, json={
        "society_id": str(world.society.id), "crew_id": str(_sched_id(engine, a)),
        "start_date": "2026-12-01", "end_date": "2026-12-03", "enabled": False})
    assert r.status_code == 201 and r.json()["enabled"] is False
    rules = api.get(f"{CREW}/{a}/break-rules", headers=admin).json()["rules"]
    assert rules[0]["enabled"] is False and rules[0]["end_date"] == "2026-12-03"


def test_only_an_admin_may_use_it_and_unknown_crew_is_404(api, admin):
    token = login(api, "customer")["access_token"]
    assert api.get(f"{CREW}/{uuid.uuid4()}/break-rules", headers=auth(token)).status_code == 403
    assert api.get(f"{CREW}/{uuid.uuid4()}/break-rules", headers=admin).status_code == 404
