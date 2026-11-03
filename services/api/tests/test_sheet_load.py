"""The Monthly Customer load, tested with a made-up workbook. No real customer data."""
from datetime import datetime, time

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select

from app.customers.models import Customer, Subscription, Vehicle
from app.customers.sheet_load import SHEET, load_monthly_customers
from app.directory.models import Plan, Society, Zone
from app.directory.seed import seed_defaults
from app.identity.models import Login

HEAD = ["Sl. No.", "Customer Name", "Alternate customer names", "Phone Number", "Make",
        "Model", "Variant", "Car Number", "Flat No.", "Basement1/2/3", "Parking Number",
        "Time Before (Customer Wish)", "Start Date", "Interior Day", "Package", "Notes"]
START = datetime(2026, 9, 14)  # noqa: DTZ001  (Excel dates carry no timezone)
ROWS = [
    [1, "Asha Rao", None, 9000000101.0, "BMW", "3 Series", "330 Li", "CH01DD6769", "D-27 001",
     "Zone1", "B1-214", time(8, 0), START, "Saturday", 1299.0, "ignored"],
    [2, "Asha Rao", None, 9000000101.0, "Mahindra", "Thar", None, "HR 98 V 9899", "D-27 001",
     "Zone1", "B1-215", None, START, "Alternate days each car", 1299.0, None],
    [3, "Rakesh Khandelwal", "Utsav", 9000000102.0, "Toyota", "Fortuner", None,
     "T0926HR9225CH", "A-805", "Zone2", "Under D25", time(7, 30), START, None, 1000.0, None],
    [4, "Vikram", None, 9000000103.0, "Tata", None, None, "XXXXXX2001", None, None,
     "Basement-2 Near B Tower", None, None, None, 699.0, None],
]


def _sheet(tmp_path, rows=ROWS):
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.append(HEAD)
    for row in rows:
        ws.append(row)
    path = tmp_path / "monthly.xlsx"
    wb.save(path)
    return path


@pytest.fixture
def society(db):
    s = Society(name="Priveo Demo Society")
    db.add(s)
    db.commit()
    return s


def test_trial_run_saves_nothing(db, society, tmp_path):
    report = load_monthly_customers(db, _sheet(tmp_path), apply=False)
    assert not report.errors
    assert report.customers_created == 3 and report.vehicles_created == 4
    assert db.scalar(select(func.count()).select_from(Customer)) == 0
    assert db.scalar(select(func.count()).select_from(Plan)) == 0
    assert db.scalar(select(func.count()).select_from(Zone)) == 0


def test_load_maps_the_sheet(db, society, tmp_path):
    report = load_monthly_customers(db, _sheet(tmp_path), apply=True)
    assert report.customers_created == 3 and report.vehicles_created == 4
    assert report.subscriptions_created == 3 and report.zones_created == 2
    assert report.plans_created == 4

    asha = db.scalar(select(Customer).where(Customer.first_name == "Asha"))
    assert (asha.email, asha.mobile, asha.flat) == (None, "9000000101", "D-27 001")
    login = db.get(Login, asha.login_id)
    assert (login.role, login.login_id, login.must_change_mpin) == ("customer", "9000000101", True)
    assert asha.society_id == society.id and asha.source == "migration"
    assert db.scalar(select(func.count()).select_from(Login)) == 3
    rakesh = db.scalar(select(Customer).where(Customer.last_name == "Khandelwal"))
    assert rakesh.alternate_names == "Utsav"

    bmw = db.scalar(select(Vehicle).where(Vehicle.model == "3 Series"))
    assert (bmw.make, bmw.variant, bmw.registration) == ("BMW", "330 Li", "CH01DD6769")
    assert (bmw.parking_basement, bmw.parking_number) == ("B1", "214")
    assert db.get(Zone, bmw.zone_id).name == "Zone1"
    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == bmw.id))
    assert (sub.monthly_price_rupees, sub.interior_day, sub.cutoff_time) == (
        1299, "Saturday", time(8, 0))
    assert db.get(Plan, sub.plan_id).name == "Luxe" and sub.first_service_date.day == 14

    thar = db.scalar(select(Vehicle).where(Vehicle.model == "Thar"))
    assert thar.registration == "HR98V9899"
    custom = db.scalar(select(Subscription).where(Subscription.vehicle_id == thar.id))
    assert custom.interior_day == "Custom"
    assert custom.interior_day_notes == "Alternate days each car"

    # As given: not a registration format, longer than 12, free-text parking.
    fortuner = db.scalar(select(Vehicle).where(Vehicle.model == "Fortuner"))
    assert fortuner.registration == "T0926HR9225CH"
    assert (fortuner.parking_basement, fortuner.parking_number) == ("", "Under D25")
    assert db.get(Plan, db.scalar(select(Subscription.plan_id).where(
        Subscription.vehicle_id == fortuner.id))).name == "Special 1K"

    # No start date: the vehicle loads, without a subscription, and it is reported.
    nitin = db.scalar(select(Vehicle).where(Vehicle.registration == "XXXXXX2001"))
    assert nitin.parking_number == "Basement-2 Near B Tower"
    assert db.scalar(select(Subscription).where(Subscription.vehicle_id == nitin.id)) is None
    assert any("row 4" in w and "without a subscription" in w for w in report.warnings)


