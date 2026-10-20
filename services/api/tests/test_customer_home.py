"""The customer's own home (HOME-01, HOME-02, HOME-07) and the review of their
details at first sign-in (ONB-25, ONB-26)."""
import uuid
from datetime import date, time

import pytest
from sqlalchemy import select

from app.customers.models import Customer, Subscription, Vehicle
from app.customers.service import read_cutoff, show_registration
from app.directory.models import Plan, Society
from app.identity.models import Login
from app.identity.service import hash_password
from app.media.models import MediaUpload
from app.platform.db import utcnow
from tests.test_api import auth, login

EMAIL = "asha@example.com"
PASSWORD = "carwash2026"


def add_photo(db, login_id, vehicle_id):
    upload_id = uuid.uuid4()
    db.add(MediaUpload(
        id=upload_id, owner_login_id=login_id, purpose="vehicle", kind="photo",
        content_type="image/jpeg", declared_size_bytes=10, size_bytes=10,
        object_key=f"vehicle/{vehicle_id}/{upload_id}", status="confirmed",
        confirmed_at=utcnow()))


@pytest.fixture
def asha(client, db):
    """A migrated customer: two subscribed cars with gaps, and a third car
    that only had a Deep Spa. She has not reviewed her details yet."""
    row = Login(role="customer", login_id=EMAIL, display_name="Asha",
                password_hash=hash_password(PASSWORD))
    society = Society(name="DLF Meadows")
    db.add_all([row, society])
    db.flush()
    customer = Customer(login_id=row.id, first_name="Asha", last_name="", email=EMAIL,
                        mobile="9xxxxx0101", society_id=society.id, flat="A-101",
                        source="migration")
    db.add(customer)
    db.flush()
    cars = [
        ("master:1", "HR26DK8337", "Hyundai Creta", "B1", "223", 1299, time(6, 30), "Friday"),
        ("master:2", None, "Swift", "", "", 999, None, None),
        ("deepspa-vehicle:1", "DL3CAB1234", "Tata Punch", "B2", "", None, None, None),
    ]
    for ref, registration, model, basement, number, price, cutoff, day in cars:
        vehicle = Vehicle(customer_id=customer.id, registration=registration, model=model,
                          parking_basement=basement, parking_number=number, source_ref=ref)
        db.add(vehicle)
        db.flush()
        # ONB-22: every vehicle already has its photo.
        add_photo(db, row.id, vehicle.id)
        if price:
            db.add(Subscription(vehicle_id=vehicle.id, monthly_price_rupees=price,
                                first_service_date=date(2026, 9, 14), cutoff_time=cutoff,
                                interior_day=day))
    db.commit()
    r = client.post("/v1/auth/login", json={"login_id": EMAIL, "password": PASSWORD})
    return auth(r.json()["access_token"])


def answers(client, headers, **changes):
    """What the app sends back: the details as given, with the gaps filled."""
    o = client.get("/v1/customer/onboarding", headers=headers).json()
    body = {
        "first_name": o["first_name"], "last_name": "Rao", "mobile": o["mobile"],
        "vehicles": [{
            "id": v["id"],
            "parking_basement": v["parking_basement"] or "B2",
            "parking_number": v["parking_number"] or "41",
            "cutoff_time": v["cutoff_time"] or ("07:30" if v["has_subscription"] else None),
            "interior_day": v["interior_day"],
        } for v in o["vehicles"]],
    }
    body.update(changes)
    return body


def confirm(client, headers, body):
    return client.post("/v1/customer/onboarding/confirm", headers=headers, json=body)


def test_helpers():
    assert show_registration("HR26DK8337") == "HR 26 DK 8337"
    assert show_registration("DL3CAB1234") == "DL 3 CAB 1234"
    assert show_registration("ODD-ONE") == "ODD-ONE"
    assert show_registration(None) == ""
    assert read_cutoff("06:30") == time(6, 30) and read_cutoff("23:00") == time(23, 0)
    for bad in ("6:30", "06:15", "24:00", "", None, "soon"):
        assert read_cutoff(bad) is None


def test_review_draft_restores_position_and_edits_without_confirmation_or_payment(client, asha, db):
    from app.billing.models import Payment

    before = len(db.scalars(select(Payment)).all())
    r = client.patch("/v1/customer/onboarding/draft", headers=asha, json={
        "step": 1, "first_name": "Asha", "last_name": "Rao", "mobile": "9876543210"})
    assert r.status_code == 204, r.text
    read = client.get("/v1/customer/onboarding", headers=asha).json()
    assert (read["step"], read["last_name"], read["mobile"], read["confirmed"]) == (
        1, "Rao", "9876543210", False)
    vid = read["vehicles"][0]["id"]
    body = {"step": 4, "vehicles": [{"id": vid, "parking_basement": "B3", "parking_number": "99"}]}
    for _ in range(2):
        assert client.patch("/v1/customer/onboarding/draft", headers=asha, json=body).status_code == 204
    restored = client.get("/v1/customer/onboarding", headers=asha).json()
    assert restored["step"] == 4 and restored["vehicles"][0]["parking_number"] == "99"
    assert not client.get("/v1/customer/home", headers=asha).json()["onboarding_confirmed"]
    db.expire_all()
    assert len(db.scalars(select(Payment)).all()) == before


