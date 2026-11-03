# ruff: noqa: F811
"""The zone is internal to the admin and the crew: the customer never sees it,
neither in the vehicle, the home, the edit reply nor the onboarding review."""
import json
import uuid

from app.customers.models import Customer, Vehicle
from app.directory.models import Zone
from tests.customers_account.test_account import me, store, vehicle_id  # noqa: F401


def test_customer_never_sees_the_zone(client, me, db):
    vid = vehicle_id(client, me)
    vehicle = db.get(Vehicle, uuid.UUID(vid))
    society_id = vehicle.society_id or db.get(Customer, vehicle.customer_id).society_id
    zone = Zone(society_id=society_id, name="Zone 7")
    db.add(zone)
    db.flush()
    vehicle.zone_id = zone.id
    db.commit()

    detail = client.get(f"/v1/customer/vehicles/{vid}", headers=me).json()
    home = client.get("/v1/customer/home", headers=me).json()
    edited = client.patch(f"/v1/customer/vehicles/{vid}", headers=me,
                          json={"parking_number": "Under D25"})
    onboarding = client.get("/v1/customer/onboarding", headers=me).json()

    assert edited.status_code == 200
    assert "zone" not in detail and "zone" not in edited.json()
    assert "zone" not in onboarding["vehicles"][0]
    # The parking is the slot alone.
    assert detail["parking"] == f'{vehicle.parking_basement}-{vehicle.parking_number}'.strip("-")
    for reply in (detail, home, edited.json(), onboarding):
        assert "Zone 7" not in json.dumps(reply)
