"""Named scheduler scenarios: the data a rule needs, built with `Scenario`.

Each function takes a `Scenario` on the test site (rules version 2 already set by
the test) and builds its data. It returns a dict of the objects a test needs.
The rules each one checks are listed in `scenario_matrix.py`, which maps every
SCHR- row to a scenario or to a test. The data is deliberately small: one
scenario per kind of data the seed tool does not hold (zones, breaks, trainees,
entitlements, outcomes, cutoffs on each kind of day, sick, leave and late start).

Week and day anchors: SUNDAY is 18-Oct-26 (a Sunday, ADM-SCH-09). MONDAY and the
rest are offsets from it. Weekly off is Wednesday (weekday index 2).
"""
from datetime import date, time, timedelta

from app.scheduling import entitlements, service
from app.scheduling.models import Job, Visit
from tests.scheduling.builders import INTERNAL
from tests.scheduling.conftest import SUNDAY

MONDAY = SUNDAY + timedelta(days=1)
TUESDAY = SUNDAY + timedelta(days=2)
WEDNESDAY = SUNDAY + timedelta(days=3)
THURSDAY = SUNDAY + timedelta(days=4)
SATURDAY = SUNDAY + timedelta(days=6)
WEEKLY_OFF_INDEX = 2  # Monday is 0, so Wednesday is 2
WEEK1 = date(2026, 10, 12)  # Monday of the service week that holds SUNDAY's Monday
WEEK2 = WEEK1 + timedelta(days=7)


def weekly_off_wednesday(sc):
    """Wednesday has no working slot: no Exterior and no Interior that day."""
    sc.slots(off=(WEEKLY_OFF_INDEX,))
    crew = sc.cleaner("Ravi", shift=(360, 720))
    cars = sc.cars(2)
    return {"crew": crew, "cars": cars, "run": (TUESDAY, 3)}  # Tuesday, Wednesday, Thursday


def home_zones_absent_and_zoneless_car(sc):
    """Two zones. North's cleaner Asha has room for one car; the second North car
    goes to South's cleaner Bina as a cross-zone job. Chetan (North) is off sick.
    A car with no zone is served by anyone and is never cross-zone."""
    asha = sc.cleaner("Asha", shift=(360, 390), zone="North")  # room for one job
    bina = sc.cleaner("Bina", shift=(360, 480), zone="South")
    chetan = sc.cleaner("Chetan", shift=(360, 480), zone="North")
    sc.exception(chetan, MONDAY, "Sick")
    north = sc.cars(2, zone="North")
    south = sc.cars(2, zone="South")
    loose = sc.car()  # no zone
    return {"asha": asha, "bina": bina, "chetan": chetan, "north": north,
            "south": south, "loose": loose, "run": (MONDAY, 1)}


def breaks_site_crew_and_date_range(sc):
    """Break lookup: site default, a crew override, a date-range override on one
    day, and a cleaner whose window starts after the break (no break, BRK-07)."""
    site_default = sc.cleaner("Site", shift=(360, 720))
    crew_override = sc.cleaner("Crew", shift=(360, 720))
    late_start = sc.cleaner("Late", shift=(600, 720))  # starts after 10:00
    sc.break_rule(MONDAY, MONDAY, cleaner=crew_override, minutes=(660, 690))
    sc.break_rule(TUESDAY, TUESDAY, minutes=(540, 570))  # site-wide, Tuesday only, 09:00
    return {"site": site_default, "crew": crew_override, "late": late_start,
            "monday": MONDAY, "tuesday": TUESDAY}


def trainee_follows_member(sc):
    """A Trainee adds no capacity. Mohan's window fits three cars; the fourth car
    must stay unassigned even though the Trainee is on shift."""
    member = sc.cleaner("Mohan", shift=(360, 450), zone="North")
    trainee = sc.cleaner("Trainee", shift=(360, 720), role="Trainee", paired=member.id)
    cars = sc.cars(4, zone="North")
    return {"member": member, "trainee": trainee, "cars": cars, "run": (MONDAY, 1)}


