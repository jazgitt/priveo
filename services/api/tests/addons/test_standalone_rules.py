from sqlalchemy import select
from app.addons.models import AddonBooking
from app.billing.models import Payment
from tests.changes.money_fixtures import at


def post(m, vehicle_id, **changes):
    return m.client.post('/v1/customer/addons/standalone', headers={**m.customer, 'Idempotency-Key': 'standalone-once'},
        json={'vehicle_id': vehicle_id, 'date': '2026-10-20', 'finish_by': '12:00', **changes})


def test_standalone_retries_create_one_booking_and_one_payment(money):
    m = money
    vehicle = m.add_vehicle(subscribed=False)
    first, second = post(m, vehicle), post(m, vehicle)
    assert first.status_code == 201 and first.json()['id'] == second.json()['id']
    assert len(m.db.scalars(select(AddonBooking)).all()) == 1
    assert len(m.db.scalars(select(Payment)).all()) == 1
    assert m.client.post(f"/v1/customer/payments/{first.json()['payment_id']}/paid", headers=m.customer).json()['payment']['status'] == 'Initiated'


def test_standalone_rejects_missing_foreign_subscribed_vehicle_and_late_booking(money):
    m = money
    assert post(m, m.vehicle_id).status_code == 409
    assert post(m, '00000000-0000-0000-0000-000000000099').status_code == 404
    vehicle = m.add_vehicle(subscribed=False)
    m.clock.now = at(19, 21, 0)
    assert post(m, vehicle).status_code == 409
    assert m.db.scalar(select(Payment)) is None


def test_standalone_cancel_voids_unpaid_payment_and_respects_cutoff(money):
    m = money
    result = post(m, m.add_vehicle(subscribed=False)).json()
    m.clock.now = at(19, 21, 0)
    assert m.client.delete(f"/v1/customer/addons/{result['id']}", headers=m.customer).status_code == 409
    m.clock.now = at(19, 20, 59)
    assert m.client.delete(f"/v1/customer/addons/{result['id']}", headers=m.customer).json()['status'] == 'Cancelled'
    m.db.expire_all()
    assert m.db.scalar(select(Payment)).voided_at is not None