def test_report_has_no_personal_data(db, society, tmp_path):
    report = load_monthly_customers(db, _sheet(tmp_path), apply=False)
    text = " ".join(report.warnings + report.errors + [report.society])
    for secret in ("Asha", "9000000101", "CH01DD6769", "Vikram", "Khandelwal"):
        assert secret not in text


def test_running_again_adds_nothing(db, society, tmp_path):
    path = _sheet(tmp_path)
    load_monthly_customers(db, path, apply=True)
    again = load_monthly_customers(db, path, apply=True)
    assert again.vehicles_created == 0 and again.vehicles_kept == 4
    assert again.customers_created == 0 and again.plans_created == 0
    assert db.scalar(select(func.count()).select_from(Customer)) == 3
    assert db.scalar(select(func.count()).select_from(Vehicle)) == 4


def test_existing_premium_care_plan_is_renamed(db, society, tmp_path):
    db.add(Plan(code="PLN-0001", name="Premium Care", monthly_price_rupees=999,
                includes_interior=True))
    db.commit()
    report = load_monthly_customers(db, _sheet(tmp_path), apply=True)
    assert report.plans_renamed == 1 and report.plans_created == 3
    assert db.scalar(select(Plan.code).where(Plan.name == "Premium")) == "PLN-0001"
    assert sorted(db.scalars(select(Plan.code))) == [
        "PLN-0001", "PLN-0002", "PLN-0003", "PLN-0004"]


def test_a_named_society_is_needed_when_there_are_several(db, society, tmp_path):
    db.add(Society(name="Other"))
    db.commit()
    with pytest.raises(ValueError, match="Name the one"):
        load_monthly_customers(db, _sheet(tmp_path), apply=False)
    report = load_monthly_customers(db, _sheet(tmp_path), society_name="other", apply=False)
    assert report.society == "Other"


def test_a_row_without_a_phone_is_not_loaded(db, society, tmp_path):
    bad = [9, "No Phone", None, None, "Tata", "Nexon", None, "HR26AA1111", None, None,
           None, None, START, None, 999.0, None]
    report = load_monthly_customers(db, _sheet(tmp_path, [bad]), apply=True)
    assert report.errors == ["row 9: the name or the 10-digit phone number is missing"]
    assert db.scalar(select(func.count()).select_from(Vehicle)) == 0


def test_the_deploy_seed_does_not_re_add_the_renamed_starter_plan(db, society, tmp_path):
    """The deploy runs the seed every time. After the load renames Premium Care to
    Premium, it must not add Premium Care again under the same plan code."""
    seed_defaults(db, starter_data=True)
    db.commit()
    load_monthly_customers(db, _sheet(tmp_path), apply=True)
    before = sorted(db.scalars(select(Plan.name)))
    assert "Premium" in before and "Premium Care" not in before
    seed_defaults(db, starter_data=True)
    db.commit()
    assert sorted(db.scalars(select(Plan.name))) == before


def test_reuse_plans_by_price_keeps_existing_names(db, society, tmp_path):
    for code, name, price in (("PLN-0001", "Monthly Care -699", 699),
                              ("PLN-0002", "Monthly Subscription-999", 999),
                              ("PLN-0003", "Monthly Subscription-1299", 1299)):
        db.add(Plan(code=code, name=name, monthly_price_rupees=price, includes_interior=True))
    db.commit()
    report = load_monthly_customers(db, _sheet(tmp_path), apply=True, reuse_plans_by_price=True)
    assert report.plans_created == 1 and report.plans_renamed == 0
    names = set(db.scalars(select(Plan.name)))
    assert names == {"Monthly Care -699", "Monthly Subscription-999",
                     "Monthly Subscription-1299", "Special 1K"}
    # Every subscription points at the plan with its own price.
    for sub in db.scalars(select(Subscription)):
        plan = db.get(Plan, sub.plan_id)
        assert plan is not None and plan.monthly_price_rupees == sub.monthly_price_rupees
    again = load_monthly_customers(db, _sheet(tmp_path), apply=True, reuse_plans_by_price=True)
    assert again.plans_created == 0 and again.vehicles_created == 0
