"""The one-time load of the service history up to 3 Nov 2026 (calendar sheet, v4.1)."""
from datetime import date, datetime, timedelta

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select

from app.customers.history_load import (
    R_BLANK_AFTER_START,
    R_LIVE_VISIT,
    R_NO_VEHICLE,
    R_NOT_A_VALUE,
    load_service_history,
    read_fills,
)
from app.customers.models import Customer, LegacyServiceRecord, Vehicle
from app.directory.models import Society

START = date(2026, 10, 17)  # 17 Oct .. 3 Nov, without 21 Oct (the real sheet has no such column)
DAYS = [START + timedelta(days=n) for n in range(18) if START + timedelta(days=n) != date(2026, 10, 21)]


def sheet(tmp_path, cars):
    """cars: {car number: {day: cell}}; header like the real sheet, plus junk to the right."""
    book = Workbook()
    ws = book.active
    ws.title = "calendar"
    ws.append(["Car Model", "Car Number", "Customer Name",
               *[datetime(d.year, d.month, d.day) for d in DAYS],  # noqa: DTZ001 (Excel dates are naive)
               "Crew", "#VALUE!"])
    for car, cells in cars.items():
        ws.append(["Creta", car, "A Name", *[cells.get(d) for d in DAYS], "Satish", None])
    path = tmp_path / "v4.1.xlsx"
    book.save(path)
    return path


@pytest.fixture
def world(db):
    society = Society(name="Green Meadows", sector="Sector 1")
    db.add(society)
    db.flush()
    customer = Customer(first_name="A", last_name="Rao", mobile="9000000111", society_id=society.id)
    db.add(customer)
    db.flush()
    for reg in ("AB12CD0001", "AB12CD0002"):
        db.add(Vehicle(customer_id=customer.id, registration=reg, model="Creta"))
    db.commit()


def d(n):  # 17 Oct + n
    return START + timedelta(days=n)


def test_maps_the_cells_and_the_owner_rules(db, world, tmp_path):
    path = sheet(tmp_path, {
        "AB12CD0001": {d(0): "ext", d(1): "int,ext", d(2): "skipped - Rain", d(3): "skipped",
                       d(11): "skipped", d(12): "ext"},          # d(11) = 28 Oct
        "AB12CD0002": {d(3): "ext", d(4): "ext"},
    })
    report = load_service_history(db, path, apply=True)
    rows = {(v, r.service_date): r for v, r in
            ((db.get(Vehicle, r.vehicle_id).registration, r) for r in db.scalars(select(LegacyServiceRecord)))}
    first = lambda day: rows[("AB12CD0001", day)]  # noqa: E731
    assert (first(d(0)).services, first(d(0)).outcome) == ("Exterior", "Completed")
    assert first(d(1)).services == "Exterior + Interior"
    assert (first(d(2)).outcome, first(d(2)).skip_reason) == ("Skipped", "Rain")
    assert (first(d(3)).outcome, first(d(3)).skip_reason) == ("Skipped", "")      # plain skipped: no reason
    assert first(date(2026, 10, 28)).skip_reason == "Weekly off"                  # 28 Oct
    assert first(date(2026, 10, 21)).skip_reason == "Weekly off"                  # no column: still added
    assert ("AB12CD0002", date(2026, 10, 21)) in rows
    assert report.weekly_off_added == 2 and report.before_start > 0
    assert report.completed + report.skipped == report.to_load == db.scalar(select(func.count(LegacyServiceRecord.id)))


def test_trial_run_saves_nothing_and_a_rerun_adds_nothing(db, world, tmp_path):
    path = sheet(tmp_path, {"AB12CD0001": {d(0): "ext", d(1): "ext"}})
    trial = load_service_history(db, path, apply=False)
    assert trial.to_load > 0 and db.scalar(select(func.count(LegacyServiceRecord.id))) == 0
    first = load_service_history(db, path, apply=True)
    again = load_service_history(db, path, apply=True)
    assert again.to_load == 0 and again.already_loaded == first.to_load
    assert db.scalar(select(func.count(LegacyServiceRecord.id))) == first.to_load


