"""S-11 / ADM-SUB-08: a plan change from a date the admin chooses, and the plan history."""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.billing.config import MoneySettings
from app.billing.service import BillingService
from app.changes.payment_dates import shift_unpaid_renewals
from app.customers.models import PlanChange, Subscription
from app.directory.models import Plan
from app.platform.clock import today_ist
from tests import test_customer_administration as base
from tests.test_api import auth, login

# The directory fixture (a society, a plan and a car) is shared with those tests.
directory = base.directory
create = base.create


def world(client, directory, db):
    admin = auth(login(client, "admin")["access_token"])
    c, _ = create(client, directory, admin)
    sub = db.get(Subscription, uuid.UUID(c["vehicles"][0]["subscription"]["id"]))
    exterior = Plan(name="Exterior test", monthly_price_rupees=699, includes_interior=False)
    db.add(exterior)
    db.commit()
    return admin, sub, exterior


def patch(client, admin, sub, **body):
    return client.patch(f"/v1/admin/subscriptions/{sub.id}", headers=admin, json=body)


def history(client, admin, sub):
    r = client.get(f"/v1/admin/subscriptions/{sub.id}/plan-history", headers=admin)
    assert r.status_code == 200, r.text
    return r.json()


def test_a_chosen_date_sets_the_start_and_is_kept_in_the_history(client, directory, db):
    admin, sub, exterior = world(client, directory, db)
    start = today_ist() + timedelta(days=5)
    r = patch(client, admin, sub, plan_id=str(exterior.id), effective_from=start.isoformat())
    assert r.status_code == 200, r.text
    assert r.json()["pending_from"] == start.isoformat()
    db.refresh(sub)
    assert sub.pending_plan_id == exterior.id and sub.pending_from == start
    assert sub.monthly_price_rupees == 999  # no change before the date

    listing = history(client, admin, sub)
    assert listing["current_price_rupees"] == 999
    (row,) = listing["changes"]
    assert (row["to_plan"], row["to_price_rupees"], row["from_price_rupees"]) == ("Exterior test", 699, 999)
    assert row["effective_from"] == start.isoformat() and row["chosen"] and row["status"] == "Scheduled"

    # The daily job moves the subscription onto the plan on that day, with no earlier effect.
    day = datetime.combine(start - timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    BillingService(db, lambda: day, MoneySettings()).generate_due_payments(day)
    db.refresh(sub)
    assert sub.plan_id != exterior.id and sub.pending_plan_id == exterior.id
    day = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
    BillingService(db, lambda: day, MoneySettings()).generate_due_payments(day)
    db.refresh(sub)
    assert sub.plan_id == exterior.id and sub.monthly_price_rupees == 699 and sub.pending_plan_id is None
    (row,) = history(client, admin, sub)["changes"]
    assert row["status"] == "Applied"
    assert history(client, admin, sub)["current_plan"] == "Exterior test"


def test_without_a_date_the_change_starts_at_the_next_renewal_as_before(client, directory, db):
    admin, sub, exterior = world(client, directory, db)
    assert patch(client, admin, sub, plan_id=str(exterior.id)).status_code == 200
    db.refresh(sub)
    (row,) = history(client, admin, sub)["changes"]
    assert not row["chosen"] and row["effective_from"] == sub.pending_from.isoformat()
    assert sub.pending_from >= today_ist() + timedelta(days=1)


def test_a_new_change_replaces_the_scheduled_one_and_cancel_keeps_history(client, directory, db):
    admin, sub, exterior = world(client, directory, db)
    other = Plan(name="Other test", monthly_price_rupees=799, includes_interior=False)
    db.add(other)
    db.commit()
    first = (today_ist() + timedelta(days=3)).isoformat()
    second = (today_ist() + timedelta(days=9)).isoformat()
    patch(client, admin, sub, plan_id=str(exterior.id), effective_from=first)
    patch(client, admin, sub, plan_id=str(other.id), effective_from=second)
    states = {c["to_plan"]: c["status"] for c in history(client, admin, sub)["changes"]}
    assert states == {"Exterior test": "Cancelled", "Other test": "Scheduled"}
    db.refresh(sub)
    assert sub.pending_plan_id == other.id and sub.pending_from.isoformat() == second

    url = f"/v1/admin/subscriptions/{sub.id}/plan-change"
    assert client.delete(url, headers=admin).status_code == 204
    db.refresh(sub)
    assert sub.pending_plan_id is None and sub.pending_from is None
    states = {c["to_plan"]: c["status"] for c in history(client, admin, sub)["changes"]}
    assert states == {"Exterior test": "Cancelled", "Other test": "Cancelled"}
    assert client.delete(url, headers=admin).status_code == 404  # nothing scheduled now


def test_bad_dates_and_inputs_are_refused(client, directory, db):
    admin, sub, exterior = world(client, directory, db)
    yesterday = (today_ist() - timedelta(days=1)).isoformat()
    assert patch(client, admin, sub, plan_id=str(exterior.id), effective_from=yesterday).status_code == 422
    assert patch(client, admin, sub, effective_from=today_ist().isoformat()).status_code == 422
    assert patch(client, admin, sub, plan_id=str(uuid.uuid4()),
                 effective_from=today_ist().isoformat()).status_code == 422
    # today is allowed
    assert patch(client, admin, sub, plan_id=str(exterior.id),
                 effective_from=today_ist().isoformat()).status_code == 200
    db.refresh(sub)
    assert sub.pending_from == today_ist()


def test_a_pause_moves_a_renewal_based_change_but_not_a_chosen_date(client, directory, db):
    admin, sub, exterior = world(client, directory, db)
    start = today_ist() + timedelta(days=10)
    patch(client, admin, sub, plan_id=str(exterior.id), effective_from=start.isoformat())
    shift_unpaid_renewals(db, sub, today_ist(), 3)
    db.commit()
    db.refresh(sub)
    assert sub.pending_from == start  # chosen: stays
    # Replace it with a renewal-based change and shift again.
    patch(client, admin, sub, plan_id=str(exterior.id))
    db.refresh(sub)
    before = sub.pending_from
    shift_unpaid_renewals(db, sub, today_ist(), 3)
    db.commit()
    db.refresh(sub)
    assert sub.pending_from == before + timedelta(days=3)
    scheduled = db.scalar(select(PlanChange).where(
        PlanChange.subscription_id == sub.id, PlanChange.status == "Scheduled"))
    assert scheduled.effective_from == sub.pending_from  # the history follows


def test_only_the_admin_reads_the_history_and_unknown_ids_are_404(client, directory, db):
    admin, sub, _ = world(client, directory, db)
    assert history(client, admin, sub)["changes"] == []
    ghost = uuid.uuid4()
    assert client.get(f"/v1/admin/subscriptions/{ghost}/plan-history", headers=admin).status_code == 404
    assert client.delete(f"/v1/admin/subscriptions/{ghost}/plan-change", headers=admin).status_code == 404
    assert client.get(f"/v1/admin/subscriptions/{sub.id}/plan-history").status_code == 401
    customer = auth(login(client, "customer")["access_token"])
    assert client.get(f"/v1/admin/subscriptions/{sub.id}/plan-history", headers=customer).status_code == 403


def quote(client, admin, sub, plan, start):
    r = client.get(f"/v1/admin/subscriptions/{sub.id}/plan-change-quote", headers=admin,
                   params={"plan_id": str(plan.id), "effective_from": start.isoformat()})
    assert r.status_code == 200, r.text
    return r.json()


def adjustments(db, sub):
    from app.billing.models import Payment
    return list(db.scalars(select(Payment).where(Payment.subscription_id == sub.id,
                                                 Payment.kind == "Adjust")))


def test_the_admin_decides_the_charge_for_the_days_before_the_renewal(client, directory, db):
    admin, sub, _ = world(client, directory, db)
    premium = Plan(name="Upgrade charge test", monthly_price_rupees=1499, includes_interior=True)
    db.add(premium)
    db.commit()
    start = today_ist() + timedelta(days=3)
    q = quote(client, admin, sub, premium, start)
    assert q["days"] > 0 and q["price_difference_rupees"] == 500
    assert q["suggested_rupees"] == round(500 * q["days"] / 30)

    # No charge is the default.
    assert patch(client, admin, sub, plan_id=str(premium.id), effective_from=start.isoformat()).status_code == 200
    assert adjustments(db, sub) == []

    # The prorated difference becomes one payment, kept with the change.
    r = patch(client, admin, sub, plan_id=str(premium.id), effective_from=start.isoformat(), charge="prorated")
    assert r.status_code == 200, r.text
    (pay,) = adjustments(db, sub)
    assert (pay.amount_rupees, pay.status, pay.due_date) == (q["suggested_rupees"], "Due", start)
    assert history(client, admin, sub)["changes"][0]["charge_rupees"] == q["suggested_rupees"]

    # Choosing again replaces the change and its unpaid charge with a custom amount.
    r = patch(client, admin, sub, plan_id=str(premium.id), effective_from=start.isoformat(),
              charge="custom", charge_rupees=250)
    assert r.status_code == 200, r.text
    db.expire_all()
    live = [p for p in adjustments(db, sub) if p.voided_at is None]
    assert [p.amount_rupees for p in live] == [250] and len(adjustments(db, sub)) == 2

    # Cancelling the change voids what was not paid.
    assert client.delete(f"/v1/admin/subscriptions/{sub.id}/plan-change", headers=admin).status_code == 204
    db.expire_all()
    assert all(p.voided_at is not None for p in adjustments(db, sub))


def test_a_charge_needs_a_date_before_the_renewal_and_a_real_amount(client, directory, db):
    admin, sub, exterior = world(client, directory, db)
    start = today_ist() + timedelta(days=3)
    # A downgrade has no difference to prorate.
    r = patch(client, admin, sub, plan_id=str(exterior.id), effective_from=start.isoformat(), charge="prorated")
    assert r.status_code == 422
    # A custom charge needs an amount.
    r = patch(client, admin, sub, plan_id=str(exterior.id), effective_from=start.isoformat(), charge="custom")
    assert r.status_code == 422
    # A charge without a date has no days to charge for.
    r = patch(client, admin, sub, plan_id=str(exterior.id), charge="custom", charge_rupees=100)
    assert r.status_code == 422
    # At the renewal itself there are no days in between.
    renewal = quote(client, admin, sub, exterior, start)["renewal_date"]
    r = patch(client, admin, sub, plan_id=str(exterior.id), effective_from=renewal, charge="custom", charge_rupees=100)
    assert r.status_code == 422
    assert adjustments(db, sub) == []
