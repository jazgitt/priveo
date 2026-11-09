"""Temporary crew roles: a role for a date range, with no change to days already
run and no change to the pairing rules (ADM-CRW-28; owner decisions 7 and 11)."""
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.platform.clock import today_ist
from app.platform.errors import ApiError
from app.scheduling import crew_roles, service
from tests.scheduling.test_crew_directory import directory, sc_of  # noqa: F401

CREW = "/v1/admin/crew"


def _avail(world, days):
    crew = service.load_crew(world.db, world.society.id)
    return service.availability(world.db, crew, days)


def test_role_on_applies_a_dated_role_only_on_its_days():
    today = today_ist()
    crew = SimpleNamespace(role="Member", role_periods=[
        (today + timedelta(2), today + timedelta(3), "Trainee"),
        (today + timedelta(5), None, "Manager"),
    ])
    assert crew_roles.role_on(crew, today + timedelta(1)) == "Member"
    assert crew_roles.role_on(crew, today + timedelta(2)) == "Trainee"
    assert crew_roles.role_on(crew, today + timedelta(3)) == "Trainee"
    assert crew_roles.role_on(crew, today + timedelta(4)) == "Member"
    assert crew_roles.role_on(crew, today + timedelta(30)) == "Manager"


def test_the_day_view_carries_that_days_role_and_the_record_fields():
    day = today_ist() + timedelta(1)
    crew = SimpleNamespace(role="Member", society_id="site", role_periods=[(day, day, "Trainee")])
    view = crew_roles.on_day(crew, day)
    assert view.role == "Trainee" and view.society_id == "site"
    assert crew_roles.on_day(crew, day + timedelta(1)) is crew


def test_a_period_that_began_earlier_covers_only_today_on(world, directory):  # noqa: F811
    """Days before today have already run, so a period never changes them (decision 7)."""
    from app.scheduling.models import SchedulingCrewRolePeriod

    sc = sc_of(world.db, directory()["crew"]["id"])
    today = today_ist()
    world.db.add(SchedulingCrewRolePeriod(
        crew_id=sc.id, role="Manager", start_date=today - timedelta(3), end_date=today + timedelta(1)))
    world.db.flush()
    crew_roles.attach(world.db, {sc.id: sc}, today)
    assert crew_roles.role_on(sc, today - timedelta(1)) == "Member"
    assert crew_roles.role_on(sc, today) == "Manager"
    assert crew_roles.role_on(sc, today + timedelta(1)) == "Manager"
    assert crew_roles.role_on(sc, today + timedelta(2)) == "Member"


def test_a_dated_member_role_gives_a_trainee_windows_only_on_those_days(world, directory):  # noqa: F811
    """A Trainee has no windows. A dated Member role gives them the same windows as a
    Member on the covered days only (the pairing is already in place, decision 11)."""
    member = directory()
    trainee = directory(role="Trainee", paired=member["crew"]["id"])
    t_sc = sc_of(world.db, trainee["crew"]["id"])
    m_sc = sc_of(world.db, member["crew"]["id"])
    today = today_ist()
    days = [today + timedelta(i) for i in range(1, 6)]
    assert all(_avail(world, days)[d].get(t_sc.id) is None for d in days)
    crew_roles.add_period(world.db, t_sc, "Member", days[1], days[2], None)
    world.db.commit()
    after = _avail(world, days)
    for day in (days[1], days[2]):
        assert after[day].get(t_sc.id) == after[day].get(m_sc.id)
    for day in (days[0], days[3], days[4]):
        assert after[day].get(t_sc.id) is None


def test_cancelling_a_period_gives_the_permanent_role_back(world, directory):  # noqa: F811
    member = directory()
    trainee = directory(role="Trainee", paired=member["crew"]["id"])
    t_sc = sc_of(world.db, trainee["crew"]["id"])
    today = today_ist()
    days = [today + timedelta(i) for i in range(1, 4)]
    before = _avail(world, days)
    row = crew_roles.add_period(world.db, t_sc, "Member", days[0], None, None)
    world.db.commit()
    assert _avail(world, days)[days[0]].get(t_sc.id) is not None
    crew_roles.cancel_period(world.db, t_sc, row.id)
    world.db.commit()
    assert _avail(world, days) == before


def test_a_past_start_date_and_an_end_before_the_start_are_refused(world, directory):  # noqa: F811
    sc = sc_of(world.db, directory()["crew"]["id"])
    today = today_ist()
    with pytest.raises(ApiError) as past:
        crew_roles.add_period(world.db, sc, "Manager", today - timedelta(1), None, None)
    assert past.value.status == 422
    with pytest.raises(ApiError) as order:
        crew_roles.add_period(world.db, sc, "Manager", today + timedelta(4), today + timedelta(2), None)
    assert order.value.status == 422


def test_periods_of_one_crew_member_cannot_overlap(world, directory):  # noqa: F811
    sc = sc_of(world.db, directory()["crew"]["id"])
    today = today_ist()
    crew_roles.add_period(world.db, sc, "Manager", today + timedelta(2), today + timedelta(4), None)
    with pytest.raises(ApiError) as overlap:
        crew_roles.add_period(world.db, sc, "Manager", today + timedelta(4), None, None)
    assert overlap.value.code == "period_overlap" and overlap.value.status == 409
    # A later period that starts after the first ends is fine.
    crew_roles.add_period(world.db, sc, "Manager", today + timedelta(5), None, None)


def test_pairing_rules_apply_to_a_temporary_role(world, directory):  # noqa: F811
    today = today_ist()
    alone = directory()
    with pytest.raises(ApiError) as no_pair:
        crew_roles.add_period(world.db, sc_of(world.db, alone["crew"]["id"]), "Trainee",
                              today + timedelta(1), None, None)
    assert no_pair.value.code == "pairing_required" and no_pair.value.status == 422
    member = directory()
    directory(role="Trainee", paired=member["crew"]["id"])
    with pytest.raises(ApiError) as paired:
        crew_roles.add_period(world.db, sc_of(world.db, member["crew"]["id"]), "Manager",
                              today + timedelta(1), None, None)
    assert paired.value.code == "trainees_paired" and paired.value.status == 409


def test_the_routes_add_list_and_cancel_a_period(api, admin, directory):  # noqa: F811
    made = directory()
    cid = made["crew"]["id"]
    start = (today_ist() + timedelta(2)).isoformat()
    no_dates = api.post(f"{CREW}/{cid}/role-periods", headers=admin, json={"role": "Manager"})
    assert no_dates.status_code == 422
    added = api.post(f"{CREW}/{cid}/role-periods", headers=admin,
                     json={"role": "Manager", "start_date": start})
    assert added.status_code == 201, added.text
    assert added.json()["periods"][0]["role"] == "Manager"
    listed = api.get(f"{CREW}/{cid}/role-periods", headers=admin).json()
    assert [p["start_date"] for p in listed] == [start]
    gone = api.delete(f"{CREW}/{cid}/role-periods/{listed[0]['id']}", headers=admin)
    assert gone.status_code == 200 and gone.json() == []


def test_a_permanent_role_change_ends_the_dated_roles(api, admin, directory):  # noqa: F811
    made = directory()
    cid = made["crew"]["id"]
    start = (today_ist() + timedelta(2)).isoformat()
    api.post(f"{CREW}/{cid}/role-periods", headers=admin, json={"role": "Manager", "start_date": start})
    changed = api.put(f"{CREW}/{cid}/role", headers=admin, json={"role": "Manager"})
    assert changed.status_code == 200, changed.text
    assert api.get(f"{CREW}/{cid}/role-periods", headers=admin).json() == []
