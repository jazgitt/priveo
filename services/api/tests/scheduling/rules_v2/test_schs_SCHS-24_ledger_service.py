"""SCHS-24: the entitlement ledger service. It creates, moves and waives rows of
interior_entitlements; nothing in the planner reads it yet."""
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.changes.models import ScheduleChange
from app.customers.models import Subscription
from app.directory import lookup
from app.directory.models import Plan, SystemSetting
from app.scheduling import entitlements
from app.scheduling.models import InteriorEntitlement, Job, Visit
from tests.scheduling.conftest import SUNDAY

MONDAY = date(2026, 10, 19)  # a service week runs Monday to Sunday (SCHR-PAR-13)
WEEK2 = MONDAY + timedelta(days=7)
WEEK3 = MONDAY + timedelta(days=14)


@pytest.fixture
def sub(world):
    car = world.add_vehicle()
    s = world.db.scalar(select(Subscription).where(Subscription.vehicle_id == car.id))
    s.first_service_date = MONDAY
    plan = Plan(name="Gold", monthly_price_rupees=1299, includes_interior=True)
    world.db.add(plan)
    world.db.flush()
    s.plan_id = plan.id
    world.db.flush()
    return s


def _rows(db, sub):
    return list(db.scalars(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == sub.vehicle_id)
        .order_by(InteriorEntitlement.service_week_start, InteriorEntitlement.seq)))


def _setting(db, key, value):
    db.merge(SystemSetting(key=key, value=str(value)))
    db.flush()
    lookup.invalidate()


def _pause(world, sub, start, end, status="Active"):
    world.db.add(ScheduleChange(customer_id=world.customer.id, vehicle_id=sub.vehicle_id,
                                kind="pause", start_date=start, end_date=end,
                                status=status, actor="customer"))
    world.db.flush()


def _skip(world, sub, day):
    world.db.add(ScheduleChange(customer_id=world.customer.id, vehicle_id=sub.vehicle_id,
                                kind="skip", start_date=day, end_date=day,
                                status="Active", actor="customer"))
    world.db.flush()


def _job(world, sub, service="Cleaning-Internal", **kw):
    from app.scheduling import service as svc
    schedule = svc.get_or_create_schedule(world.db, world.society.id, MONDAY, 7)
    visit = world.db.scalar(select(Visit).where(
        Visit.schedule_id == schedule.id, Visit.vehicle_id == sub.vehicle_id))
    if visit is None:
        visit = Visit(schedule_id=schedule.id, vehicle_id=sub.vehicle_id, date=MONDAY)
        world.db.add(visit)
        world.db.flush()
    job = Job(visit_id=visit.id, service=service, duration_minutes=40, **kw)
    world.db.add(job)
    world.db.flush()
    return job


# ---- service week (SCHR-PAR-13) --------------------------------------------

def test_schr_par_13_a_service_week_runs_monday_to_sunday(world):
    for offset in range(7):
        assert entitlements.week_start(world.db, MONDAY + timedelta(days=offset)) == MONDAY
    assert entitlements.week_start(world.db, SUNDAY) == MONDAY - timedelta(days=7)


def test_schr_par_13_the_week_start_is_its_own_setting(world):
    _setting(world.db, "schedule.service_week_start", 6)
    assert entitlements.week_start(world.db, SUNDAY) == SUNDAY
    assert entitlements.week_start(world.db, MONDAY) == SUNDAY


# ---- creation (SCHR-INT-19) -------------------------------------------------

def test_schr_int_19_one_row_for_each_week_from_the_first_service_week(world, sub):
    entitlements.ensure(world.db, sub, through=WEEK3 + timedelta(days=2))
    rows = _rows(world.db, sub)
    assert [r.service_week_start for r in rows] == [MONDAY, WEEK2, WEEK3]
    assert {r.status for r in rows} == {"Pending"}
    assert {r.subscription_id for r in rows} == {sub.id}


def test_schr_int_19_creating_twice_makes_no_second_row(world, sub):
    entitlements.ensure(world.db, sub, through=WEEK2)
    again = entitlements.ensure(world.db, sub, through=WEEK2)
    assert again == []
    assert len(_rows(world.db, sub)) == 2


def test_schr_int_19_nothing_before_the_first_service_date(world, sub):
    entitlements.ensure(world.db, sub, through=MONDAY - timedelta(days=3))
    assert _rows(world.db, sub) == []


def test_schr_int_19_only_active_subscriptions_get_new_rows(world, sub):
    sub.status = "Cancelled"
    entitlements.ensure(world.db, sub, through=WEEK2)
    assert _rows(world.db, sub) == []


# ---- the per-week count comes from the setting (SCHR-PAR-12, INT-06) -------

