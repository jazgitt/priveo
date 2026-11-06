"""SCHS-51: the entitlement backfill script. Tested here, never run on a real database."""
import importlib.util
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.changes.models import ScheduleChange
from app.customers.models import Subscription
from app.directory.models import Plan
from app.scheduling.models import InteriorEntitlement
from tests.scheduling.builders import Scenario

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "rules_v2_backfill.py"
spec = importlib.util.spec_from_file_location("rules_v2_backfill", SCRIPT)
script = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = script
spec.loader.exec_module(script)

TODAY = date(2026, 11, 4)  # a Wednesday of the service week starting Monday 02-Nov-26
WEEK = date(2026, 11, 2)


def _count(db, car=None):
    query = select(func.count()).select_from(InteriorEntitlement)
    if car is not None:
        query = query.where(InteriorEntitlement.vehicle_id == car.id)
    return db.scalar(query)


def test_schs_51_the_dry_run_counts_rows_and_saves_nothing(world):
    sc = Scenario(world)
    sc.cars(3, interior=True)
    sc.db.commit()
    report = script.backfill(sc.db, TODAY)
    assert (report.subscriptions, report.created) == (3, 3)
    assert _count(sc.db) == 0


def test_schs_51_only_the_current_week_is_created_and_there_is_no_past_debt(world):
    sc = Scenario(world)
    car = sc.car(interior=True)  # its first service date is 01-Sep-26: nine weeks back
    sc.db.commit()
    script.backfill(sc.db, TODAY, apply=True)
    (row,) = sc.db.scalars(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == car.id))
    assert (row.service_week_start, row.status) == (WEEK, "Pending")


def test_schs_51_a_second_run_adds_nothing(world):
    sc = Scenario(world)
    sc.cars(2, interior=True)
    sc.db.commit()
    assert script.backfill(sc.db, TODAY, apply=True).created == 2
    assert script.backfill(sc.db, TODAY, apply=True).created == 0
    assert _count(sc.db) == 2


def test_schs_51_only_active_subscriptions_with_an_interior_plan_are_included(world):
    sc = Scenario(world)
    sc.car(interior=True)
    sc.car(interior=True, status="Paused")
    sc.car()  # Exterior-only plan
    sc.db.commit()
    report = script.backfill(sc.db, TODAY, apply=True)
    assert report.subscriptions == 2 and report.created == 1


def test_schs_51_a_car_whose_first_service_is_next_week_gets_no_row(world):
    sc = Scenario(world)
    car = sc.car(interior=True)
    sub = sc.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    sub.first_service_date = WEEK + timedelta(days=7)
    sc.db.commit()
    assert script.backfill(sc.db, TODAY, apply=True).created == 0


def test_schs_51_a_fully_paused_week_is_waived(world):
    sc = Scenario(world)
    car = sc.car(interior=True)
    sc.db.add(ScheduleChange(customer_id=world.customer.id, vehicle_id=car.id, kind="pause",
                             start_date=WEEK - timedelta(days=1), end_date=WEEK + timedelta(days=8),
                             status="Active", actor="customer"))
    sc.db.commit()
    report = script.backfill(sc.db, TODAY, apply=True)
    assert report.created == 1 and report.waived == 1
    assert sc.db.scalar(select(InteriorEntitlement.status)) == "Waived"


def test_schs_51_a_plan_without_interior_care_is_left_out(world):
    sc = Scenario(world)
    car = sc.car(interior=True)
    sub = sc.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    plan = Plan(name="Silver", monthly_price_rupees=799, includes_interior=False)
    sc.db.add(plan)
    sc.db.flush()
    sub.plan_id = plan.id
    sc.db.commit()
    assert script.backfill(sc.db, TODAY, apply=True).created == 0


def test_schs_51_undo_deletes_only_the_rows_a_run_made_and_still_owed(world):
    sc = Scenario(world)
    car = sc.car(interior=True)
    old = sc.entitlement(car, WEEK - timedelta(days=14))
    old.created_at = datetime(2026, 11, 1, tzinfo=UTC)
    sc.db.commit()
    before_run = datetime.now(UTC) - timedelta(minutes=1)
    script.backfill(sc.db, TODAY, apply=True)
    assert _count(sc.db) == 2
    assert script.undo(sc.db, before_run).deleted == 1 and _count(sc.db) == 2  # trial run
    assert script.undo(sc.db, before_run, apply=True).deleted == 1
    (left,) = sc.db.scalars(select(InteriorEntitlement))
    assert left.id == old.id
