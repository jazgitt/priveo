"""P01: API/service rating guards, not merely disabled client controls."""
import uuid

import pytest
from sqlalchemy import select

from app.customers.models import Customer, Vehicle
from app.identity.models import Login
from app.support.models import VisitRating


@pytest.mark.parametrize("visit_id", ["not-a-uuid", str(uuid.UUID(int=99))])
def test_rating_unknown_visit_has_no_side_effects(client, customer, db, visit_id):
    r = client.put(f"/v1/customer/visits/{visit_id}/rating", headers=customer,
                   json={"rating": 5})
    assert r.status_code == 422 and "visit_id" in r.json()["fields"]
    assert not db.scalars(select(VisitRating)).all()


@pytest.mark.parametrize("status", ["Scheduled", "In progress", "Skipped", "Could not complete"])
def test_rating_requires_completed_visit(client, customer, db, rating_visit, status):
    rating_visit.status = status
    db.commit()
    r = client.put(f"/v1/customer/visits/{rating_visit.id}/rating", headers=customer,
                   json={"rating": 5})
    assert r.status_code == 409 and r.json()["code"] == "visit_not_completed"
    assert not db.scalars(select(VisitRating)).all()


def test_rating_foreign_completed_visit_is_rejected(client, customer, db, rating_visit):
    login = Login(role="customer", login_id="other@example.com", display_name="Other")
    db.add(login)
    db.flush()
    original = db.get(Customer, db.get(Vehicle, rating_visit.vehicle_id).customer_id)
    owner = Customer(login_id=login.id, email=login.login_id, first_name="Other", last_name="Owner",
                     mobile="9999999999", society_id=original.society_id)
    db.add(owner)
    db.flush()
    foreign = Vehicle(customer_id=owner.id, model="Other car")
    db.add(foreign)
    db.flush()
    rating_visit.vehicle_id = foreign.id
    db.commit()
    r = client.put(f"/v1/customer/visits/{rating_visit.id}/rating", headers=customer,
                   json={"rating": 4, "comment": "Unauthorized"})
    assert r.status_code == 422 and "visit_id" in r.json()["fields"]
    assert not db.scalars(select(VisitRating)).all()


def test_rating_canonical_id_updates_one_record(client, customer, db, rating_visit):
    for spelling, stars in [(str(rating_visit.id).upper(), 5), (str(rating_visit.id), 4)]:
        r = client.put(f"/v1/customer/visits/{spelling}/rating", headers=customer,
                       json={"rating": stars, "comment": "Updated"})
        assert r.status_code == 200, r.text
    db.expire_all()
    rows = db.scalars(select(VisitRating)).all()
    assert len(rows) == 1 and rows[0].rating == 4


def test_other_roles_cannot_rate(client, crew, admin, rating_visit):
    for headers in (crew, admin):
        r = client.put(f"/v1/customer/visits/{rating_visit.id}/rating", headers=headers,
                       json={"rating": 5})
        assert r.status_code == 403
