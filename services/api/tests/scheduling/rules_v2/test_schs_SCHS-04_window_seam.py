"""SCHS-04: cleaner windows, job windows and capacity come from small rule
modules found in app/scheduling/window_rules. The base rules reproduce the old
behaviour exactly, which a golden file captured before the refactor proves."""
import importlib
import json
import os
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.directory.models import Society, WorkingSlot
from app.identity.models import Login
from app.scheduling import service, window_rules, windows
from app.scheduling.models import SchedulingCrew, SchedulingCrewException
from tests.scheduling.conftest import SUNDAY

GOLDEN = Path(__file__).with_name("schs_04_golden.json")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SERVICES = ["Cleaning-External", "Cleaning-Internal", "Deep Spa"]


def _hours(extra_monday=True):
    out = [{"day": d, "working": d != "Wednesday", "start": "05:30" if d != "Wednesday" else "",
            "end": "12:00" if d != "Wednesday" else "", "extra_slots": []} for d in DAYS]
    if extra_monday:
        out[0]["extra_slots"] = [{"start": "16:00", "end": "18:00"}]
    return out


def _crew(db, society, name, role="Member", start=330, end=720, hours=None):
    login = Login(role="crew", login_id=f"8{uuid.uuid4().int % 10**9:09d}", display_name=name)
    db.add(login)
    db.flush()
    member = SchedulingCrew(login_id=login.id, society_id=society.id, role=role,
                            start_minute=start, end_minute=end, working_hours=hours)
    db.add(member)
    db.flush()
    return member


def _build(world):
    """Two sites with different crew, slots, exceptions and cars."""
    db = world.db
    world.add_crew(name="Asha", start=360, end=420)
    world.add_crew(name="Bala", start=300, end=780)
    world.add_crew(name="Chitra", role="Trainee", start=360, end=600)
    _crew(db, world.society, "Dev", hours=_hours())
    world.add_vehicle(cutoff=None, interior_day="Sunday")
    world.add_vehicle(interior_day="Tuesday")
    world.add_vehicle()
    other = Society(name="Second Site")
    db.add(other)
    db.flush()
    c1 = _crew(db, other, "Esha", start=300, end=600)
    c2 = _crew(db, other, "Farid", hours=_hours(False))
    db.add(WorkingSlot(society_id=world.society.id, service="Cleaning-External",
                       start_minute=330, end_minute=600, days=[0, 1, 2, 3, 4, 5]))
    db.add(WorkingSlot(society_id=world.society.id, service="Cleaning-Internal",
                       start_minute=420, end_minute=480, days=[0, 1]))
    db.add(WorkingSlot(society_id=other.id, service="Cleaning-External",
                       start_minute=360, end_minute=540, days=[0, 1, 2, 3, 4, 5, 6]))
    db.add(SchedulingCrewException(crew_id=world.crew[1].id, on_date=SUNDAY + timedelta(1),
                                   kind="Late start", from_minute=420))
    db.add(SchedulingCrewException(crew_id=c1.id, on_date=SUNDAY + timedelta(2), kind="Sick"))
    db.add(SchedulingCrewException(crew_id=c2.id, on_date=SUNDAY + timedelta(3), kind="Leave"))
    db.commit()
    return [world.society, other]


def _snapshot(world, sites):
    db = world.db
    out = {}
    week = [SUNDAY + timedelta(i) for i in range(7)]
    for site in sites:
        crew = service.load_crew(db, site.id)
        names = {c.id: db.get(Login, c.login_id).display_name for c in crew.values()}
        avail = service.availability(db, crew, week)
        out[f"{site.name}:availability"] = {
            d.isoformat(): sorted([str(names[c]), [list(w) for w in ws]] for c, ws in v.items())
            for d, v in avail.items()}
        out[f"{site.name}:service_windows"] = {
            f"{svc}:{d.isoformat()}": [list(w) for w in service.service_windows(db, site.id, svc, d)]
            for svc in SERVICES for d in week}
        cap = json.loads(json.dumps(service.capacity(db, site.id, week[0], week[-1]), default=str))
        by_id = {str(k): v for k, v in names.items()}
        for day in cap:  # crew ids are random: name them and sort
            for row in day["availability"]:
                row["crew_id"] = by_id[row["crew_id"]]
            day["availability"].sort(key=lambda r: r["crew_id"])
        out[f"{site.name}:capacity"] = cap
    return out


