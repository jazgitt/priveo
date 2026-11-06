"""SCHS-48: the weekly summary as a file."""
import csv
import io
from datetime import date, timedelta

from sqlalchemy import select

from app.changes.rules import show_date
from app.scheduling import entitlements, service
from app.scheduling.models import Job, Visit
from tests.scheduling.builders import EXTERNAL, INTERNAL, Scenario
from tests.test_api import auth, login

SCREEN = "/v1/admin/scheduling/reports/weekly"
EXPORT = SCREEN + "/export"
WEEK1 = date(2026, 11, 2)
WEEK2 = WEEK1 + timedelta(days=7)
MON2, THU2 = WEEK2, WEEK2 + timedelta(days=3)


def _call(api, world, url, week, **extra):
    admin = auth(login(api, "admin")["access_token"])
    return api.get(url, headers=admin, params={
        "society_id": str(world.society.id), "week_start": week.isoformat(), **extra})


def _job(sc, car, day, service_name, status):
    schedule = service.get_or_create_schedule(sc.db, sc.site.id, WEEK2, 7)
    visit = sc.db.scalar(select(Visit).where(
        Visit.schedule_id == schedule.id, Visit.vehicle_id == car.id, Visit.date == day))
    if visit is None:
        visit = Visit(schedule_id=schedule.id, vehicle_id=car.id, date=day)
        sc.db.add(visit)
        sc.db.flush()
    job = Job(visit_id=visit.id, service=service_name, duration_minutes=30, status=status)
    sc.db.add(job)
    sc.db.flush()
    return job


def _catch_up(sc):
    car = sc.car()
    row1, row2 = sc.entitlement(car, WEEK1), sc.entitlement(car, WEEK2)
    entitlements.complete(sc.db, row1, _job(sc, car, MON2, INTERNAL, "Completed"), MON2)
    entitlements.complete(sc.db, row2, _job(sc, car, THU2, INTERNAL, "Completed"), THU2)
    return car


def _rows(response):
    return list(csv.reader(io.StringIO(response.text)))


def test_schr_out_06_the_file_is_a_csv_download(api, world):
    Scenario(world)
    world.db.commit()
    r = _call(api, world, EXPORT, WEEK2)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert f"weekly-summary-{WEEK2.isoformat()}.csv" in r.headers["content-disposition"]


def test_schr_out_06_the_file_matches_the_screen(api, world):
    sc = Scenario(world)
    car = _catch_up(sc)
    _job(sc, car, MON2, EXTERNAL, "Completed")
    _job(sc, car, THU2, EXTERNAL, "Could not complete")
    sc.db.commit()
    screen = _call(api, world, SCREEN, WEEK2, as_of=THU2.isoformat()).json()
    rows = _rows(_call(api, world, EXPORT, WEEK2, as_of=THU2.isoformat()))
    assert rows[0] == ["Weekly summary", show_date(WEEK2), show_date(WEEK2 + timedelta(days=6))]
    ext = screen["exteriors"]
    at = rows.index(["Exteriors", "Due", "Completed", "Missed", "Open"])
    assert rows[at + 1] == ["", str(ext["due"]), str(ext["completed"]), str(ext["missed"]),
                            str(ext["open"])]
    done = screen["completions"]
    assert ["", str(done["weekday"]), str(done["weekend"])] in rows
    carry = screen["carry_over"]
    assert ["", str(carry["carried_in"]), str(carry["still_owed"])] in rows
    assert ["Catch-up services", str(screen["catch_up_services"])] in rows
    assert ["Missed breaks", str(screen["missed_breaks"])] in rows
    # Each Interior line of the screen is a line of the file, in both blocks.
    for block, key in (("Interiors by service week", "interiors_by_service_week"),
                       ("Interiors completed in the week", "interiors_completed_in_week")):
        start = rows.index([block]) + 2
        expected = [[car.registration, show_date(date.fromisoformat(ln["service_week_start"])),
                     ln["status"],
                     show_date(date.fromisoformat(ln["completed_on"])) if ln["completed_on"] else "",
                     str(ln["overdue_days"]), "Yes" if ln["catch_up"] else "No"]
                    for ln in screen[key]]
        assert rows[start:start + len(expected)] == expected and expected


def test_schr_out_06_week_1_shows_one_overdue_day_in_the_file(api, world):
    sc = Scenario(world)
    car = _catch_up(sc)
    sc.db.commit()
    rows = _rows(_call(api, world, EXPORT, WEEK1, as_of=THU2.isoformat()))
    line = next(r for r in rows if r[:2] == [car.registration, show_date(WEEK1)])
    assert line[2:5] == ["Completed", show_date(MON2), "1"]


def test_schr_out_06_only_admins_may_download_it(api, world):
    cust = auth(login(api, "customer")["access_token"])
    r = api.get(EXPORT, headers=cust, params={
        "society_id": str(world.society.id), "week_start": WEEK1.isoformat()})
    assert r.status_code in (401, 403)
