"""The customer load, tested with a made-up workbook. No real customer data."""
from datetime import date, datetime, time

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select

from app.customers.importer import (
    PLACEHOLDER_SOCIETY,
    addon_date_of,
    import_workbook,
    mobile_of,
    parking_of,
    registration_of,
    split_name,
)
from app.customers.models import AddonRequest, Customer, Subscription, Vehicle
from app.directory.models import Society
from app.identity.models import Login

MASTER = ["Sl. No.", "Customer Name", "Phone Number", "Car Model", "Car Number", "Flat No.",
          "Parking Number", "Customer cutoff time", "Start Date", "Interior Preferred day",
          "Subscription Price (INR)", "Email"]
ADDONS = ["Sl. No.", "Customer Name", "Phone Number", "Car Model", "Car Number", "Flat No.",
          "Parking Number", "Package", "Date", "Status", "Notes", "Email"]


def _workbook(tmp_path, master, addons=()):
    wb = Workbook()
    ws = wb.active
    ws.title = "Customer Master"
    ws.append(MASTER)
    for row in master:
        ws.append(row)
    ws2 = wb.create_sheet("Deep Spa Addons")
    ws2.append(ADDONS)
    for row in addons:
        ws2.append(row)
    path = tmp_path / "customers.xlsx"
    wb.save(path)
    return path


# Excel dates carry no timezone.
START = datetime(2026, 9, 14)  # noqa: DTZ001
ASHA = "asha@example.com"
ROWS = [
    [1, "Asha Rao", 9000000101, "Hyundai Creta", "DL 13 CM 0019", "A-101", "B1-223",
     time(6, 30), START, "Friday", 1299, ASHA],
    [2, "Asha Rao", 9000000101, "Swift", "", "A-101", "B1 near pillar 4",
     None, START, None, 999, "ASHA@example.com "],
    [3, "Vikram", 9000000102, "Nexon", "7577", "D-2 14", "B2-9",
     time(7, 0), datetime(2026, 10, 1), "Sunday", 1299,  # noqa: DTZ001
     "vikram@example.com"],
]
ADDON_ROWS = [
    [1, "Asha Rao", 9000000101, "Creta", "DL13CM 0019", "A-101", "B1-223",
     "Deep Spa (799/-)", "4th Oct", "Paid", "Deep Spa done on 4th Oct", ASHA],
    [2, "Vikram", "9000000102/9000000103", "Nexon", 7577, "D-2 14", "B2-9",
     "Deep Spa (699/-)", "7th Oct 5:30 PM", None, "", "vikram@example.com"],
    [3, "Nobody", 9000000199, "Punch", "", "", "", "Deep Spa (699/-)", "5th Oct", "Pending",
     "", "nobody@example.com"],
]


def _count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_helpers():
    assert split_name("Asha Rao") == ("Asha", "Rao")
    assert split_name("Asha Devi Rao") == ("Asha Devi", "Rao")
    assert split_name("Vikram") == ("Vikram", "")
    assert mobile_of(9000000101.0) == "9000000101"
    assert mobile_of("+91 90000 00101") == "9000000101"
    assert mobile_of("9000000102/9000000103") == "9000000102"
    assert mobile_of(12345) is None
    assert mobile_of("9xxxxx0101") == "9xxxxx0101"  # masked
    assert registration_of("dl 13 cm 0019") == "DL13CM0019"
    assert registration_of("22 BH 1234 A") == "22BH1234A"
    assert registration_of("7577") is None
    assert parking_of("B1-223") == ("B1", "223", True)
    assert parking_of("B1 near pillar 4") == ("B1", "", False)
    assert parking_of("Under D4") == ("", "", False)
    assert addon_date_of("4th Oct", 2026) == date(2026, 10, 4)
    assert addon_date_of("7th Oct 5:30 PM", 2026) == date(2026, 10, 7)
    assert addon_date_of("soon", 2026) is None


def test_a_trial_run_saves_nothing(db, tmp_path):
    report = import_workbook(db, _workbook(tmp_path, ROWS, ADDON_ROWS), apply=False)
    assert (report.customers_created, report.vehicles_created) == (2, 3)
    assert _count(db, Customer) == 0 and _count(db, Login) == 0 and _count(db, Society) == 0


