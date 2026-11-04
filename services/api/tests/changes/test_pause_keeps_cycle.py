"""A pause, skip or credit does not move the cycle (owner, 4 Nov 2026)."""
from datetime import date

from app.billing.models import Payment
from app.changes.cycle import cycle_window, plan_expires_on, shift_days
from tests.changes.money_fixtures import at


def test_pause_does_not_shift_the_cycle_window_or_the_expiry(money):
    m = money
    sub = m.subscription()
    today = date(2026, 10, 11)
    before = (cycle_window(sub.first_service_date, shift_days(m.db, sub.vehicle_id), today),
              plan_expires_on(m.db, sub, today))
    assert before == ((date(2026, 10, 1), date(2026, 10, 31)), date(2026, 10, 30))
    m.clock.now = at(11, 10)
    r = m.client.post(f"/v1/customer/vehicles/{m.vehicle_id}/pauses",
                      json={"from_date": "2026-10-19", "to_date": "2026-10-25"},
                      headers=m.customer)
    assert r.status_code == 201, r.text
    sub = m.subscription()
    assert shift_days(m.db, sub.vehicle_id) == 0
    assert (cycle_window(sub.first_service_date, shift_days(m.db, sub.vehicle_id), today),
            plan_expires_on(m.db, sub, today)) == before


def test_a_paid_next_cycle_does_not_extend_the_expiry(money):
    m = money
    sub = m.subscription()
    m.db.add(Payment(customer_id=m.customer_id, vehicle_id=sub.vehicle_id, subscription_id=sub.id,
                     kind="Plan", description="Plan", amount_rupees=1299, status="Paid",
                     due_date=date(2026, 11, 29), cycle_start=date(2026, 10, 31),
                     cycle_end=date(2026, 11, 30)))
    m.db.commit()
    assert plan_expires_on(m.db, sub, date(2026, 10, 11)) == date(2026, 10, 30)
