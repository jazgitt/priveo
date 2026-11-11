"""The sheet sets the status of the Scheduled visits on 4 to 7 Nov 2026 (owner answers,
9 Nov 2026): "Priveo Missed" is Could not complete; "int,ext" adds a completed Interior
when the visit has none; "ext" marks an Interior of the visit skipped; a skip keeps the
sheet's reason text. A day with no visit is written as live history. Nothing is notified."""
from datetime import date, datetime

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.customers.history_convert import parse_cell
from app.customers.history_load import load_service_history
from app.customers.models import Customer, Vehicle
from app.directory.models import Society
from app.identity.models import Login
from app.scheduling.models import InteriorEntitlement, Job, Schedule, Visit
from app.visits.models import JobOutcome

DAYS = [date(2026, 11, n) for n in (4, 5, 6, 7)]
EXT, INT = "Cleaning-External", "Cleaning-Internal"
D6 = date(2026, 11, 6)


def sheet(tmp_path, cars):
    book = Workbook()
    ws = book.active
    ws.title = "calendar"
    ws.append(["Car Model", "Car Number", "Customer Name",
               *[datetime(d.year, d.month, d.day) for d in DAYS],  # noqa: DTZ001
               "Crew"])
    for car, cells in cars.items():
        ws.append(["Creta", car, "A Name", *[cells.get(d) for d in DAYS], "Satish"])
    path = tmp_path / "v2.xlsx"
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
    for reg in ("AB12CD0001", "AB12CD0002", "AB12CD0003"):
        db.add(Vehicle(customer_id=customer.id, registration=reg, model="Creta"))
    db.add(Login(role="admin", login_id="testadminid", display_name="Admin", password_hash="x"))
    db.commit()


def scheduled(db, reg, day, services=(EXT,), status="Scheduled"):
    vehicle = db.scalar(select(Vehicle).where(Vehicle.registration == reg))
    schedule = db.scalar(select(Schedule).where(Schedule.start_date == day))
    if schedule is None:
        schedule = Schedule(society_id=vehicle.society_id or db.scalar(select(Society.id)),
                            start_date=day, end_date=day, status="Draft")
        db.add(schedule)
        db.flush()
    visit = Visit(schedule_id=schedule.id, vehicle_id=vehicle.id, date=day, status=status)
    db.add(visit)
    db.flush()
    for service in services:
        db.add(Job(visit_id=visit.id, service=service, status="Scheduled", duration_minutes=30))
    db.commit()
    return visit


def jobs_of(db, visit):
    return {j.service: j.status for j in db.scalars(select(Job).where(Job.visit_id == visit.id))}


def test_the_cell_values_are_read_and_no_reason_is_refused():
    assert parse_cell("ext") == ("Exterior", "Completed", "")
    assert parse_cell("int,ext") == ("Exterior + Interior", "Completed", "")
    assert parse_cell("skipped") == ("", "Skipped", "")
    assert parse_cell("skipped - Customer car gone for repair till 13th Nov") == (
        "", "Skipped", "Customer car gone for repair till 13th Nov")
    assert parse_cell("Skipped - Priveo Missed") == ("", "Missed", "")
    assert parse_cell("AB12CD0001") is None


def test_ext_completes_the_scheduled_exterior(db, world, tmp_path):
    visit = scheduled(db, "AB12CD0001", D6)
    path = sheet(tmp_path, {"AB12CD0001": {D6: "ext"}})
    report = load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7))
    assert report.updated["Completed"] == 1
    db.refresh(visit)
    assert jobs_of(db, visit) == {EXT: "Completed"} and visit.status == "Completed"


def test_int_ext_adds_a_completed_interior_and_counts_in_its_week(db, world, tmp_path):
    from app.scheduling import entitlements

    vehicle = db.scalar(select(Vehicle).where(Vehicle.registration == "AB12CD0002"))
    week = entitlements.week_start(db, D6, entitlements.society_of(db, vehicle.id))
    owed = InteriorEntitlement(vehicle_id=vehicle.id, service_week_start=week, seq=1, status="Pending")
    db.add(owed)
    visit = scheduled(db, "AB12CD0002", D6)
    path = sheet(tmp_path, {"AB12CD0002": {D6: "int,ext"}})
    report = load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7))
    assert report.updated_jobs["interior_added"] == 1
    db.refresh(visit)
    assert jobs_of(db, visit) == {EXT: "Completed", INT: "Completed"}
    db.refresh(owed)
    assert owed.status == "Completed" and owed.completed_on == D6


