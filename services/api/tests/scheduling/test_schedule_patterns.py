"""S-02 / S-03 / ADM-SCH-41: a Weekly or Cycle schedule pattern per subscription.
A subscription with no pattern keeps the default (Exterior every day, Interior on
its day), and the calendar projection agrees with the scheduler on every day."""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.changes.models import ScheduleChange
from app.changes.projection import day_services
from app.customers.models import SchedulePattern, Subscription
from app.directory.models import DirectoryAudit, Plan
from app.scheduling import service
from app.scheduling.models import Visit
from tests.scheduling.conftest import SUNDAY
from tests.test_api import auth, login

EXT, INT = "Cleaning-External", "Cleaning-Internal"


def sub_of(world, vehicle):
    return world.db.scalar(select(Subscription).where(Subscription.vehicle_id == vehicle.id))


def put(api, admin, sub, **body):
    return api.put(f"/v1/admin/subscriptions/{sub.id}/schedule-pattern", headers=admin, json=body)


def demand(world, vehicle, start, count):
    days = [start + timedelta(days=i) for i in range(count)]
    got = service.build_demand(world.db, world.society.id, days)
    by_day = {d: [] for d in days}
    for item in got:
        if item.vehicle_id == vehicle.id:
            by_day[item.day].append(item.service)
    return by_day


def week(world, vehicle):
    return {d.strftime("%a"): s for d, s in demand(world, vehicle, SUNDAY, 7).items()}


def test_a_vehicle_with_no_pattern_keeps_the_default(world):
    vehicle = world.add_vehicle(interior_day="Wednesday")
    world.db.commit()
    assert week(world, vehicle) == {
        "Sun": [EXT], "Mon": [EXT], "Tue": [EXT], "Wed": [EXT, INT], "Thu": [EXT],
        "Fri": [EXT], "Sat": [EXT]}
    bare = world.add_vehicle()
    world.db.commit()
    assert all(s == [EXT] for s in week(world, bare).values())


def test_a_weekly_pattern_gives_a_rest_day_and_a_combined_day(world, api, admin):
    vehicle = world.add_vehicle(interior_day="Wednesday")
    world.db.commit()
    sub = sub_of(world, vehicle)
    # S-01: six days a week, five Exterior only and one Exterior + Interior (a Saturday).
    r = put(api, admin, sub, kind="Weekly",
            exterior_weekdays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
            interior_weekdays=["Saturday"])
    assert r.status_code == 200, r.text
    assert r.json()["exterior_count"] == 5 and r.json()["combined_count"] == 1
    world.db.expire_all()
    assert week(world, vehicle) == {
        "Sun": [], "Mon": [EXT], "Tue": [EXT], "Wed": [EXT], "Thu": [EXT], "Fri": [EXT],
        "Sat": [EXT, INT]}


def test_an_interior_weekday_is_also_an_exterior_day(world, api, admin):
    vehicle = world.add_vehicle()
    world.db.commit()
    sub = sub_of(world, vehicle)
    # S-04: Exterior + Interior on Saturdays only.
    assert put(api, admin, sub, kind="Weekly", exterior_weekdays=["Saturday"],
               interior_weekdays=["Saturday"]).status_code == 200
    world.db.expire_all()
    assert week(world, vehicle)["Sat"] == [EXT, INT]
    assert sum(1 for s in week(world, vehicle).values() if s) == 1


def test_a_cycle_pattern_counts_days_from_the_cycles_first_day(world, api, admin):
    vehicle = world.add_vehicle()  # first service date 01-Sep-26, a 30-day cycle
    world.db.commit()
    sub = sub_of(world, vehicle)
    r = put(api, admin, sub, kind="Cycle", exterior_days=[1, 3], combined_days=[2],
            exterior_count=2, combined_count=1)
    assert r.status_code == 200, r.text
    world.db.expire_all()
    got = demand(world, vehicle, date(2026, 10, 1), 36)  # cycle 2 is 01-Oct to 30-Oct
    on = {d.isoformat(): s for d, s in got.items() if s}
    # Cycle 2 starts 01-Oct and cycle 3 starts 31-Oct; it repeats every cycle.
    assert on == {
        "2026-10-01": [EXT], "2026-10-02": [EXT, INT], "2026-10-03": [EXT],
        "2026-10-31": [EXT], "2026-11-01": [EXT, INT], "2026-11-02": [EXT]}


def test_paused_days_move_the_cycle_as_they_move_the_billing_cycle(world, api, admin):
    vehicle = world.add_vehicle()
    world.db.add(ScheduleChange(
        customer_id=world.customer.id, vehicle_id=vehicle.id, kind="pause",
        start_date=date(2026, 9, 10), end_date=date(2026, 9, 12), status="Active", actor="admin"))
    world.db.commit()
    sub = sub_of(world, vehicle)
    assert put(api, admin, sub, kind="Cycle", exterior_days=[1], combined_days=[]).status_code == 200
    world.db.expire_all()
    on = [d.isoformat() for d, s in demand(world, vehicle, date(2026, 10, 1), 10).items() if s]
    assert on == ["2026-10-04"]  # three paused days: cycle 2 starts on 04-Oct, not 01-Oct


