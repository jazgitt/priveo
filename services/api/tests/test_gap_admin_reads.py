"""P07: pagination and visible imported records without invented fulfilment."""
from datetime import date

from sqlalchemy import select

from app.customers.models import AddonRequest, Customer, Vehicle
from app.identity.models import Login
from tests.test_api import auth, login


def test_customer_paging_reads_past_the_original_limit(client, db):
    owner = db.scalar(select(Customer))
    for i in range(215):
        person = Login(role="customer", login_id=f"page{i}@example.com", display_name="Same Name")
        db.add(person)
        db.flush()
        db.add(Customer(login_id=person.id, email=person.login_id, first_name="Same", last_name="Name",
                         mobile="9000000000", society_id=owner.society_id))
    db.commit()
    headers = auth(login(client, "admin")["access_token"])
    collected = []
    for offset in range(0, 250, 50):
        result = client.get(f"/v1/admin/customers?q=page&limit=50&offset={offset}", headers=headers)
        assert result.status_code == 200, result.text
        collected.extend(c["id"] for c in result.json())
    assert len(collected) == len(set(collected)) == 215
    assert client.get("/v1/admin/customers?offset=-1", headers=headers).status_code == 422


def test_imported_history_preserves_unknowns_and_is_customer_scoped(client, db):
    owner = db.scalar(select(Customer).where(Customer.email == "customer@priveo.test"))
    vehicle = db.scalar(select(Vehicle).where(Vehicle.customer_id == owner.id))
    db.add_all([
        AddonRequest(customer_id=owner.id, vehicle_id=vehicle.id, service="Deep Spa",
                     service_date=date(2026, 9, 1), payment_status="Received", notes="Original note",
                     source_ref="deepspa:one"),
        AddonRequest(customer_id=owner.id, service="Deep Spa", notes="Date as given: unclear",
                     source_ref="deepspa:two"),
    ])
    person = Login(role="customer", login_id="otherhistory@example.com", display_name="Other")
    db.add(person)
    db.flush()
    other = Customer(login_id=person.id, first_name="Other", last_name="Owner", email=person.login_id,
                     mobile="9999999999", society_id=owner.society_id)
    db.add(other)
    db.flush()
    db.add(AddonRequest(customer_id=other.id, service="Secret service", source_ref="deepspa:other"))
    db.commit()
    headers = auth(login(client, "customer")["access_token"])
    result = client.get("/v1/customer/history/imported", headers=headers)
    assert result.status_code == 200, result.text
    rows = result.json()
    assert len(rows) == 2 and all(r["completion_status"] is None and r["proof"] == [] for r in rows)
    unknown = next(r for r in rows if r["date"] is None)
    assert unknown["vehicle_id"] is None and unknown["payment_status"] is None
    assert "unclear" in unknown["notes"] and "Secret" not in result.text
    admin_detail = client.get(f"/v1/admin/customers/{owner.id}",
                              headers=auth(login(client, "admin")["access_token"])).json()
    assert {r["id"] for r in admin_detail["imported_history"]} == {r["id"] for r in rows}
