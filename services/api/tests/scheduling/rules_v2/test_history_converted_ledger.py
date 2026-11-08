"""Migrated history counts in the Interior ledger like live work (owner decision, 8 Nov 2026):
a service week with a migrated Interior is Completed and owes nothing more; a week
before the car's first service date creates no debt; the planner's own rows are
unchanged for the weeks after."""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.customers.history_convert import admin_login_id, write_record
from app.customers.models import Subscription
from app.directory.models import Plan
from app.scheduling import entitlements
from app.scheduling.models import InteriorEntitlement

MONDAY = date(2026, 10, 19)  # a service week runs Monday to Sunday (SCHR-PAR-13)
WEEK2 = MONDAY + timedelta(days=7)


@pytest.fixture
def car(world):
    car = world.add_vehicle()
    sub = world.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    sub.first_service_date = MONDAY
    plan = Plan(name="Gold", monthly_price_rupees=1299, includes_interior=True)
    world.db.add(plan)
    world.db.flush()
    sub.plan_id = plan.id
    world.db.flush()
    return car


def _rows(db, car):
    return list(db.scalars(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == car.id)
        .order_by(InteriorEntitlement.service_week_start, InteriorEntitlement.seq)))


def test_schr_int_29_a_migrated_interior_completes_its_week_and_the_planner_owes_only_the_rest(world, car):
    who = admin_login_id(world.db)
    write_record(world.db, car, MONDAY + timedelta(days=1), services="Exterior + Interior",
                 outcome="Completed", skip_reason="", admin_id=who)
    world.db.flush()
    sub = world.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    entitlements.ensure(world.db, sub, through=WEEK2)
    rows = _rows(world.db, car)
    first = [r for r in rows if r.service_week_start == MONDAY]
    assert [(r.status, r.completed_on) for r in first] == [("Completed", MONDAY + timedelta(days=1))]
    assert [r.status for r in rows if r.service_week_start == WEEK2] == ["Pending"]


def test_schr_int_29_a_migrated_week_before_the_first_service_date_creates_no_debt(world, car):
    who = admin_login_id(world.db)
    before = MONDAY - timedelta(days=7)
    write_record(world.db, car, before + timedelta(days=2), services="Exterior + Interior",
                 outcome="Completed", skip_reason="", admin_id=who)
    world.db.flush()
    sub = world.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    entitlements.ensure(world.db, sub, through=WEEK2)
    weeks = {r.service_week_start for r in _rows(world.db, car)}
    assert before in weeks                       # the migrated Interior, Completed
    assert MONDAY in weeks and WEEK2 in weeks    # the planner's own weeks, owed as usual
    pending_before = [r for r in _rows(world.db, car)
                      if r.service_week_start == before and r.status == "Pending"]
    assert pending_before == []                  # nothing owed for the weeks before the first service
