"""Calendar, next service, visit details with proof, history and vehicles."""
from datetime import date, datetime

from app.customer_reads.repository import Visit
from app.customer_reads.service import CustomerReads
from app.platform.clock import IST
from tests.customer_reads.conftest import add_customer


def test_calendar_month_lists_visits_with_their_services(api, asha):
    r = api.get("/v1/customer/calendar?month=2026-11", headers=asha["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["month"] == "2026-11"
    # The days with no planned visit are projected from the subscription.
    planned = [v for v in body["visits"] if v["source"] == "visit"]
    assert [v["visit_id"] for v in planned] == ["v-1", "v-2", "v-3", "v-4"]
    assert planned[0]["services"] == ["Cleaning-External", "Cleaning-Internal"]
    assert planned[1]["status"] == "Skipped"


def test_calendar_can_be_limited_to_one_vehicle(api, asha):
    first = asha["vehicles"][0]
    r = api.get(f"/v1/customer/calendar?month=2026-11&vehicle_id={first}",
                headers=asha["headers"])
    assert {v["vehicle_id"] for v in r.json()["visits"]} == {first}


def test_calendar_refuses_someone_elses_vehicle_and_a_bad_month(api, asha, db):
    other = add_customer(db, "other@example.com", [("MH12AB0001", "Alto", True)])[0]
    r = api.get(f"/v1/customer/calendar?month=2026-11&vehicle_id={other}",
                headers=asha["headers"])
    assert r.status_code == 404
    assert api.get("/v1/customer/calendar?month=2026-13",
                   headers=asha["headers"]).status_code == 422
    assert api.get("/v1/customer/calendar?month=nov",
                   headers=asha["headers"]).status_code == 422


def test_visit_detail_carries_the_proof_media(api, asha):
    r = api.get("/v1/customer/visits/v-1", headers=asha["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "Completed"
    assert body["vehicle_registration"] == "HR 26 DK 8337"
    assert [j["service"] for j in body["jobs"]] == ["Cleaning-External", "Cleaning-Internal"]
    assert body["jobs"][0]["proof"][0] == {"kind": "photo", "url": "https://media.test/a.jpg"}
    assert body["jobs"][0]["proof"][2]["kind"] == "video"
    # No crew name or customer detail is in the response.
    assert "crew" not in r.text


def test_visit_of_another_customer_is_not_found(api, asha, db, repo):
    other = add_customer(db, "other@example.com", [("MH12AB0001", "Alto", True)])[0]
    repo.visit_rows.append(Visit("v-x", other, date(2026, 11, 2), "Completed"))
    assert api.get("/v1/customer/visits/v-x", headers=asha["headers"]).status_code == 404
    assert api.get("/v1/customer/visits/nope", headers=asha["headers"]).status_code == 404


def test_history_is_newest_first_and_only_visits_that_are_over(api, asha):
    r = api.get("/v1/customer/history", headers=asha["headers"])
    items = r.json()
    assert [i["visit_id"] for i in items] == ["v-2", "v-1"]
    assert items[1]["photo_count"] == 3
    assert items[1]["services"] == ["Cleaning-External", "Cleaning-Internal"]
    page = api.get("/v1/customer/history?limit=1&offset=1", headers=asha["headers"]).json()
    assert [i["visit_id"] for i in page] == ["v-1"]


def test_next_service_is_the_first_visit_not_over_for_each_vehicle(db, asha, repo):
    from app.customers.models import Customer

    login = db.query(Customer).filter_by(email="asha@example.com").one().login_id
    reads = CustomerReads(db, repo, lambda: datetime(2026, 11, 20, 10, 0, tzinfo=IST))
    items = reads.next_services(login, date(2026, 11, 20))
    assert [(i.vehicle_id, i.visit_id, i.service) for i in items] == [
        (asha["vehicles"][0], "v-3", "Cleaning-External"),
        (asha["vehicles"][1], "v-4", ""),
    ]
    # Visits that are over are not next: the subscription's next day takes over.
    later = CustomerReads(db, repo, lambda: datetime(2026, 12, 2, 10, 0, tzinfo=IST))
    assert [i.source for i in later.next_services(login, date(2026, 12, 2))] == [
        "projected", "projected"]


def test_next_service_endpoint(api, asha):
    assert api.get("/v1/customer/next-service", headers=asha["headers"]).status_code == 200


def test_vehicles_list_and_detail(api, asha):
    r = api.get("/v1/customer/vehicles", headers=asha["headers"])
    assert [v["registration"] for v in r.json()] == ["HR 26 DK 8337", "DL 3 CAB 1234"]
    assert r.json()[0]["subscription_status"] == "Active"
    first = asha["vehicles"][0]
    d = api.get(f"/v1/customer/vehicles/{first}", headers=asha["headers"]).json()
    assert d["parking"] == "B2-14" and d["monthly_price_rupees"] == 1299
    assert d["cutoff_time"] == "07:00" and d["variant"] == "SX"
    assert api.get("/v1/customer/vehicles/nope", headers=asha["headers"]).status_code == 404


def test_reads_need_a_customer_sign_in(api, asha):
    assert api.get("/v1/customer/vehicles").status_code == 401