def test_ext_on_a_visit_with_an_interior_skips_the_interior(db, world, tmp_path):
    visit = scheduled(db, "AB12CD0003", D6, services=(EXT, INT))
    path = sheet(tmp_path, {"AB12CD0003": {D6: "ext"}})
    report = load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7))
    assert report.updated_jobs["interior_skipped"] == 1
    db.refresh(visit)
    assert jobs_of(db, visit) == {EXT: "Completed", INT: "Skipped"}
    interior = db.scalar(select(Job).where(Job.visit_id == visit.id, Job.service == INT))
    assert db.scalar(select(JobOutcome).where(JobOutcome.job_id == interior.id)).kind == "skipped"


def test_a_skip_keeps_the_sheet_reason_and_a_missed_cell_is_could_not_complete(db, world, tmp_path):
    skipped = scheduled(db, "AB12CD0001", date(2026, 11, 5))
    missed = scheduled(db, "AB12CD0002", date(2026, 11, 5))
    path = sheet(tmp_path, {
        "AB12CD0001": {date(2026, 11, 5): "skipped - Customer not available"},
        "AB12CD0002": {date(2026, 11, 5): "Skipped - Priveo Missed"},
    })
    load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7))
    db.refresh(skipped)
    db.refresh(missed)
    assert jobs_of(db, skipped) == {EXT: "Skipped"}
    outcome = db.scalar(select(JobOutcome).join(Job, Job.id == JobOutcome.job_id).where(Job.visit_id == skipped.id))
    assert outcome.note == "Customer not available"
    assert jobs_of(db, missed) == {EXT: "Could not complete"}


def test_a_completed_visit_is_not_changed(db, world, tmp_path):
    done = scheduled(db, "AB12CD0001", D6, status="Completed")
    path = sheet(tmp_path, {"AB12CD0001": {D6: "skipped"}})
    report = load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7))
    db.refresh(done)
    assert jobs_of(db, done) == {EXT: "Scheduled"} and report.updated == {}


def test_a_day_with_no_visit_is_written_as_live_history_and_an_empty_cell_records_nothing(db, world, tmp_path):
    path = sheet(tmp_path, {"AB12CD0003": {date(2026, 11, 4): "ext"}})
    report = load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7))
    assert report.to_load == 1 and report.no_entry == 3
    assert db.scalar(select(Visit).where(Visit.date == date(2026, 11, 4))).status == "Completed"


def test_scheduled_visits_the_sheet_does_not_cover_are_listed(db, world, tmp_path):
    visit = scheduled(db, "AB12CD0002", D6)
    path = sheet(tmp_path, {"AB12CD0001": {D6: "ext"}})
    report = load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7))
    assert report.scheduled_without_entry == [("AB12CD0002", D6, str(visit.id))]


def test_a_trial_run_changes_nothing(db, world, tmp_path):
    visit = scheduled(db, "AB12CD0002", D6, services=(EXT, INT))
    path = sheet(tmp_path, {"AB12CD0002": {D6: "ext"}})
    report = load_service_history(db, path, apply=False, since=date(2026, 11, 4), through=date(2026, 11, 7))
    assert report.updated["Completed"] == 1
    db.expire_all()
    assert jobs_of(db, visit) == {EXT: "Scheduled", INT: "Scheduled"}


def test_no_notification_is_sent(db, world, tmp_path, monkeypatch):
    from app.notifications import emit

    def refuse(*args, **kwargs):
        raise AssertionError("a notification was sent")
    for name in ("job_status_changed", "job_missed", "job_removed", "admin_push"):
        if hasattr(emit, name):
            monkeypatch.setattr(emit, name, refuse)
    scheduled(db, "AB12CD0001", D6, services=(EXT, INT))
    path = sheet(tmp_path, {"AB12CD0001": {D6: "skipped - Customer not available"}})
    load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7))


def test_an_alias_matches_a_sheet_car_to_its_registration(db, world, tmp_path):
    visit = scheduled(db, "AB12CD0003", D6)
    path = sheet(tmp_path, {"2001": {D6: "ext"}})
    report = load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7),
                                  aliases={"2001": "AB12CD0003"})
    assert report.vehicles_matched == 1 and report.updated["Completed"] == 1
    db.refresh(visit)
    assert visit.status == "Completed"


def test_an_alias_to_an_unknown_registration_stops(db, world, tmp_path):
    path = sheet(tmp_path, {"2001": {D6: "ext"}})
    with pytest.raises(ValueError):
        load_service_history(db, path, apply=True, since=date(2026, 11, 4), through=date(2026, 11, 7),
                             aliases={"2001": "NOPE0000"})
