# ruff: noqa: F811
"""The customer sees the vehicle's zone beside the parking, read only."""
import uuid

from app.customers.models import Customer, Vehicle
from app.directory.models import Zone
from tests.customers_account.test_account import me, store, vehicle_id  # noqa: F401


def test_customer_sees_the_zone_with_the_parking(client, me, db):
    vid = vehicle_id(client, me)
    vehicle = db.get(Vehicle, uuid.UUID(vid))
    society_id = vehicle.society_id or db.get(Customer, vehicle.customer_id).society_id
    zone = Zone(society_id=society_id, name="Zone 7")
    db.add(zone)
    db.flush()
    vehicle.zone_id = zone.id
    db.commit()
    detail = client.get(f"/v1/customer/vehicles/{vid}", headers=me).json()
    assert detail["zone"] == "Zone 7" and detail["parking"].startswith("Zone 7 · ")
    home = client.get("/v1/customer/home", headers=me).json()
    assert home["vehicles"][0]["parking"].startswith("Zone 7 · ")
    edited = client.patch(f"/v1/customer/vehicles/{vid}", headers=me,
                          json={"parking_number": "Under D25"})
    assert edited.status_code == 200 and edited.json()["zone"] == "Zone 7"
    onboarding = client.get("/v1/customer/onboarding", headers=me).json()
    assert onboarding["vehicles"][0]["zone"] == "Zone 7"
