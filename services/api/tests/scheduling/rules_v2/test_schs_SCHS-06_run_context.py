"""SCHS-06: the run context, the hook points and the settings snapshot."""
import contextlib
import shutil
import sys
import textwrap
from pathlib import Path

import pytest
from sqlalchemy import select

from app.directory import lookup, site_settings
from app.scheduling import hooks, run_context, service
from app.scheduling.models import Job, ScheduleFinding, ScheduleRunConfig
from tests.scheduling.conftest import SUNDAY

SCHEDULING = Path(service.__file__).parent
FOLDERS = ("hook_handlers", "job_sync", "demand_providers", "post_solve", "routes")


@contextlib.contextmanager
def dropped(folder: str, name: str, body: str):
    """A module file dropped into a hook folder, removed afterwards."""
    path = SCHEDULING / folder / f"{name}.py"
    path.write_text(textwrap.dedent(body))
    try:
        yield
    finally:
        path.unlink(missing_ok=True)
        shutil.rmtree(SCHEDULING / folder / "__pycache__", ignore_errors=True)
        sys.modules.pop(f"app.scheduling.{folder}.{name}", None)


@pytest.fixture
def calls(monkeypatch):
    log: list = []
    monkeypatch.setattr(hooks, "test_calls", log, raising=False)
    return log


def _plan(world):
    world.add_crew()
    world.add_vehicle()
    world.db.commit()
    return service.get_or_create_schedule(world.db, world.society.id, SUNDAY, 7)


def _configs(world, schedule):
    return list(world.db.scalars(
        select(ScheduleRunConfig).where(ScheduleRunConfig.schedule_id == schedule.id)
        .order_by(ScheduleRunConfig.created_at, ScheduleRunConfig.id)))


def _names(folder):
    import importlib
    return [m.__name__.rsplit(".", 1)[1]
            for m in importlib.import_module(f"app.scheduling.{folder}").discover()]


@pytest.mark.parametrize("folder", FOLDERS)
def test_schr_cfg_07_a_file_dropped_in_a_folder_is_found_in_order(folder):
    base = _names(folder)  # real modules of the folder; later stories add to it
    body = "ORDER = {}\n"
    with dropped(folder, "zz_late", body.format(5)), dropped(folder, "aa_early", body.format(9)), \
            dropped(folder, "_skipped", body.format(1)):
        found = _names(folder)
        added = [n for n in found if n not in base]
        assert added == ["zz_late", "aa_early"]  # ORDER first, then name
        assert [n for n in found if n in base] == base
    assert _names(folder) == base


def test_schr_cfg_07_a_route_module_is_included_by_register(api):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.scheduling import register
    with dropped("routes", "ping", """
        from fastapi import APIRouter
        router = APIRouter()

        @router.get("/v1/schs06-ping")
        def ping():
            return {"ok": True}
    """):
        app = FastAPI()
        register(app)
        assert TestClient(app).get("/v1/schs06-ping").json() == {"ok": True}


def test_schr_cfg_08_run_stores_the_values_it_used(world, api, calls):
    schedule = _plan(world)
    body = """
        from app.scheduling import hooks
        def provide(ctx, demand):
            hooks.test_calls.append(("provide", ctx.setting("scheduler.grid_minutes")))
            return []
        def sync(ctx, job, item): hooks.test_calls.append("sync")
        def after_solve(ctx, day, items, result):
            hooks.test_calls.append("solve")
            ctx.add_finding("T", "found", items[0][0].id)
        def on_status_change(db, job, source): hooks.test_calls.append(("status", source, job.status))
    """
    with dropped("demand_providers", "t2", body), dropped("job_sync", "t2", body), \
            dropped("post_solve", "t2", body), dropped("hook_handlers", "t2", body):
        service.run_schedule(world.db, schedule, None)
        service.run_schedule(world.db, schedule, None)
        job = world.db.scalars(select(Job)).first()
        service.set_job_status(world.db, job.id, "Started")
    assert ("provide", 5) in calls and "sync" in calls and "solve" in calls
    assert ("status", "crew", "Started") in calls
    rows = _configs(world, schedule)
    assert len(rows) == 2
    assert rows[0].values == lookup.site_settings_all(world.db, world.society.id)
    findings = list(world.db.scalars(select(ScheduleFinding)))
    # Last run only: one finding of each kind and job. The Interior the ledger now
    # plans (SCHS-36) can add an unassigned-reason finding of its own.
    mine = [f for f in findings if f.code == "T"]
    assert mine and len({(f.code, f.job_id) for f in findings}) == len(findings)
    assert len({f.id for f in findings}) == len(findings)


def test_schr_cfg_07_a_setting_change_does_not_touch_past_snapshots_or_a_frozen_plan(world, api):
    schedule = _plan(world)
    service.run_schedule(world.db, schedule, None)
    first = _configs(world, schedule)[0].values["site.first_job_minute"]
    service.freeze(world.db, schedule, None)
    placed = {j.id: (j.crew_id, j.start_minute) for j in world.db.scalars(select(Job))}
    site_settings.write(world.db, world.society.id, "site.first_job_minute", first + 5, None)
    lookup.invalidate()
    world.db.expire_all()
    assert _configs(world, schedule)[0].values["site.first_job_minute"] == first
    assert {j.id: (j.crew_id, j.start_minute) for j in world.db.scalars(select(Job))} == placed
    service.run_schedule(world.db, schedule, None)  # a frozen schedule keeps its placements
    world.db.expire_all()
    assert {j.id: (j.crew_id, j.start_minute) for j in world.db.scalars(select(Job))} == placed
    rows = _configs(world, schedule)
    assert rows[0].values["site.first_job_minute"] == first
    assert rows[-1].values["site.first_job_minute"] == first + 5


def test_schr_cfg_08_status_hook_needs_a_handler(world, api, calls):
    schedule = _plan(world)
    service.run_schedule(world.db, schedule, None)
    job = world.db.scalars(select(Job)).first()
    body = """
        from app.scheduling import hooks
        def on_status_change(db, job, source): hooks.test_calls.append(source)
    """
    with dropped("hook_handlers", "t3", body):
        hooks.job_status_changed(world.db, job, "visit_skip")
    assert calls == ["visit_skip"]
    hooks.job_status_changed(world.db, job, "crew")  # no handler left
    assert calls == ["visit_skip"]


def test_schr_cfg_07_no_handlers_means_no_change_to_the_plan(world, api):
    schedule = _plan(world)
    service.run_schedule(world.db, schedule, None)
    # The ledger plans Interiors (SCHS-36), so only the
    # Exterior jobs are compared: the handlers change none of them.
    def plan():
        return {j.id: (j.crew_id, j.start_minute, j.status) for j in world.db.scalars(
            select(Job).where(Job.service == "Cleaning-External"))}

    before = plan()
    service.run_schedule(world.db, schedule, None)
    world.db.expire_all()
    assert plan() == before
    assert run_context.RunContext  # the context is part of the public seam