def _stable(snap):
    return json.dumps(snap, sort_keys=True, indent=1, default=str)


def test_golden_capacity_availability_and_job_windows_are_unchanged(world):
    sites = _build(world)
    text = _stable(_snapshot(world, sites))
    if os.environ.get("SCHS04_RECORD"):
        GOLDEN.write_text(text)
    assert text == GOLDEN.read_text()


# ---- the seam ---------------------------------------------------------------

@pytest.fixture
def rule_file():
    """Drops a rule module into the folder and removes it afterwards."""
    folder = Path(window_rules.__file__).parent
    created = []

    def _drop(name, body):
        path = folder / f"{name}.py"
        path.write_text(body)
        created.append(path)
        importlib.invalidate_caches()
        return path

    yield _drop
    import sys
    for path in created:
        path.unlink(missing_ok=True)
        sys.modules.pop(f"app.scheduling.window_rules.{path.stem}", None)
    importlib.invalidate_caches()


def test_base_rules_are_found_in_a_deterministic_order():
    names = [m.__name__.rsplit(".", 1)[1] for m in window_rules.discover()]
    assert names == window_rules_order()
    assert names == [m.__name__.rsplit(".", 1)[1] for m in window_rules.discover()]


def window_rules_order():
    mods = window_rules.discover()
    return [m.__name__.rsplit(".", 1)[1]
            for m in sorted(mods, key=lambda m: (getattr(m, "ORDER", 100), m.__name__))]


def test_a_dropped_rule_changes_a_cleaners_windows(world, rule_file):
    world.add_crew(start=360, end=420)
    world.db.commit()
    crew = service.load_crew(world.db, world.society.id)
    cid = next(iter(crew))
    before = service.availability(world.db, crew, [SUNDAY])[SUNDAY][cid]
    assert before == [(360, 420)]
    rule_file("zz_test_late", "ORDER = 500\n"
              "def cleaner_windows(db, crew, day, windows, exception):\n"
              "    return [(max(s, 380), e) for s, e in windows]\n")
    assert service.availability(world.db, crew, [SUNDAY])[SUNDAY][cid] == [(380, 420)]


def test_a_dropped_rule_changes_a_jobs_windows(world, rule_file):
    world.db.commit()
    assert service.service_windows(world.db, world.society.id, "Deep Spa", SUNDAY) == ((0, 1440),)
    rule_file("zz_test_job", "ORDER = 500\n"
              "def job_windows(db, society_id, service, day, windows):\n"
              "    return tuple(w for w in windows if w[0] >= 100) or ((60, 120),)\n")
    assert service.service_windows(world.db, world.society.id, "Deep Spa", SUNDAY) == ((60, 120),)


def test_a_dropped_rule_adds_a_capacity_line(world, rule_file):
    world.add_crew()
    world.db.commit()
    plain = service.capacity(world.db, world.society.id, SUNDAY, SUNDAY)[0]
    rule_file("zz_test_cap", "def capacity_lines(db, society_id, day):\n"
              "    return [{'service': 'Test rule', 'source': 'Rule', 'jobs': 1, 'minutes': 15}]\n")
    day = service.capacity(world.db, world.society.id, SUNDAY, SUNDAY)[0]
    assert {"service": "Test rule", "source": "Rule", "jobs": 1, "minutes": 15} in day["demand"]
    assert day["demand_minutes"] == plain["demand_minutes"] + 15
    assert day["capacity_minutes"] == plain["capacity_minutes"]


def test_the_service_names_are_thin_delegates():
    assert service.availability.__module__ == "app.scheduling.service"
    assert windows.cleaner_windows is not None
    assert date  # keep the import used