def test_the_load(db, tmp_path):
    report = import_workbook(db, _workbook(tmp_path, ROWS, ADDON_ROWS), apply=True)
    assert (report.customers_created, report.vehicles_created, report.addons_created) == (2, 3, 2)

    # Two rows with one email, in any letter case, are one customer.
    asha = db.scalar(select(Customer).where(Customer.email == ASHA))
    assert (asha.first_name, asha.last_name, asha.mobile, asha.flat) == (
        "Asha", "Rao", "9000000101", "A-101")
    assert asha.source == "migration"
    assert db.get(Society, asha.society_id).name == PLACEHOLDER_SOCIETY

    # The login exists but has no password until the first sign-in.
    login = db.get(Login, asha.login_id)
    assert (login.role, login.login_id, login.password_hash) == ("customer", ASHA, None)

    cars = {v.source_ref: v for v in db.scalars(select(Vehicle))}
    assert cars["master:1"].registration == "DL13CM0019"
    assert (cars["master:1"].parking_basement, cars["master:1"].parking_number) == ("B1", "223")
    assert cars["master:2"].registration is None
    assert "Parking as given: B1 near pillar 4" in cars["master:2"].notes
    assert cars["master:3"].registration is None
    assert "Car number as given: 7577" in cars["master:3"].notes

    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == cars["master:1"].id))
    assert (sub.monthly_price_rupees, sub.first_service_date, sub.cutoff_time,
            sub.interior_day, sub.status, sub.plan_id) == (
        1299, date(2026, 9, 14), time(6, 30), "Friday", "Active", None)
    sub2 = db.scalar(select(Subscription).where(Subscription.vehicle_id == cars["master:2"].id))
    assert (sub2.monthly_price_rupees, sub2.cutoff_time, sub2.interior_day) == (999, None, None)

    addons = {a.source_ref: a for a in db.scalars(select(AddonRequest))}
    first = addons["deepspa:1"]
    assert (first.service, first.price_rupees, first.service_date, first.payment_status) == (
        "Deep Spa", 799, date(2026, 10, 4), "Received")
    assert first.vehicle_id == cars["master:1"].id  # matched by car number
    second = addons["deepspa:2"]
    assert second.vehicle_id == cars["master:3"].id  # matched by a partial number
    assert second.payment_status is None and "7th Oct 5:30 PM" in second.notes


def test_the_report_flags_gaps_without_personal_details(db, tmp_path):
    report = import_workbook(db, _workbook(tmp_path, ROWS, ADDON_ROWS), apply=True)
    text = "\n".join(report.warnings + report.errors)
    assert "Customer Master row 2: the car number is missing or incomplete" in text
    assert "Customer Master row 2: no cutoff time" in text
    assert "Customer Master row 3: the name is one word" in text
    assert "Deep Spa Addons row 2: no payment status" in text
    assert report.errors == [
        "Deep Spa Addons row 3: no customer with this email in the Customer Master sheet"]
    for secret in ("Asha", "Vikram", "9000000101", "example.com", "DL13", "7577"):
        assert secret not in text


def test_running_it_again_adds_nothing(db, tmp_path):
    path = _workbook(tmp_path, ROWS, ADDON_ROWS)
    import_workbook(db, path, apply=True)
    again = import_workbook(db, path, apply=True)
    assert (again.customers_created, again.vehicles_created, again.addons_created) == (0, 0, 0)
    assert (again.customers_kept, again.vehicles_kept, again.addons_kept) == (2, 3, 2)
    assert (_count(db, Customer), _count(db, Vehicle), _count(db, Subscription),
            _count(db, AddonRequest)) == (2, 3, 3, 2)


@pytest.mark.parametrize("change, message", [
    ({11: "not-an-email"}, "the email is missing or not valid"),
    ({8: None}, "the start date, the price or the car model is missing"),
    ({2: 123}, "the name or the 10-digit phone number is missing"),
])
def test_a_bad_row_is_skipped_and_reported(db, tmp_path, change, message):
    row = list(ROWS[0])
    for index, value in change.items():
        row[index] = value
    report = import_workbook(db, _workbook(tmp_path, [row]), apply=True)
    assert report.errors == [f"Customer Master row 1: {message}"]
    assert _count(db, Customer) == 0 and _count(db, Vehicle) == 0


def test_a_migrated_customer_cannot_sign_in_before_setting_a_password(client, engine, tmp_path):
    from sqlalchemy.orm import Session
    with Session(engine) as session:
        import_workbook(session, _workbook(tmp_path, ROWS), apply=True)
    r = client.post("/v1/auth/login", json={"login_id": ASHA, "password": ""})
    assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"
