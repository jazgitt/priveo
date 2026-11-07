"""SCHS-23: break rules store, lookup and API (SCHR-PAR-09, SCHR-BRK-06, SCHR-BRK-07,
SCHR-BRK-10). Lookup only: nothing plans around a break."""
from datetime import timedelta

from sqlalchemy import select

from app.directory import settings_registry
from app.directory.models import DirectoryAudit
from app.scheduling import breaks
from app.scheduling.models import BreakRule, Job, Schedule, Visit
from tests.scheduling.builders import Scenario
from tests.scheduling.conftest import SUNDAY

DAY = SUNDAY + timedelta(days=1)
URL = "/v1/admin/scheduling/break-rules"


def _default(key):
    return int(settings_registry.default_for(key))


def _site():
    return (_default("site.break_start_minute"), _default("site.break_end_minute"))


def _scenario(world, site_cfg):
    site_cfg({})  # seeds the global defaults the site falls back to
    sc = Scenario(world)
    sc.slots()
    return sc


def _got(db, cleaner, day=DAY):
    found = breaks.effective_break(db, cleaner, day)
    return None if found is None else (found.start_minute, found.end_minute, found.source)


def test_schr_par_09_site_default_comes_from_settings(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    assert _got(sc.db, ravi) == (*_site(), "site")
    site_cfg({"site.break_end_minute": 630, "site.break_start_minute": 600})
    assert _got(sc.db, ravi) == (600, 630, "site")


def test_schr_par_09_site_break_switched_off_gives_none(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    site_cfg({"site.break_enabled": False})
    assert _got(sc.db, ravi) is None


def test_schr_brk_06_crew_override_beats_site(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi, sam = sc.cleaner("Ravi", shift=(360, 780)), sc.cleaner("Sam", shift=(360, 780))
    breaks.save_rule(sc.db, None, sc.site.id, crew_id=ravi.id, start_minute=600, end_minute=630)
    assert _got(sc.db, ravi) == (600, 630, "crew")
    assert _got(sc.db, sam) == (*_site(), "site")


def test_schr_brk_06_date_beats_crew_and_site(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi, sam = sc.cleaner("Ravi", shift=(360, 780)), sc.cleaner("Sam", shift=(360, 780))
    breaks.save_rule(sc.db, None, sc.site.id, crew_id=ravi.id, start_minute=600, end_minute=630)
    sc.break_rule(DAY, DAY, minutes=(570, 585))  # the whole site, that date
    assert _got(sc.db, ravi) == (570, 585, "date")
    assert _got(sc.db, sam) == (570, 585, "date")
    assert _got(sc.db, ravi, DAY + timedelta(days=1)) == (600, 630, "crew")


def test_schr_brk_06_date_and_crew_is_most_specific(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi, sam = sc.cleaner("Ravi", shift=(360, 780)), sc.cleaner("Sam", shift=(360, 780))
    sc.break_rule(DAY, DAY, minutes=(570, 585))
    sc.break_rule(DAY, DAY + timedelta(days=2), cleaner=ravi, minutes=(580, 610))
    breaks.save_rule(sc.db, None, sc.site.id, crew_id=ravi.id, start_minute=600, end_minute=630)
    assert _got(sc.db, ravi) == (580, 610, "date_crew")
    assert _got(sc.db, sam) == (570, 585, "date")
    assert _got(sc.db, ravi, DAY + timedelta(days=3)) == (600, 630, "crew")


def test_schr_brk_06_a_rule_with_no_break_turns_it_off(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    sc.break_rule(DAY, DAY, cleaner=ravi, enabled=False)
    assert _got(sc.db, ravi) is None
    assert _got(sc.db, ravi, DAY + timedelta(days=1)) == (*_site(), "site")


def test_schr_brk_06_rule_without_minutes_uses_the_site_break(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    sc.break_rule(DAY, DAY, cleaner=ravi)
    assert _got(sc.db, ravi) == (*_site(), "date_crew")


def test_schr_brk_06_another_site_and_another_cleaner_are_not_affected(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi, sam = sc.cleaner("Ravi", shift=(360, 780)), sc.cleaner("Sam", shift=(360, 780))
    sc.break_rule(DAY, DAY, cleaner=ravi, minutes=(600, 630))
    other = sc.add_site("Other")
    sc.db.add(BreakRule(society_id=other.id, start_date=DAY, end_date=DAY,
                        start_minute=1, end_minute=2))
    sc.db.flush()
    assert _got(sc.db, sam) == (*_site(), "site")


def test_schr_brk_07_window_not_covering_the_break_has_none(world, site_cfg):
    sc = _scenario(world, site_cfg)
    late = sc.cleaner("Late", shift=(630, 900))   # starts after 10:00
    early = sc.cleaner("Early", shift=(300, 560))  # ends before 09:30
    ok = sc.cleaner("Ok", shift=(360, 780))
    assert _got(sc.db, late) is None
    assert _got(sc.db, early) is None
    assert _got(sc.db, ok) is not None


def test_schr_brk_07_sick_or_late_start_changes_cover(world, site_cfg):
    sc = _scenario(world, site_cfg)
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    sc.exception(ravi, DAY, "Late start", from_minute=630)
    assert _got(sc.db, ravi) is None
    sc.exception(ravi, DAY + timedelta(days=1), "Sick")
    assert _got(sc.db, ravi, DAY + timedelta(days=1)) is None


def test_schr_brk_07_a_crew_rule_does_not_give_a_break_outside_the_window(world, site_cfg):
    sc = _scenario(world, site_cfg)
    late = sc.cleaner("Late", shift=(630, 900))
    breaks.save_rule(sc.db, None, sc.site.id, crew_id=late.id, start_minute=600, end_minute=630)
    assert _got(sc.db, late) is None


def _api_body(world, **extra):
    return {"society_id": str(world.society.id), **extra}


def test_schr_par_09_api_is_admin_only(api, world):
    r = api.get(URL, params={"society_id": str(world.society.id)})
    assert r.status_code in (401, 403)
    from tests.test_api import auth, login
    crew = auth(login(api, "crew")["access_token"])
    assert api.get(URL, params={"society_id": str(world.society.id)}, headers=crew).status_code == 403
    assert api.post(URL, json=_api_body(world), headers=crew).status_code == 403


def test_schr_par_09_api_create_list_update_delete(api, admin, world, site_cfg):
    ravi = Scenario(world).cleaner("Ravi", shift=(360, 780))
    world.db.commit()
    body = _api_body(world, crew_id=str(ravi.id), start_date=DAY.isoformat(),
                     end_date=(DAY + timedelta(days=2)).isoformat(),
                     start_minute=600, end_minute=630)
    r = api.post(URL, json=body, headers=admin)
    assert r.status_code == 201, r.text
    rule = r.json()
    assert (rule["crew_id"], rule["start_minute"], rule["end_minute"], rule["enabled"]) == (
        str(ravi.id), 600, 630, True)

    listed = api.get(URL, params={"society_id": str(world.society.id)}, headers=admin).json()
    assert [x["id"] for x in listed] == [rule["id"]]

    r = api.patch(f"{URL}/{rule['id']}", json={"start_minute": 590, "end_minute": 620}, headers=admin)
    assert r.status_code == 200 and r.json()["start_minute"] == 590

    r = api.delete(f"{URL}/{rule['id']}", headers=admin)
    assert r.status_code == 204
    assert api.get(URL, params={"society_id": str(world.society.id)}, headers=admin).json() == []

    actions = [a.action for a in world.db.scalars(
        select(DirectoryAudit).where(DirectoryAudit.entity == "break_rule").order_by(DirectoryAudit.at))]
    assert sorted(actions) == ["create", "delete", "update"]


def test_schr_par_09_api_crew_rule_without_dates_applies_every_day(api, admin, world, site_cfg):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    world.db.commit()
    r = api.post(URL, json=_api_body(world, crew_id=str(ravi.id), start_minute=600, end_minute=630),
                 headers=admin)
    assert r.status_code == 201 and r.json()["start_date"] is None and r.json()["end_date"] is None
    for day in (DAY, DAY + timedelta(days=400)):
        assert _got(world.db, ravi, day) == (600, 630, "crew")


def test_schr_par_09_api_rejects_bad_input(api, admin, world, site_cfg):
    ravi = Scenario(world).cleaner("Ravi", shift=(360, 780))
    world.db.commit()
    bad = [
        {"start_minute": 630, "end_minute": 600},                       # end before start
        {"start_minute": 600},                                           # one minute only
        {"start_date": DAY.isoformat()},                                 # one date only
        {"start_date": DAY.isoformat(), "end_date": (DAY - timedelta(days=1)).isoformat()},
        {"start_minute": 600, "end_minute": 2000},                       # out of the day
        {"crew_id": str(ravi.id).replace(str(ravi.id)[0], "0" if str(ravi.id)[0] != "0" else "1", 1)},
    ]
    for extra in bad:
        r = api.post(URL, json=_api_body(world, **extra), headers=admin)
        assert r.status_code in (404, 422), (extra, r.text)
    assert world.db.scalar(select(BreakRule.id)) is None


def test_schr_par_09_api_effective_break(api, admin, world, site_cfg):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    sc.break_rule(DAY, DAY, cleaner=ravi, minutes=(600, 630))
    world.db.commit()
    r = api.get(f"{URL}/effective", params={"crew_id": str(ravi.id), "date": DAY.isoformat()},
                headers=admin)
    assert r.status_code == 200
    assert r.json() == {"crew_id": str(ravi.id), "date": DAY.isoformat(),
                        "start_minute": 600, "end_minute": 630, "source": "date_crew"}
    r = api.get(f"{URL}/effective", params={"crew_id": str(ravi.id),
                                            "date": (DAY + timedelta(days=1)).isoformat()},
                headers=admin).json()
    assert r["source"] == "site" and r["start_minute"] == _site()[0]


def _frozen_day(sc, cleaner, statuses):
    """A frozen schedule with one job on DAY for the cleaner in each status."""
    sched = Schedule(society_id=sc.site.id, start_date=SUNDAY, end_date=SUNDAY + timedelta(days=6),
                     status="Frozen")
    sc.db.add(sched)
    sc.db.flush()
    for n, status in enumerate(statuses):
        car = sc.car()
        visit = Visit(schedule_id=sched.id, vehicle_id=car.id, date=DAY)
        sc.db.add(visit)
        sc.db.flush()
        sc.db.add(Job(visit_id=visit.id, service="Cleaning-External", status=status,
                      duration_minutes=30, crew_id=cleaner.id, start_minute=400 + 40 * n))
    sc.db.flush()
    sched_id = sched.id
    sc.db.commit()
    return sched_id


def test_schr_brk_10_change_for_a_frozen_date_is_audited_and_counts_only_unstarted_jobs(
        api, admin, world, site_cfg):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    _frozen_day(sc, ravi, ["Scheduled", "In progress", "Completed"])
    r = api.post(URL, json=_api_body(world, crew_id=str(ravi.id), start_date=DAY.isoformat(),
                                     end_date=DAY.isoformat(), start_minute=600, end_minute=630),
                 headers=admin)
    assert r.status_code == 201, r.text
    row = world.db.scalars(select(DirectoryAudit).where(
        DirectoryAudit.entity == "break_rule", DirectoryAudit.action == "create")).one()
    d = row.detail
    assert d["frozen_dates"] == [DAY.isoformat()]
    assert d["jobs_affected"] == 1 and d["jobs_not_affected"] == 2
    assert d["society_id"] == str(world.society.id)
    assert row.admin_login_id is not None


def test_schr_brk_10_unfrozen_dates_report_no_frozen_dates(api, admin, world, site_cfg):
    sc = Scenario(world)
    sc.slots()
    ravi = sc.cleaner("Ravi", shift=(360, 780))
    world.db.commit()
    api.post(URL, json=_api_body(world, crew_id=str(ravi.id), start_date=DAY.isoformat(),
                                 end_date=DAY.isoformat(), start_minute=600, end_minute=630),
             headers=admin)
    d = world.db.scalars(select(DirectoryAudit).where(DirectoryAudit.entity == "break_rule")).one().detail
    assert d["frozen_dates"] == [] and d["jobs_affected"] == 0


def test_schr_brk_10_job_started_is_not_affected():
    assert breaks.affects_job("Scheduled") is True
    for status in ("In progress", "Completed", "Skipped", "Could not complete"):
        assert breaks.affects_job(status) is False


def test_lookup_only_planning_is_unchanged(world, site_cfg):
    sc = _scenario(world, site_cfg)
    sc.cleaner("Ravi", shift=(360, 780))
    car = sc.car()
    before = sc.run(SUNDAY)
    sc.break_rule(SUNDAY, SUNDAY, minutes=(400, 700))
    after = sc.run(SUNDAY)
    assert [(p.start, p.crew_id) for p in after.placed_on(SUNDAY, car)] == \
           [(p.start, p.crew_id) for p in before.placed_on(SUNDAY, car)]
