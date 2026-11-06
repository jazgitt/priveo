"""SCHS-39: the weekly summary endpoint (SCHR-OUT-02, SCHR-INT-17)."""
from datetime import date, timedelta

from sqlalchemy import select

from app.scheduling import entitlements, service
from app.scheduling.models import Job, ScheduleFinding, Visit
from tests.scheduling.builders import EXTERNAL, INTERNAL, Scenario
from tests.test_api import auth, login

URL = "/v1/admin/scheduling/reports/weekly"
WEEK1 = date(2026, 11, 2)  # Monday: the worked example of section 12
WEEK2 = WEEK1 + timedelta(days=7)
MON2, THU2 = WEEK2, WEEK2 + timedelta(days=3)
SAT2 = WEEK2 + timedelta(days=5)


def get(api, world, week, **extra):
    admin = auth(login(api, "admin")["access_token"])
    return api.get(URL, headers=admin, params={
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
    """The section 12 example: week 1 done on Mon 09-Nov, week 2 done on Thu 12-Nov."""
    car = sc.car()
    row1, row2 = sc.entitlement(car, WEEK1), sc.entitlement(car, WEEK2)
    j1 = _job(sc, car, MON2, INTERNAL, "Completed")
    j2 = _job(sc, car, THU2, INTERNAL, "Completed")
    entitlements.complete(sc.db, row1, j1, MON2)
    entitlements.complete(sc.db, row2, j2, THU2)
    return car


def test_schr_int_17_the_catch_up_example_shows_one_overdue_day_and_the_completion_date(
        api, world):
    sc = Scenario(world)
    _catch_up(sc)
    sc.db.commit()
    week1 = get(api, world, WEEK1, as_of=THU2.isoformat()).json()
    (line,) = week1["interiors_by_service_week"]
    assert (line["service_week_start"], line["completed_on"], line["overdue_days"]) == (
        WEEK1.isoformat(), MON2.isoformat(), 1)
    week2 = get(api, world, WEEK2, as_of=THU2.isoformat()).json()
    (own,) = week2["interiors_by_service_week"]
    assert (own["completed_on"], own["overdue_days"], own["catch_up"]) == (
        THU2.isoformat(), 0, False)
    assert len(week2["interiors_completed_in_week"]) == 2
    assert week2["catch_up_services"] == 1
    assert week2["carry_over"]["carried_in"] == 1 and week2["carry_over"]["still_owed"] == 0


def test_schr_out_02_totals_match_a_hand_computed_week(api, world, rules_v2):
    sc = Scenario(world)
    a, b, c = sc.cars(3)
    for car, day, status in [(a, MON2, "Completed"), (b, MON2, "Completed"),
                             (c, MON2, "Could not complete"), (a, SAT2, "Completed"),
                             (b, SAT2, "Scheduled")]:
        _job(sc, car, day, EXTERNAL, status)
    _job(sc, c, MON2, EXTERNAL, "Skipped")  # not mandatory: left out
    sc.db.commit()
    body = get(api, world, THU2).json()  # any date of the week picks the week
    assert body["week_start"] == WEEK2.isoformat() and body["week_end"] == (
        WEEK2 + timedelta(days=6)).isoformat()
    assert body["exteriors"] == {"due": 5, "completed": 3, "missed": 1, "open": 1}
    assert body["completions"] == {"weekday": 2, "weekend": 1}  # Saturday is a weekend day


def test_schr_out_02_an_owed_interior_counts_as_carry_over_and_overdue(api, world):
    sc = Scenario(world)
    car = sc.car()
    sc.entitlement(car, WEEK1)
    sc.db.commit()
    body = get(api, world, WEEK1, as_of=MON2.isoformat()).json()
    (line,) = body["interiors_by_service_week"]
    assert (line["status"], line["completed_on"], line["overdue_days"]) == ("Pending", None, 1)
    assert body["carry_over"] == {"carried_in": 0, "still_owed": 1}
    assert get(api, world, WEEK2, as_of=MON2.isoformat()).json()["carry_over"] == {
        "carried_in": 1, "still_owed": 1}


def test_schr_out_02_missed_breaks_are_counted_for_the_week(api, world):
    sc = Scenario(world)
    car = sc.car()
    job = _job(sc, car, MON2, EXTERNAL, "Scheduled")
    schedule_id = sc.db.get(Visit, job.visit_id).schedule_id
    sc.db.add(ScheduleFinding(schedule_id=schedule_id, job_id=job.id, code="break_missed"))
    sc.db.add(ScheduleFinding(schedule_id=schedule_id, job_id=None, code="no_cleaner"))
    sc.db.commit()
    assert get(api, world, WEEK2).json()["missed_breaks"] == 1
    assert get(api, world, WEEK1).json()["missed_breaks"] == 0


def test_schr_out_02_only_admins_may_read_it(api, world):
    cust = auth(login(api, "customer")["access_token"])
    r = api.get(URL, headers=cust, params={
        "society_id": str(world.society.id), "week_start": WEEK1.isoformat()})
    assert r.status_code in (401, 403)
