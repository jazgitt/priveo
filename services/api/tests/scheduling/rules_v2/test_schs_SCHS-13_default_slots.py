"""SCHS-13: a new site's default slots leave the weekly-off weekday (Wednesday)
out, for all three services; existing sites are untouched."""
from sqlalchemy import select

from app.directory import lookup
from app.directory.models import Society, WorkingSlot
from app.directory.seed import add_default_slots

SERVICES = {"Cleaning-External", "Cleaning-Internal", "Deep Spa"}
WEDNESDAY = 2


def _new_site(world, name="Fresh Site"):
    society = Society(name=name, sector="S", city="C", active=True)
    world.db.add(society)
    world.db.flush()
    add_default_slots(world.db, society)
    world.db.commit()
    return society


def _slots(world, society):
    return list(world.db.scalars(select(WorkingSlot).where(WorkingSlot.society_id == society.id)))


def test_schr_par_03_new_site_has_no_slot_on_wednesday_for_any_service(world):
    slots = _slots(world, _new_site(world))
    assert {s.service for s in slots} == SERVICES
    assert all(WEDNESDAY not in s.days for s in slots)


def test_schr_par_03_new_site_is_open_every_other_day_including_deep_spa(world):
    slots = _slots(world, _new_site(world))
    for s in slots:
        assert sorted(s.days) == [0, 1, 3, 4, 5, 6]


def test_schr_par_03_existing_sites_slots_are_unchanged(world):
    old = Society(name="Old Site", sector="S", city="C", active=True)
    world.db.add(old)
    world.db.flush()
    world.db.add(WorkingSlot(society_id=old.id, service="Cleaning-External",
                             start_minute=300, end_minute=660, days=list(range(7))))
    world.db.commit()
    _new_site(world)
    lookup.invalidate(world.db)
    kept = _slots(world, old)
    assert len(kept) == 1 and sorted(kept[0].days) == list(range(7))