@pytest.mark.parametrize("body", [{"step": 1, "email": "other@example.com"},
                                 {"step": 4, "vehicles": [{"id": "foreign", "parking_number": "9"}]},
                                 {"step": 99}, {"step": -1},
                                 {"step": 4, "vehicles": [{"id": "foreign", "plan_id": "x"}]}])
def test_review_draft_rejects_read_only_foreign_and_invalid_position(client, asha, body):
    before = client.get("/v1/customer/onboarding", headers=asha).json()
    assert client.patch("/v1/customer/onboarding/draft", headers=asha, json=body).status_code == 422
    assert client.get("/v1/customer/onboarding", headers=asha).json() == before


def test_home_vehicle_fields_and_rate_action_match_requirements(client, asha, db):
    person = db.scalar(select(Customer).where(Customer.email == EMAIL))
    vehicle = db.scalar(select(Vehicle).where(Vehicle.customer_id == person.id))
    vehicle.make, vehicle.model, vehicle.variant = "Hyundai", "Creta", "SX"
    db.commit()
    home = client.get("/v1/customer/home", headers=asha).json()
    car = next(v for v in home["vehicles"] if v["id"] == str(vehicle.id))
    assert (car["make"], car["model"], car["variant"]) == ("Hyundai", "Creta", "SX")
    assert "rate_today" in {a["key"] for a in home["quick_actions"]}
    assert "feedback" not in {a["key"] for a in home["quick_actions"]}


def test_confirmed_review_cannot_be_changed_by_draft_endpoint(client, asha):
    assert confirm(client, asha, answers(client, asha)).status_code == 204
    result = client.patch("/v1/customer/onboarding/draft", headers=asha,
                          json={"step": 0, "first_name": "Changed"})
    assert result.status_code == 409 and result.json()["code"] == "already_confirmed"


def test_home_shows_the_customers_own_vehicles(client, asha):
    home = client.get("/v1/customer/home", headers=asha).json()
    assert home["greeting_name"] == "Asha" and home["onboarding_confirmed"] is False
    assert [a["key"] for a in home["quick_actions"]] == [
        "skip_pause", "history", "rate_today", "report_issue"]

    creta, swift, punch = home["vehicles"]
    assert creta == {
        "id": creta["id"], "registration": "HR 26 DK 8337", "model": "Hyundai Creta",
        "society": "DLF Meadows", "parking": "B1-223", "subscription_status": "Active",
        "monthly_price_rupees": 1299, "cutoff_time": "06:30", "interior_day": "Friday",
        "plan_name": None, "expires_on": creta["expires_on"], "next_service": None, "make": "", "variant": "",
        "photo_url": creta["photo_url"],
    }
    assert creta["photo_url"].startswith("/v1/media/local/")
    assert (swift["registration"], swift["parking"], swift["cutoff_time"]) == ("", "", None)
    # The car with no subscription comes last and has no plan details (ADD-14).
    assert (punch["model"], punch["parking"], punch["subscription_status"],
            punch["monthly_price_rupees"]) == ("Tata Punch", "B2", None, None)


def test_home_shows_the_plan_name_of_each_subscription(client, db, asha):
    plan = Plan(name="Daily Premium", monthly_price_rupees=1299)
    db.add(plan)
    db.flush()
    vehicle = db.scalar(select(Vehicle).where(Vehicle.source_ref == "master:1"))
    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == vehicle.id))
    sub.plan_id = plan.id
    db.commit()
    creta, swift, punch = client.get("/v1/customer/home", headers=asha).json()["vehicles"]
    assert creta["plan_name"] == "Daily Premium"
    assert swift["plan_name"] is None and punch["plan_name"] is None


def test_a_customer_sees_only_their_own_record(client, asha):
    demo = client.get("/v1/customer/home",
                      headers=auth(login(client, "customer")["access_token"])).json()
    assert demo["greeting_name"] == "Aarav" and demo["onboarding_confirmed"] is True
    assert [v["model"] for v in demo["vehicles"]] == ["Hyundai Creta", "Maruti Swift"]
    assert all(v["society"] == "Priveo Demo Society" for v in demo["vehicles"])
    mine = client.get("/v1/customer/home", headers=asha).json()
    assert not {v["id"] for v in demo["vehicles"]} & {v["id"] for v in mine["vehicles"]}


def test_crew_and_admin_cannot_read_customer_screens(client):
    for role in ("crew", "admin"):
        headers = auth(login(client, role)["access_token"])
        for path in ("/v1/customer/home", "/v1/customer/onboarding"):
            assert client.get(path, headers=headers).status_code == 403
    assert client.get("/v1/customer/onboarding").status_code == 401


