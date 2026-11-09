"""P3-3 (ADM-SVS-12, decision 8): a working-slot exception changes the slot for its
weekdays and dates only, beats the weekly off on them, and capacity and the
scheduler read the same slot through the resolver."""
from datetime import timedelta

from app.directory import slot_resolver
from app.directory.models import WorkingSlot, WorkingSlotException
from app.scheduling import capacity, service
from tests.scheduling.conftest import SUNDAY, run_days

EXT, INT, SPA = "Cleaning-External", "Cleaning-Internal", "Deep Spa"
WEDNESDAY = SUNDAY + timedelta(days=3)  # 21-Oct-26, the weekly off in these tests
THURSDAY = WEDNESDAY + timedelta(days=1)
BASE = "/v1/admin/scheduling"


def _root(world, closed=2):
    """Root slots for every service, closed on one weekday (Wednesday)."""
    days = [d for d in range(7) if d != closed]
    for name in (EXT, INT, SPA):
        world.drop_slots(name)
        world.db.add(WorkingSlot(society_id=world.society.id, service=name,
                                 start_minute=300, end_minute=660, days=days))
    world.db.commit()


def _exception(world, days, start, end, windows=((300, 660),), service_name=EXT):
    world.db.add(WorkingSlotException(
        society_id=world.society.id, service=service_name, start_date=start, end_date=end,
        days=list(days), windows=[{"start_minute": s, "end_minute": e} for s, e in windows]))
    world.db.commit()


def _cap(world, day):
    return capacity.capacity(world.db, world.society.id, day, day)[0]


def test_without_exceptions_the_resolver_reads_root_only(world):
    _root(world)
    site = slot_resolver.load(world.db, world.society.id)
    assert site.effective(EXT, WEDNESDAY).source == slot_resolver.WEEKLY_OFF
    assert site.effective(EXT, THURSDAY).windows == ((300, 660),)


def test_the_wednesday_exception_opens_wednesday_for_its_range_only(world):
    world.add_crew()  # a default crew member: 06:00 to 07:00, 60 minutes a day
    _root(world)
    _exception(world, [2], WEDNESDAY, WEDNESDAY + timedelta(days=6))
    assert _cap(world, WEDNESDAY)["capacity_minutes"] == 60
    assert _cap(world, WEDNESDAY + timedelta(days=7))["capacity_minutes"] == 0
    assert _cap(world, THURSDAY)["capacity_minutes"] == 60


def test_the_exception_beats_the_weekly_off_for_the_scheduler(world, api, admin):
    world.add_vehicle()
    world.add_crew()
    _root(world)
    _exception(world, [2], WEDNESDAY, WEDNESDAY)
    # A run covers one day (ADM-SCH-09): read Wednesday's own schedule, the fourth run.
    summary = run_days(api, admin, world.society.id, SUNDAY, 4)[3]
    board = api.get(f"{BASE}/board", headers=admin,
                    params={"schedule_id": summary["schedule_id"]}).json()
    on_wednesday = [j for j in board["jobs"] if j["date"] == WEDNESDAY.isoformat()]
    assert any(j["service"] == EXT and j["crew_id"] for j in on_wednesday)
    # The exception opens only Cleaning-External: Interior stays off on that Wednesday.
    assert not any(j["service"] == INT for j in on_wednesday)


def test_capacity_and_the_scheduler_read_the_same_demand_on_an_exception_day(world):
    world.add_crew()
    world.add_vehicle()
    _root(world)
    _exception(world, [2], WEDNESDAY, WEDNESDAY)
    site = slot_resolver.load(world.db, world.society.id)
    scheduler_demand = {
        (d.service, d.day)
        for d in service.build_demand(world.db, world.society.id, [WEDNESDAY], site=site)}
    assert (EXT, WEDNESDAY) in scheduler_demand
    assert not any(name == INT for name, _ in scheduler_demand)
    # Capacity counts the same Exterior: 30 minutes of work on the exception day.
    assert _cap(world, WEDNESDAY)["demand_minutes"] == 30
    assert _cap(world, WEDNESDAY)["capacity_minutes"] == 60
