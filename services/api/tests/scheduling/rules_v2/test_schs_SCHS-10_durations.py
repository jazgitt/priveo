"""SCHS-10: durations 30 / 30 / 120 come from the service table only."""
import inspect

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory import defaults, lookup
from app.directory.models import DirectoryService
from app.directory.seed import seed_defaults
from app.scheduling import models as scheduling_models
from app.scheduling import service
from app.scheduling.models import Job, Visit


def _seeded(engine):
    with Session(engine) as session:
        seed_defaults(session)
        session.commit()
        return {r.name: r.duration_minutes for r in session.scalars(select(DirectoryService))}


def test_schr_par_06_new_site_seeds_30_and_30(engine):
    rows = _seeded(engine)
    assert rows["Cleaning-External"] == 30
    assert rows["Cleaning-Internal"] == 30


def test_schr_par_07_deep_spa_keeps_120(engine):
    assert _seeded(engine)["Deep Spa"] == 120


def test_schr_par_06_existing_rows_are_not_changed_by_the_seed(engine):
    with Session(engine) as session:
        for order, name in enumerate(defaults.SERVICES):
            session.add(DirectoryService(name=name, duration_minutes=20, min_photos=2,
                                         min_videos=1, sort_order=order))
        session.commit()
        seed_defaults(session)
        session.commit()
        assert {r.duration_minutes for r in session.scalars(select(DirectoryService))
                if r.name != "Deep Spa"} == {20}


def test_schr_par_06_extra_addons_use_the_service_default_not_a_literal(db):
    for addon in defaults.EXTRA_ADDONS:
        assert addon["duration_minutes"] == defaults.DURATIONS[addon["service"]] == 30


def test_schr_hard_06_planner_has_no_duration_constant():
    assert not hasattr(scheduling_models, "DURATIONS")
    assert "DURATIONS" not in inspect.getsource(service)


def test_schr_hard_06_demand_duration_follows_the_service_table(world, run_week):
    world.add_crew(start=360, end=840)
    world.add_vehicle(interior_day="Sunday")
    world.db.commit()
    row = world.db.scalar(select(DirectoryService).where(
        DirectoryService.name == "Cleaning-External"))
    if row is None:
        seed_defaults(world.db)
        world.db.commit()
        row = world.db.scalar(select(DirectoryService).where(
            DirectoryService.name == "Cleaning-External"))
    row.duration_minutes = 45
    world.db.commit()
    lookup.invalidate()
    run_week(days=7)
    jobs = world.db.scalars(select(Job).where(Job.service == "Cleaning-External")).all()
    assert jobs and {j.duration_minutes for j in jobs} == {45}


def test_schr_ext_02_and_int_02_each_job_takes_exactly_30(world, run_week):
    world.add_crew(start=360, end=840)
    world.add_vehicle(interior_day="Sunday")
    world.db.commit()
    run_week(days=7)
    jobs = world.db.scalars(select(Job)).all()
    assert {j.service for j in jobs} >= {"Cleaning-External", "Cleaning-Internal"}
    assert {j.duration_minutes for j in jobs} == {30}


def test_schr_int_04_visit_with_both_services_is_60_minutes_of_work(world, run_week):
    from tests.scheduling.conftest import SUNDAY
    world.add_crew(start=360, end=840)
    world.add_vehicle(interior_day="Sunday")
    world.db.commit()
    run_week(days=7)
    visit = world.db.scalar(select(Visit).where(Visit.date == SUNDAY))
    jobs = world.db.scalars(select(Job).where(Job.visit_id == visit.id)).all()
    assert {j.service for j in jobs} == {"Cleaning-External", "Cleaning-Internal"}
    # Work is the two set durations: no travel minutes are added to either job.
    assert sum(j.duration_minutes for j in jobs) == 60
    placed = [j for j in jobs if j.start_minute is not None]
    assert len(placed) == 2