def test_schr_par_12_the_count_per_week_is_the_setting(world, sub):
    _setting(world.db, "schedule.interior_entitlement_per_week", 2)
    entitlements.ensure(world.db, sub, through=MONDAY)
    assert [r.seq for r in _rows(world.db, sub)] == [1, 2]


def test_schr_par_12_a_count_of_zero_owes_nothing(world, sub):
    _setting(world.db, "schedule.interior_entitlement_per_week", 0)
    entitlements.ensure(world.db, sub, through=WEEK2)
    assert _rows(world.db, sub) == []


def test_schr_int_06_a_second_interior_is_never_claimed_for_the_same_week(world, sub):
    entitlements.ensure(world.db, sub, through=MONDAY)
    first = entitlements.claim(world.db, sub.vehicle_id, MONDAY)
    entitlements.plan(world.db, first, _job(world, sub))
    assert entitlements.claim(world.db, sub.vehicle_id, MONDAY) is None


# ---- part weeks (SCHR-INT-20) ----------------------------------------------

def test_schr_int_20_a_part_first_week_owes_one_interior(world, sub):
    sub.first_service_date = MONDAY + timedelta(days=5)  # Saturday
    entitlements.ensure(world.db, sub, through=MONDAY + timedelta(days=6))
    rows = _rows(world.db, sub)
    assert [(r.service_week_start, r.status) for r in rows] == [(MONDAY, "Pending")]


def test_schr_int_20_a_plan_change_keeps_the_week_if_the_new_plan_has_interior(world, sub):
    other = Plan(name="Silver Plus", monthly_price_rupees=999, includes_interior=True)
    world.db.add(other)
    world.db.flush()
    entitlements.ensure(world.db, sub, through=MONDAY)
    sub.pending_plan_id, sub.pending_from = other.id, MONDAY + timedelta(days=3)
    assert entitlements.ensure(world.db, sub, through=MONDAY) == []
    assert len(_rows(world.db, sub)) == 1


def test_schr_int_20_a_week_touched_by_an_interior_plan_is_owed_after_a_change(world, sub):
    plain = Plan(name="Basic", monthly_price_rupees=699, includes_interior=False)
    world.db.add(plain)
    world.db.flush()
    sub.pending_plan_id, sub.pending_from = plain.id, MONDAY + timedelta(days=3)
    entitlements.ensure(world.db, sub, through=WEEK2)
    assert [r.service_week_start for r in _rows(world.db, sub)] == [MONDAY]


# ---- pauses, skips, misses (SCHR-INT-21) -----------------------------------

def test_schr_int_21_a_fully_paused_week_is_waived(world, sub):
    entitlements.ensure(world.db, sub, through=WEEK2)
    _pause(world, sub, MONDAY, MONDAY + timedelta(days=6))
    entitlements.refresh_waivers(world.db, sub)
    first, second = _rows(world.db, sub)
    assert (first.status, first.waived_reason) == ("Waived", "paused")
    assert second.status == "Pending"


def test_schr_int_21_a_pause_over_part_of_the_week_leaves_it_owed(world, sub):
    entitlements.ensure(world.db, sub, through=MONDAY)
    _pause(world, sub, MONDAY, MONDAY + timedelta(days=5))
    entitlements.refresh_waivers(world.db, sub)
    assert _rows(world.db, sub)[0].status == "Pending"


def test_schr_int_21_a_one_day_skip_stays_pending(world, sub):
    entitlements.ensure(world.db, sub, through=MONDAY)
    _skip(world, sub, MONDAY + timedelta(days=2))
    entitlements.refresh_waivers(world.db, sub)
    assert _rows(world.db, sub)[0].status == "Pending"


def test_schr_int_21_a_cancelled_pause_returns_the_week_to_pending(world, sub):
    entitlements.ensure(world.db, sub, through=MONDAY)
    _pause(world, sub, MONDAY - timedelta(days=1), MONDAY + timedelta(days=7))
    entitlements.refresh_waivers(world.db, sub)
    assert _rows(world.db, sub)[0].status == "Waived"
    world.db.scalar(select(ScheduleChange)).status = "Cancelled"
    world.db.flush()
    entitlements.refresh_waivers(world.db, sub)
    row = _rows(world.db, sub)[0]
    assert (row.status, row.waived_reason) == ("Pending", None)


def test_schr_int_21_waiving_never_touches_a_completed_row(world, sub):
    entitlements.ensure(world.db, sub, through=MONDAY)
    entitlements.complete(world.db, _rows(world.db, sub)[0], _job(world, sub), MONDAY)
    _pause(world, sub, MONDAY, MONDAY + timedelta(days=6))
    entitlements.refresh_waivers(world.db, sub)
    assert _rows(world.db, sub)[0].status == "Completed"


