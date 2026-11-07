"""SCHS-11: a Draft re-run gives unfrozen Scheduled jobs the new duration."""
from sqlalchemy import select

from app.directory import lookup
from app.directory.models import DirectoryService
from app.directory.seed import seed_defaults
from app.scheduling import service
from app.scheduling.models import Job, Schedule
from tests.scheduling.builders import EXTERNAL, INTERNAL, Scenario
from tests.scheduling.conftest import SUNDAY


def _set_duration(db, name: str, minutes: int) -> None:
    row = db.scalar(select(DirectoryService).where(DirectoryService.name == name))
    if row is None:
        seed_defaults(db)
        db.flush()
        row = db.scalar(select(DirectoryService).where(DirectoryService.name == name))
    row.duration_minutes = minutes
    db.commit()
    lookup.invalidate()


def _scenario(world):
    sc = Scenario(world)
    sc.slots()
    sc.cleaner("Ravi", shift=(360, 840))
    sc.car(interior_day="Sunday")
    return sc


def _lengths(db) -> dict[str, set[int]]:
    db.expire_all()
    out: dict[str, set[int]] = {}
    for job in db.scalars(select(Job)):
        out.setdefault(job.service, set()).add(job.duration_minutes)
    return out


def test_draft_rerun_gives_unfrozen_scheduled_jobs_the_new_length(world):
    sc = _scenario(world)
    sc.run(SUNDAY)
    assert _lengths(world.db) == {EXTERNAL: {30}, INTERNAL: {30}}
    _set_duration(world.db, EXTERNAL, 45)
    sc.run(SUNDAY)
    assert _lengths(world.db) == {EXTERNAL: {45}, INTERNAL: {30}}


def test_new_jobs_get_the_new_length(world):
    sc = _scenario(world)
    _set_duration(world.db, EXTERNAL, 45)
    sc.run(SUNDAY)
    assert _lengths(world.db)[EXTERNAL] == {45}


def test_frozen_schedule_keeps_its_length(world):
    sc = _scenario(world)
    sc.run(SUNDAY)
    schedule = world.db.scalar(select(Schedule))
    service.freeze(world.db, schedule, None)
    _set_duration(world.db, EXTERNAL, 45)
    sc.run(SUNDAY)
    assert _lengths(world.db) == {EXTERNAL: {30}, INTERNAL: {30}}


def test_started_jobs_keep_their_length(world):
    sc = _scenario(world)
    sc.run(SUNDAY)
    job = world.db.scalar(select(Job).where(Job.service == EXTERNAL))
    job.status = "In progress"
    world.db.commit()
    _set_duration(world.db, EXTERNAL, 45)
    sc.run(SUNDAY)
    assert _lengths(world.db)[EXTERNAL] == {30}