def test_a_customer_login_with_no_record_is_told_so(client, db):
    db.add(Login(role="customer", login_id="bare@example.com", display_name="Bare",
                 password_hash=hash_password(PASSWORD)))
    db.commit()
    r = client.post("/v1/auth/login", json={"login_id": "bare@example.com",
                                            "password": PASSWORD})
    r = client.get("/v1/customer/home", headers=auth(r.json()["access_token"]))
    assert r.status_code == 404 and r.json()["code"] == "no_customer_record"


def test_the_review_shows_what_the_admin_entered(client, asha):
    o = client.get("/v1/customer/onboarding", headers=asha).json()
    assert (o["confirmed"], o["first_name"], o["last_name"], o["email"], o["mobile"],
            o["society"], o["flat"]) == (
        False, "Asha", "", EMAIL, "9xxxxx0101", "DLF Meadows", "A-101")
    creta, swift, punch = o["vehicles"]
    assert (creta["has_subscription"], creta["asks_interior_day"], creta["interior_day"],
            creta["monthly_price_rupees"], creta["plan_name"]) == (
        True, True, "Friday", 1299, None)
    # No interior day came with the Swift, so the day is not asked for it.
    assert (swift["asks_interior_day"], swift["cutoff_time"]) == (False, None)
    assert (punch["has_subscription"], punch["asks_interior_day"],
            punch["monthly_price_rupees"]) == (False, False, None)


def test_confirming_saves_the_changes_and_opens_home(client, db, asha):
    body = answers(client, asha, first_name="  Asha ", mobile="9000000777")
    body["vehicles"][0].update(parking_number="301", cutoff_time="07:00",
                               interior_day="sunday")
    assert confirm(client, asha, body).status_code == 204

    customer = db.scalar(select(Customer).where(Customer.email == EMAIL))
    assert (customer.first_name, customer.last_name, customer.mobile) == (
        "Asha", "Rao", "9000000777")
    assert customer.onboarding_confirmed_at is not None
    assert db.get(Login, customer.login_id).display_name == "Asha Rao"

    home = client.get("/v1/customer/home", headers=asha).json()
    assert home["onboarding_confirmed"] is True
    creta, swift, punch = home["vehicles"]
    assert (creta["parking"], creta["cutoff_time"], creta["interior_day"]) == (
        "B1-301", "07:00", "Sunday")
    assert (swift["parking"], swift["cutoff_time"], swift["interior_day"]) == (
        "B2-41", "07:30", None)
    assert punch["parking"] == "B2-41"
    # What only Priveo can change stays as it was (ONB-26).
    assert (creta["registration"], creta["monthly_price_rupees"]) == ("HR 26 DK 8337", 1299)

    assert confirm(client, asha, body).json()["code"] == "already_confirmed"


def test_the_gaps_must_be_filled_before_confirming(client, db, asha):
    o = client.get("/v1/customer/onboarding", headers=asha).json()
    body = {"first_name": "Asha", "last_name": "", "mobile": "12345",
            "vehicles": [{"id": v["id"], "parking_basement": v["parking_basement"],
                          "parking_number": v["parking_number"],
                          "cutoff_time": v["cutoff_time"], "interior_day": None}
                         for v in o["vehicles"]]}
    r = confirm(client, asha, body)
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
    assert set(r.json()["fields"]) == {
        "last_name", "mobile", "vehicles.0.interior_day", "vehicles.1.parking_basement",
        "vehicles.1.parking_number", "vehicles.1.cutoff_time", "vehicles.2.parking_number"}
    assert r.json()["fields"]["vehicles.1.cutoff_time"] == (
        "Please select your service cutoff time.")
    assert db.scalar(select(Customer).where(Customer.email == EMAIL)
                     ).onboarding_confirmed_at is None


def test_the_masked_number_on_file_is_accepted_as_it_is(client, asha):
    assert confirm(client, asha, answers(client, asha)).status_code == 204


@pytest.mark.parametrize("change", [
    lambda b: b["vehicles"].pop(),
    lambda b: b["vehicles"].append(dict(b["vehicles"][0])),
    lambda b: b["vehicles"][0].update(id="not-mine"),
])
def test_every_vehicle_must_be_reviewed_and_no_other(client, asha, change):
    body = answers(client, asha)
    change(body)
    r = confirm(client, asha, body)
    assert r.status_code == 422 and "vehicles" in r.json()["fields"]


def test_one_customer_cannot_confirm_with_anothers_vehicle(client, asha):
    demo = auth(login(client, "customer")["access_token"])
    theirs = client.get("/v1/customer/home", headers=demo).json()["vehicles"][0]["id"]
    body = answers(client, asha)
    body["vehicles"][0]["id"] = theirs
    assert confirm(client, asha, body).status_code == 422