def test_schr_int_21_an_operational_miss_stays_owed_and_keeps_the_week(world, sub):
    entitlements.ensure(world.db, sub, through=WEEK2)
    row = entitlements.claim(world.db, sub.vehicle_id, MONDAY)
    entitlements.plan(world.db, row, _job(world, sub))
    entitlements.defer(world.db, row)  # missed: car, keys, capacity
    assert (row.status, row.job_id, row.service_week_start) == ("Pending", None, MONDAY)
    entitlements.refresh_waivers(world.db, sub)
    assert row.status == "Pending"
    # Carry-forward: it is still the oldest owed Interior at the next week.
    assert entitlements.oldest_owed(world.db, sub.vehicle_id).service_week_start == MONDAY


# ---- states and the week being kept (SCHR-INT-11) --------------------------

def test_schr_int_11_planned_keeps_the_job_and_the_week_until_done(world, sub):
    entitlements.ensure(world.db, sub, through=MONDAY)
    row = entitlements.claim(world.db, sub.vehicle_id, MONDAY)
    job = _job(world, sub)
    entitlements.plan(world.db, row, job)
    assert (row.status, row.job_id) == ("Planned", job.id)
    assert job.service_week_start == MONDAY
    entitlements.complete(world.db, row, job, WEEK2 + timedelta(days=1))
    assert (row.status, row.completed_on) == ("Completed", WEEK2 + timedelta(days=1))
    assert row.service_week_start == MONDAY


def test_schr_int_11_completing_in_a_later_week_credits_the_original_week(world, sub):
    entitlements.ensure(world.db, sub, through=WEEK2)
    row = entitlements.oldest_owed(world.db, sub.vehicle_id)
    assert row.service_week_start == MONDAY
    job = _job(world, sub)
    entitlements.plan(world.db, row, job)
    entitlements.complete(world.db, row, job, WEEK2)
    assert _rows(world.db, sub)[0].status == "Completed"
    assert _rows(world.db, sub)[1].status == "Pending"


def test_schr_int_21_a_cancelled_subscription_cancels_its_open_rows(world, sub):
    entitlements.ensure(world.db, sub, through=WEEK3)
    entitlements.complete(world.db, _rows(world.db, sub)[0], _job(world, sub), MONDAY)
    entitlements.cancel_open(world.db, sub, from_day=WEEK2)
    assert [r.status for r in _rows(world.db, sub)] == ["Completed", "Cancelled", "Cancelled"]


# ---- extras, Deep Spa, plans without Interior, Custom ----------------------

def test_schr_int_22_extras_and_deep_spa_do_not_use_the_entitlement(world, sub):
    assert entitlements.uses_entitlement(_job(world, sub))
    assert not entitlements.uses_entitlement(_job(world, sub, service="Deep Spa"))
    assert not entitlements.uses_entitlement(_job(world, sub, service="Cleaning-External"))
    extra = _job(world, sub)
    from app.customers.models import AddonRequest
    req = AddonRequest(customer_id=world.customer.id, vehicle_id=sub.vehicle_id,
                       service="Extra interior cleaning", service_date=MONDAY)
    world.db.add(req)
    world.db.flush()
    extra.addon_request_id = req.id
    assert not entitlements.uses_entitlement(extra)


def test_schr_int_23_a_plan_without_interior_has_no_entitlement(world, sub):
    sub.plan_id = world.db.scalar(select(Plan.id).where(Plan.name == "Gold"))
    world.db.get(Plan, sub.plan_id).includes_interior = False
    entitlements.ensure(world.db, sub, through=WEEK3)
    assert _rows(world.db, sub) == []
    assert entitlements.claim(world.db, sub.vehicle_id, MONDAY) is None


def test_schr_int_25_a_custom_subscription_is_treated_as_normal(world, sub):
    sub.interior_day = "Custom"
    sub.interior_day_notes = "Tuesdays and Fridays when the car is home"
    entitlements.ensure(world.db, sub, through=WEEK2)
    assert [(r.service_week_start, r.seq) for r in _rows(world.db, sub)] == [
        (MONDAY, 1), (WEEK2, 1)]


# ---- no live effect --------------------------------------------------------

def test_schr_int_19_the_service_alone_changes_no_demand(world, sub):
    from app.scheduling import service as svc
    before = svc.build_demand(world.db, world.society.id, [MONDAY, WEEK2])
    entitlements.ensure(world.db, sub, through=WEEK3)
    after = svc.build_demand(world.db, world.society.id, [MONDAY, WEEK2])
    assert before == after
    assert world.db.scalar(select(func.count()).select_from(Job)) == 0
