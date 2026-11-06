"""SCHS-50: the data script for live sites. Enabling story, no SCHR row.
The script is tested here against the test database only."""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.directory.models import AddonCatalogueItem, DirectoryService, Society, WorkingSlot
from app.directory.seed import seed_defaults
from app.identity.models import Login
from app.scheduling.models import SchedulingCrew

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "rules_v2_site_data.py"


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("rules_v2_site_data", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hours(wed_working=True):
    return [{"day": d, "working": (d != 2 or wed_working), "start": "05:00", "end": "11:00"}
            for d in range(7)]


@pytest.fixture
def site(engine):
    with Session(engine) as db:
        society = Society(name="Live Site")
        other = Society(name="Other Site")
        db.add_all([society, other])
        db.flush()
        for s in (society, other):
            for service in ("Cleaning-External", "Deep Spa"):
                db.add(WorkingSlot(society_id=s.id, service=service, start_minute=300,
                                   end_minute=660, days=list(range(7))))
        for n, (s, hours) in enumerate([(society, _hours()), (society, None), (other, _hours())]):
            login = Login(role="crew", login_id=f"9111{n:06d}", display_name=f"C{n}")
            db.add(login)
            db.flush()
            db.add(SchedulingCrew(login_id=login.id, society_id=s.id, working_hours=hours))
        seed_defaults(db)
        for svc in db.query(DirectoryService).filter(DirectoryService.name != "Deep Spa"):
            svc.duration_minutes = 20
        for item in db.query(AddonCatalogueItem):
            item.duration_minutes = 20
        db.commit()
    return engine


def test_dry_run_lists_every_change_and_saves_nothing(site, script):
    with Session(site) as db:
        plan = script.plan_site(db, script.find_site(db, "Live Site"))
        text = script.render(plan, apply=False)
        db.rollback()
    kinds = sorted(c.table for c in plan.changes)
    assert kinds == ["scheduling_crew", "working_slots", "working_slots"]
    assert "DRY RUN" in text and "changes: 3" in text
    assert len(plan.skipped) == 1
    with Session(site) as db:
        assert all(2 in s.days for s in db.query(WorkingSlot))


def test_apply_removes_wednesday_for_that_site_only(site, script):
    with Session(site) as db:
        plan = script.plan_site(db, script.find_site(db, "Live Site"))
        script.apply_changes(db, plan.changes)
        db.commit()
    with Session(site) as db:
        mine = {s.society_id: s for s in db.query(WorkingSlot)}
        live = db.query(Society).filter_by(name="Live Site").one()
        for slot in db.query(WorkingSlot):
            assert (2 in slot.days) == (slot.society_id != live.id)
        crew = db.query(SchedulingCrew).filter_by(society_id=live.id).all()
        with_hours = [c for c in crew if c.working_hours]
        assert with_hours[0].working_hours[2]["working"] is False
        assert with_hours[0].working_hours[3]["working"] is True
        other = db.query(SchedulingCrew).filter(SchedulingCrew.society_id != live.id).one()
        assert other.working_hours[2]["working"] is True
        assert mine


def test_applying_twice_changes_nothing(site, script):
    for _ in range(2):
        with Session(site) as db:
            plan = script.plan_site(db, script.find_site(db, "Live Site"))
            script.apply_changes(db, plan.changes)
            db.commit()
    with Session(site) as db:
        assert script.plan_site(db, script.find_site(db, "Live Site")).changes == []
        assert script.plan_durations(db).changes
        script.apply_changes(db, script.plan_durations(db).changes)
        db.commit()
        assert script.plan_durations(db).changes == []


def test_durations_20_to_30_and_deep_spa_untouched(site, script):
    with Session(site) as db:
        plan = script.plan_durations(db)
        assert len(plan.changes) == 4
        script.apply_changes(db, plan.changes)
        db.commit()
        got = {s.name: s.duration_minutes for s in db.query(DirectoryService)}
        assert got == {"Cleaning-External": 30, "Cleaning-Internal": 30, "Deep Spa": 120}
        assert {a.duration_minutes for a in db.query(AddonCatalogueItem)
                if a.name in script.DURATION_ADDONS} == {30}


def test_reversible_from_the_printout(site, script):
    with Session(site) as db:
        before_slots = sorted((str(s.id), list(s.days)) for s in db.query(WorkingSlot))
        plan = script.plan_site(db, script.find_site(db, "Live Site"))
        dur = script.plan_durations(db)
        text = script.render(plan, apply=True) + "\n" + script.render(dur, apply=True)
        script.apply_changes(db, plan.changes + dur.changes)
        db.commit()
    first = script.read_printout(text.split("SAVED", 2)[1])
    second = script.read_printout("SAVED" + text.split("SAVED", 2)[2])
    with Session(site) as db:
        script.apply_changes(db, first + second, reverse=True)
        db.commit()
    with Session(site) as db:
        assert sorted((str(s.id), list(s.days)) for s in db.query(WorkingSlot)) == before_slots
        assert script.plan_durations(db).changes and len(script.plan_durations(db).changes) == 4
        crew = [c for c in db.query(SchedulingCrew) if c.working_hours]
        assert len(crew) == 2 and all(c.working_hours[2]["working"] for c in crew)