def test_the_calendar_projection_agrees_with_the_scheduler_on_every_day(world, api, admin):
    patterns = [
        None,
        dict(kind="Weekly", exterior_weekdays=["Monday", "Thursday", "Saturday"],
             interior_weekdays=["Thursday"]),
        dict(kind="Weekly", exterior_weekdays=["Sunday"], interior_weekdays=[]),
        dict(kind="Cycle", exterior_days=[1, 5, 30], combined_days=[7, 8]),
        dict(kind="Cycle", exterior_days=[], combined_days=[15]),
    ]
    start = SUNDAY - timedelta(days=20)
    for i, body in enumerate(patterns):
        vehicle = world.add_vehicle(interior_day="Friday" if i == 0 else None)
        world.db.commit()
        if body:
            assert put(api, admin, sub_of(world, vehicle), **body).status_code == 200
    world.db.expire_all()
    for vehicle in world.vehicles:
        sub = sub_of(world, vehicle)
        want = {d: s for d, s in demand(world, vehicle, start, 75).items()}
        for day, services in want.items():
            assert day_services(sub, day) == services, (vehicle.registration, day)


def test_a_plan_without_interior_refuses_interior_days_and_the_scheduler_drops_them(world, api, admin):
    plan = Plan(name="Exterior only", monthly_price_rupees=699, includes_interior=False)
    world.db.add(plan)
    vehicle = world.add_vehicle()
    world.db.flush()
    sub = sub_of(world, vehicle)
    sub.plan_id = plan.id
    world.db.commit()
    assert put(api, admin, sub, kind="Weekly", exterior_weekdays=["Monday"],
               interior_weekdays=["Monday"]).status_code == 422
    assert put(api, admin, sub, kind="Cycle", exterior_days=[], combined_days=[2]).status_code == 422
    assert put(api, admin, sub, kind="Weekly", exterior_weekdays=["Monday"]).status_code == 200


@pytest.mark.parametrize("body", [
    dict(kind="Daily"),
    dict(kind="Weekly"),  # no Exterior day
    dict(kind="Weekly", exterior_weekdays=["Funday"]),
    dict(kind="Weekly", exterior_weekdays=["Monday"], interior_weekdays=["Tuesday"]),
    dict(kind="Cycle"),  # no days
    dict(kind="Cycle", exterior_days=[0]),
    dict(kind="Cycle", exterior_days=[31]),
    dict(kind="Cycle", exterior_days=[2, 2]),
    dict(kind="Cycle", exterior_days=[2], combined_days=[2]),
    dict(kind="Cycle", exterior_days=[1, 2], exterior_count=3),
    dict(kind="Cycle", combined_days=[1], combined_count=2),
])
def test_bad_patterns_are_refused_and_nothing_is_saved(world, api, admin, body):
    vehicle = world.add_vehicle()
    world.db.commit()
    sub = sub_of(world, vehicle)
    assert put(api, admin, sub, **body).status_code == 422
    assert world.db.scalar(select(SchedulePattern)) is None


def test_read_replace_and_clear_a_pattern_with_audit(world, api, admin):
    vehicle = world.add_vehicle(interior_day="Monday")
    world.db.commit()
    sub = sub_of(world, vehicle)
    url = f"/v1/admin/subscriptions/{sub.id}/schedule-pattern"
    assert api.get(url, headers=admin).json() | {} == {
        "kind": "Default", "exterior_weekdays": [], "interior_weekdays": [], "exterior_days": [],
        "combined_days": [], "cycle_days": 30, "default_interior_day": "Monday",
        "exterior_count": None, "combined_count": None}
    put(api, admin, sub, kind="Weekly", exterior_weekdays=["Friday", "Monday"])
    put(api, admin, sub, kind="Cycle", exterior_days=[4, 2], combined_days=[9])
    body = api.get(url, headers=admin).json()
    assert body["kind"] == "Cycle" and body["exterior_days"] == [2, 4] and body["combined_days"] == [9]
    assert api.delete(url, headers=admin).status_code == 204
    assert api.delete(url, headers=admin).status_code == 204  # again
    assert api.get(url, headers=admin).json()["kind"] == "Default"
    world.db.expire_all()
    assert week(world, vehicle)["Mon"] == [EXT, INT]  # the default is back
    kinds = [a.detail["schedule_pattern"] for a in world.db.scalars(select(DirectoryAudit).where(
        DirectoryAudit.entity_id == str(sub.id)).order_by(DirectoryAudit.at))]
    assert kinds == [["Default", "Weekly"], ["Weekly", "Cycle"], ["Cycle", "Default"]]


def test_only_the_admin_may_use_it_and_unknown_ids_are_404(world, api, admin):
    import uuid
    vehicle = world.add_vehicle()
    world.db.commit()
    sub = sub_of(world, vehicle)
    url = f"/v1/admin/subscriptions/{sub.id}/schedule-pattern"
    ghost = f"/v1/admin/subscriptions/{uuid.uuid4()}/schedule-pattern"
    assert api.get(ghost, headers=admin).status_code == 404
    assert api.put(ghost, headers=admin, json={"kind": "Weekly"}).status_code == 404
    assert api.delete(ghost, headers=admin).status_code == 404
    assert api.get(url).status_code == 401
    crew = auth(login(api, "crew")["access_token"])
    assert api.put(url, headers=crew, json={"kind": "Weekly"}).status_code == 403


def test_a_planned_week_follows_the_pattern(world, api, admin):
    world.add_crew(start=360, end=840)
    vehicle = world.add_vehicle()
    world.db.commit()
    assert put(api, admin, sub_of(world, vehicle), kind="Weekly",
               exterior_weekdays=["Monday", "Wednesday"], interior_weekdays=["Wednesday"]
               ).status_code == 200
    r = api.post("/v1/admin/scheduling/run", headers=admin, json={
        "society_id": str(world.society.id), "start_date": SUNDAY.isoformat(), "days": 7})
    assert r.status_code == 200, r.text
    world.db.expire_all()
    dates = sorted(v.date for v in world.db.scalars(select(Visit).where(Visit.vehicle_id == vehicle.id)))
    assert dates == [SUNDAY + timedelta(days=1), SUNDAY + timedelta(days=3)]
