"""A migrated visit (from the owner's calendar sheet) is history, not a visit the
customer experienced in the app, so it cannot be rated (owner decision, 8 Nov 2026)."""
from datetime import date

from sqlalchemy import select

from app.customers.history_convert import admin_login_id, write_record
from app.customers.models import Customer, Vehicle
from app.scheduling.models import Visit


def test_a_migrated_visit_cannot_be_rated(client, customer, db):
    owner = db.scalar(select(Customer).where(Customer.email == "customer@priveo.test"))
    vehicle = db.scalar(select(Vehicle).where(Vehicle.customer_id == owner.id))
    write_record(db, vehicle, date(2026, 10, 1), services="Exterior + Interior",
                 outcome="Completed", skip_reason="", admin_id=admin_login_id(db))
    db.commit()
    visit = db.scalar(select(Visit).where(Visit.vehicle_id == vehicle.id, Visit.date == date(2026, 10, 1)))
    assert visit.status == "Completed"
    r = client.put(f"/v1/customer/visits/{visit.id}/rating", headers=customer,
                   json={"rating": 5, "tags": []})
    assert r.status_code == 409 and r.json()["code"] == "visit_not_rateable"
