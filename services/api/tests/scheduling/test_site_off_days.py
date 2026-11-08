"""A weekday the site has no working slot for a service has no demand for it
(ADM-CAP-08)."""
from datetime import time, timedelta

from app.directory.models import WorkingSlot
from app.scheduling.service import build_demand
from tests.scheduling.conftest import SUNDAY, run_days

BASE = "/v1/admin/scheduling"
MONDAY = SUNDAY + timedelta(days=1)


def slot(world, service, days, start=300, end=660):
    world.drop_slots(service)
    world.db.add(WorkingSlot(society_id=world.society.id, service=service,
                             start_minute=start, end_minute=end, days=days))


def services_on(world, day):
    return {(d.service, d.day) for d in build_demand(world.db, world.society.id, [day])}


def test_a_day_without_a_slot_has_no_demand_and_other_days_are_unchanged(world):
    world.add_vehicle()
    slot(world, "Cleaning-External", [0, 1, 2, 3, 4, 5])  # Sunday off
    world.db.commit()
    assert services_on(world, SUNDAY) == set()
    assert services_on(world, MONDAY) == {("Cleaning-External", MONDAY)}


def test_a_society_with_no_slots_is_not_filtered(world):
    world.add_vehicle()
    world.db.commit()
    assert len(services_on(world, SUNDAY)) == 1


def test_a_service_with_no_slot_at_all_is_not_filtered(world):
    world.add_vehicle(interior_day="Sunday")
    slot(world, "Cleaning-External", [0, 1, 2, 3, 4, 5])
    world.db.commit()
    # Cleaning-Internal has no slot anywhere, so it is not zeroed.
    assert services_on(world, SUNDAY) == {("Cleaning-Internal", SUNDAY)}


def test_each_service_follows_its_own_slots(world):
    world.add_vehicle(interior_day="Sunday")
    slot(world, "Cleaning-External", [0, 1, 2, 3, 4, 5])
    slot(world, "Cleaning-Internal", [6])
    world.db.commit()
    assert services_on(world, SUNDAY) == {("Cleaning-Internal", SUNDAY)}


def test_capacity_and_the_run_agree_on_an_off_day(api, admin, world):
    from app.directory import lookup
    from app.directory.models import DirectoryService
    for order, name in enumerate(("Cleaning-External", "Cleaning-Internal")):
        # This test is not about the default length: pin both cleans to 20.
        world.db.add(DirectoryService(name=name, duration_minutes=20, min_photos=2,
                                      min_videos=1, sort_order=order))
    lookup.invalidate()
    world.add_crew()
    for _ in range(3):
        world.add_vehicle(cutoff=time(8, 0))
    slot(world, "Cleaning-External", [1, 2, 3, 4, 5, 6])  # Monday off
    world.db.commit()

    # Sunday and Monday, one daily run each (ADM-SCH-09); each day's board shows its own day.
    days = run_days(api, admin, world.society.id, SUNDAY, 2)
    boards = [api.get(f"{BASE}/board", headers=admin, params={"schedule_id": d["schedule_id"]}).json()
              for d in days]
    jobs = [j for b in boards for j in b["jobs"]]
    by_day = {d["date"]: d for b in boards for d in b["days"]}
    # Every Exterior fits; only Interiors (ledger demand, SCHS-36) can be left over.
    assert all(j["service"] == "Cleaning-Internal" for j in jobs if j["crew_id"] is None)
    off = by_day[MONDAY.isoformat()]
    assert off["demand_minutes"] == 0 and not off["over_capacity"] and off["demand"] == []
    assert by_day[SUNDAY.isoformat()]["demand_minutes"] == 60
    assert all(j["date"] != MONDAY.isoformat() or j["service"] == "Cleaning-Internal" for j in jobs)


def test_a_closed_weekday_gives_no_cleaner_window(world):
    from app.scheduling import service

    world.add_crew()
    for name in ("Cleaning-External", "Cleaning-Internal", "Deep Spa"):
        slot(world, name, [0, 1, 3, 4, 5, 6])  # Wednesday off
    world.db.commit()
    crew = service.load_crew(world.db, world.society.id)
    wednesday = SUNDAY + timedelta(days=3)
    assert service.availability(world.db, crew, [wednesday])[wednesday] == {}
