"""Preferred Interior day and the actual Interior of the plan week (item 18.5).

A small gap (an actual Interior on the preferred day or up to SMALL_GAP_DAYS
later, same week) keeps the preferred day. Otherwise the Interior is held as
optional on the preferred day, with the message, and is Unscheduled.
"""
from datetime import date, timedelta

from sqlalchemy import select

from app.scheduling.demand_providers.entitlement import HELD_NOTE
from app.scheduling.models import Job, Visit
from tests.scheduling.builders import INTERNAL, Scenario

WEEK1 = date(2026, 11, 2)  # Monday
MONDAY, TUESDAY, SATURDAY = WEEK1, WEEK1 + timedelta(days=1), WEEK1 + timedelta(days=5)


def _scenario(world):
    sc = Scenario(world)
    sc.slots()
    cleaner = sc.cleaner(shift=(360, 660))
    car = sc.car(interior_day="Monday")
    sc.entitlement(car, WEEK1)
    return sc, car, cleaner


def _completed_interior(sc, car, cleaner, day):
    job = sc.fixed(car, day, cleaner, 420, service_name=INTERNAL,
                   schedule_start=WEEK1, days=7)
    job.status = "Completed"
    sc.db.flush()


def _interior_on(sc, car, day):
    sc.db.expire_all()
    return sc.db.execute(
        select(Job).join(Visit, Visit.id == Job.visit_id)
        .where(Visit.vehicle_id == car.id, Visit.date == day, Job.service == INTERNAL,
               Job.status == "Scheduled", Job.manual.is_(False))).scalars().all()


def test_schr_int_27_small_gap_keeps_the_preferred_day(world, rules_v2):
    sc, car, cleaner = _scenario(world)
    _completed_interior(sc, car, cleaner, TUESDAY)  # one day after Monday: a small gap
    res = sc.run(WEEK1, days=7)
    (job,) = _interior_on(sc, car, MONDAY)
    assert job.crew_id is not None
    assert not any("Preferred Interior day moved" in (u.note or "") for u in res.unassigned)


def test_schr_int_27_large_gap_holds_the_interior_as_optional_and_unscheduled(world, rules_v2):
    sc, car, cleaner = _scenario(world)
    _completed_interior(sc, car, cleaner, SATURDAY)  # five days after Monday: a large gap
    res = sc.run(WEEK1, days=7)
    (job,) = _interior_on(sc, car, MONDAY)
    assert job.crew_id is None
    assert job.note == HELD_NOTE.format(when=SATURDAY.strftime("%d-%b-%y"))
    assert any(u.day == MONDAY and u.vehicle_id == car.id for u in res.unassigned)


def test_schr_int_28_no_completed_interior_in_the_week_keeps_the_preferred_day(world, rules_v2):
    # Changed 08-Nov-26 (owner rule): the last actual Interior is the most recent
    # completed one, not one in the plan week. With no completed Interior at all
    # the preferred day is kept and nothing is held.
    sc, car, _cleaner = _scenario(world)
    sc.run(WEEK1, days=7)
    (job,) = _interior_on(sc, car, MONDAY)
    assert job.crew_id is not None
    assert job.note != HELD_NOTE.format(when="none this week")
    assert not (job.note or "").startswith("Preferred Interior day moved")