def test_everything_not_loaded_is_reported_with_a_reason(db, world, tmp_path):
    path = sheet(tmp_path, {
        "AB12CD0001": {d(0): "ext", d(1): "AB12CD0001", d(3): "ext"},          # junk text; blank d(2) after start
        "ZZ99ZZ9999": {d(0): "ext"},                                            # not in the database
    })
    report = load_service_history(db, path, apply=True)
    why = {(n.car_number, n.day): n.reason for n in report.not_loaded}
    assert why[("AB12CD0001", d(1))] == R_NOT_A_VALUE
    assert why[("AB12CD0001", d(2))] == R_BLANK_AFTER_START
    assert why[("ZZ99ZZ9999", d(0))] == R_NO_VEHICLE
    assert ("AB12CD0001", d(0)) not in why
    assert db.scalar(select(func.count(LegacyServiceRecord.id)).join(
        Vehicle, Vehicle.id == LegacyServiceRecord.vehicle_id).where(Vehicle.registration == "ZZ99ZZ9999")) == 0


def test_the_two_blank_cells_the_owner_filled_in(db, world, tmp_path):
    db.add(Vehicle(customer_id=db.scalar(select(Customer.id)), registration="AB12CD0003", model="Creta"))
    db.add(Vehicle(customer_id=db.scalar(select(Customer.id)), registration="AB12CD0004", model="Creta"))
    db.commit()
    day27, day18 = date(2026, 10, 27), date(2026, 10, 18)
    path = sheet(tmp_path, {
        "AB12CD0003": {date(2026, 10, 22): "ext", date(2026, 10, 26): "ext", date(2026, 10, 28): "ext"},
        "AB12CD0004": {date(2026, 10, 17): "ext", date(2026, 10, 19): "ext"},
    })
    fills = {("AB12CD0003", day27): "ext", ("AB12CD0004", day18): "int,ext"}
    report = load_service_history(db, path, apply=True, fills=fills)
    assert report.owner_fills == 2
    blank = {(n.car_number, n.day) for n in report.not_loaded if n.reason == R_BLANK_AFTER_START}
    assert ("AB12CD0003", day27) not in blank and ("AB12CD0004", day18) not in blank
    assert ("AB12CD0003", date(2026, 10, 23)) in blank      # other blanks are still reported
    got = {(db.get(Vehicle, r.vehicle_id).registration, r.service_date): r
           for r in db.scalars(select(LegacyServiceRecord))}
    assert got[("AB12CD0003", day27)].services == "Exterior"
    assert got[("AB12CD0004", day18)].services == "Exterior + Interior"


def test_a_day_with_a_live_visit_is_not_loaded(db, world, tmp_path):
    from app.scheduling.models import Schedule, Visit
    vehicle = db.scalar(select(Vehicle).where(Vehicle.registration == "AB12CD0001"))
    schedule = db.scalar(select(Schedule))
    assert schedule is None  # no schedule yet: build the minimum
    schedule = Schedule(society_id=db.scalar(select(Society.id)), start_date=d(0), end_date=d(0), status="Draft")
    db.add(schedule)
    db.flush()
    db.add(Visit(schedule_id=schedule.id, vehicle_id=vehicle.id, date=d(0)))
    db.commit()
    path = sheet(tmp_path, {"AB12CD0001": {d(0): "ext", d(1): "ext"}})
    report = load_service_history(db, path, apply=True)
    assert [(n.day, n.reason) for n in report.not_loaded if n.reason == R_LIVE_VISIT] == [(d(0), R_LIVE_VISIT)]
    loaded = {r.service_date for r in db.scalars(select(LegacyServiceRecord))}
    assert d(0) not in loaded and d(1) in loaded
    assert db.scalar(select(func.count(LegacyServiceRecord.id))) > 0


def test_a_workbook_without_the_calendar_sheet_stops(db, world, tmp_path):
    book = Workbook()
    book.active.title = "Other"
    path = tmp_path / "x.xlsx"
    book.save(path)
    with pytest.raises(ValueError):
        load_service_history(db, path, apply=True)


def test_the_fills_file_is_read_and_checked(tmp_path):
    good = tmp_path / "fills.csv"
    good.write_text("car_number,day,value\nab12 cd0003,2026-10-27,ext\nAB12CD0004,2026-10-18,\"int,ext\"\n")
    assert read_fills(good) == {("AB12CD0003", date(2026, 10, 27)): "ext",
                                ("AB12CD0004", date(2026, 10, 18)): "int,ext"}
    bad_value = tmp_path / "bad_value.csv"
    bad_value.write_text("car_number,day,value\nAB12CD0003,2026-10-27,done\n")
    with pytest.raises(ValueError):
        read_fills(bad_value)
    bad_day = tmp_path / "bad_day.csv"
    bad_day.write_text("car_number,day,value\nAB12CD0003,27 Oct,ext\n")
    with pytest.raises(ValueError):
        read_fills(bad_day)