def interior_oldest_week_first(sc):
    """Capacity for one Interior. Car Old owes an overdue row from week 1; car New
    owes a row for week 2. Oldest first: Old gets the Interior, New stays owed."""
    old = sc.car(interior=True)
    new = sc.car(interior=True)
    sc.entitlement(old, WEEK1)
    sc.entitlement(new, WEEK2)
    sc.cleaner("Ravi", shift=(420, 510))  # 07:00 to 08:30: two Exteriors and one Interior
    return {"old": old, "new": new, "run": (TUESDAY, 1)}


def weekend_cutoff_is_soft(sc):
    """A car whose cutoff is 06:15, and a cleaner who starts at 06:00. On a weekday
    the Exterior cannot finish in time, so it is placed late and flagged (SCHR-CUT-09).
    On Saturday the cutoff is flexible: the job runs late and is placed."""
    sc.cleaner("Ravi", shift=(360, 480))
    car = sc.car(cutoff=_time(6, 15))
    return {"car": car, "saturday": SATURDAY, "monday": MONDAY}


def weekday_cutoff_is_hard(sc):
    """A Monday cutoff of 06:45, with the cleaner starting at 06:30: the Exterior
    would end at 07:00. An Exterior is protected (SCHR-CUT-09), so it is placed
    late and flagged; an Interior in the same position would be unassigned."""
    sc.cleaner("Ravi", shift=(390, 480))
    car = sc.car(cutoff=_time(6, 45))
    return {"car": car, "run": (MONDAY, 1)}


def sick_leave_and_late_start(sc):
    """Monday: Asha is sick, Bina is on leave, Chetan starts at 10:00, Dev is in
    normal hours. Only Chetan (from 10:00) and Dev may take jobs."""
    asha = sc.cleaner("Asha", shift=(360, 720))
    bina = sc.cleaner("Bina", shift=(360, 720))
    chetan = sc.cleaner("Chetan", shift=(360, 720))
    dev = sc.cleaner("Dev", shift=(360, 720))
    sc.exception(asha, MONDAY, "Sick")
    sc.exception(bina, MONDAY, "Leave")
    sc.exception(chetan, MONDAY, "Late start", from_minute=600)
    cars = sc.cars(3)
    return {"asha": asha, "bina": bina, "chetan": chetan, "dev": dev, "cars": cars,
            "run": (MONDAY, 1)}


def hand_placement_past_cutoff(sc):
    """An admin places an Exterior by hand so that it ends after the Monday cutoff.
    The placement stays, and the breach is recorded for the exception report."""
    crew = sc.cleaner("Ravi", shift=(360, 480))
    car = sc.car(cutoff=_time(6, 20))
    sc.fixed(car, MONDAY, crew, start=360)  # 06:00 to 06:30, past 06:20
    return {"car": car, "crew": crew, "run": (MONDAY, 1)}


def deferred_interior_returns_to_pending(sc):
    """A planned Interior is marked Deferred by the crew. Its row goes back to
    Pending with its original service week."""
    car = sc.car(interior=True)
    row = sc.entitlement(car, WEEK1)
    schedule = service.get_or_create_schedule(sc.db, sc.site.id, TUESDAY, 1)
    visit = Visit(schedule_id=schedule.id, vehicle_id=car.id, date=TUESDAY)
    sc.db.add(visit)
    sc.db.flush()
    job = Job(visit_id=visit.id, service=INTERNAL, duration_minutes=30)
    sc.db.add(job)
    sc.db.flush()
    entitlements.plan(sc.db, row, job)
    sc.db.commit()
    return {"car": car, "row": row, "job": job}


def exterior_shortfall(sc):
    """Capacity for two Exteriors from 07:00 to 08:00. Two cars are Exterior-only;
    a third car also owes an Interior. The Exteriors come first: the two cars are
    served, the third car's Exterior is the shortfall, and no Interior is placed."""
    sc.cleaner("Ravi", shift=(420, 480))
    served = sc.cars(2)
    short = sc.car(interior=True)
    sc.entitlement(short, WEEK1)
    return {"served": served, "short": short, "run": (TUESDAY, 1)}


def shift_too_short(sc):
    """A cleaner on a 20-minute shift. No 30-minute job fits, so the car is
    unassigned with the shift-too-short reason."""
    sc.cleaner("Ravi", shift=(360, 380))
    car = sc.car()
    return {"car": car, "run": (TUESDAY, 1)}


def _time(hour: int, minute: int):
    return time(hour, minute)
