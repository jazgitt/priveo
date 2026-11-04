"""The scheduled-job switch, the run record and the admin view (ADM-OPS-05 to ADM-OPS-09)."""
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory.models import DirectoryAudit
from app.notifications import cron, cron_log
from app.notifications.cron import CronSettings, get_cron_settings
from app.notifications.models import CronJob, CronRun
from tests.test_api import auth, login

VERCEL = Path(__file__).resolve().parents[2] / "vercel.json"
H = {"Authorization": "Bearer s3cret"}
ADMIN_PATH = "/v1/admin/operations/cron"


@pytest.fixture(autouse=True)
def quiet_payments(monkeypatch):
    """The seed has subscriptions; the real job would make payments for them."""
    monkeypatch.setitem(cron.JOBS, "payments-daily",
                        lambda *_: {"created": 0, "marked_overdue": 0, "inactivated": 0})


@pytest.fixture
def api(client):
    client.app.dependency_overrides[get_cron_settings] = lambda: CronSettings(cron_secret="s3cret")
    return client


@pytest.fixture
def admin(api):
    return auth(login(api, "admin")["access_token"])


def runs(db, job=None):
    db.expire_all()
    q = select(CronRun).order_by(CronRun.started_at)
    if job:
        q = q.where(CronRun.job == job)
    return list(db.scalars(q))


def enable(db, job, on=True):
    cron_log.set_enabled(db, job, on, None)
    db.commit()


# ---- defaults and the switch ---------------------------------------------------

def test_the_defaults_are_the_owners(db):
    assert cron_log.DEFAULTS == {
        "complaints-overdue": True, "payments-daily": True, "freeze-due": False,
        "automatic-planning": False, "renewal-reminders": False, "checkin-notify": False,
        "mani-retention": False}
    for job, on in cron_log.DEFAULTS.items():
        assert cron_log.is_enabled(db, job) is on


def test_a_disabled_job_does_nothing_and_is_recorded_as_skipped(api, db):
    r = api.get("/v1/internal/cron/freeze-due", headers=H)
    assert r.status_code == 200
    body = r.json()
    assert body["skipped"] == "disabled" and body["job"] == "freeze-due" and "result" not in body
    assert "ran_at" in body
    [run] = runs(db)
    assert run.status == "skipped" and run.result == {"skipped": "disabled"}


def test_an_enabled_job_runs_and_is_recorded(api, db):
    r = api.get("/v1/internal/cron/payments-daily", headers=H)
    assert r.status_code == 200 and r.json()["result"] == {
        "created": 0, "marked_overdue": 0, "inactivated": 0}
    [run] = runs(db)
    assert run.status == "success" and run.trigger == "manual" and run.duration_ms is not None
    assert run.finished_at is not None and run.error == ""
    r = api.get("/v1/internal/cron/payments-daily", headers={**H, "User-Agent": "vercel-cron/1.0"})
    assert runs(db)[-1].trigger == "vercel"


def test_an_unknown_job_is_404_and_not_recorded(api, db):
    assert api.get("/v1/internal/cron/nope", headers=H).status_code == 404
    assert runs(db) == []


def test_the_removed_jobs_are_gone(api):
    for job in ("crew-society-moves", "payments-generate", "payments-overdue"):
        assert job not in cron.JOBS
        assert api.get(f"/v1/internal/cron/{job}", headers=H).status_code == 404


# ---- the recorder --------------------------------------------------------------

def test_a_failing_job_keeps_the_error_and_the_status_code(api, db, monkeypatch):
    def boom(*_):
        raise RuntimeError("secret stack detail\nline two")

    monkeypatch.setitem(cron.JOBS, "payments-daily", boom)
    from fastapi.testclient import TestClient
    quiet = TestClient(api.app, raise_server_exceptions=False)
    r = quiet.get("/v1/internal/cron/payments-daily", headers=H)
    assert r.status_code == 500
    [run] = runs(db)
    assert run.status == "failed" and run.error == "RuntimeError: secret stack detail line two"
    assert "Traceback" not in run.error and run.finished_at is not None


def test_a_recorder_fault_never_breaks_the_job(api, db, monkeypatch, caplog):
    def broken(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(cron_log, "Session", broken)
    with caplog.at_level(logging.WARNING, logger="priveo.cron"):
        r = api.get("/v1/internal/cron/payments-daily", headers=H)
    assert r.status_code == 200 and "result" in r.json()
    assert any(rec.levelno == logging.WARNING for rec in caplog.records)


def test_one_log_line_for_each_run(api, caplog):
    with caplog.at_level(logging.INFO, logger="priveo.cron"):
        api.get("/v1/internal/cron/payments-daily", headers=H)
    lines = [r.getMessage() for r in caplog.records if r.name == "priveo.cron"]
    assert len(lines) == 1
    assert lines[0].startswith("cron job=payments-daily trigger=manual status=success duration_ms=")
    assert 'result={"created":0,"marked_overdue":0,"inactivated":0}' in lines[0]


def test_the_cron_logger_has_a_stdout_handler():
    cron_log.configure_logging()
    log = logging.getLogger("priveo.cron")
    assert log.level == logging.INFO and any(getattr(h, "_priveo_cron", False) for h in log.handlers)
    assert logging.getLogger().level != logging.INFO


def test_timed_out_is_worked_out_on_read():
    now = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    run = CronRun(job="x", trigger="vercel", status="started", started_at=now - timedelta(minutes=7))
    assert cron_log.run_status(run, now) == "Timed out"
    run.started_at = now - timedelta(minutes=2)
    assert cron_log.run_status(run, now) == "Running"


def test_status_words():
    now = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)

    def run(status, result=None):
        return CronRun(job="x", trigger="vercel", status=status, started_at=now, result=result)

    assert cron_log.run_status(None, now) == "Never run"
    assert cron_log.run_status(run("success", {"sent": 2}), now) == "Success"
    assert cron_log.run_status(run("success", {"sent": 0, "errors": 0}), now) == "Did nothing"
    assert cron_log.run_status(run("failed"), now) == "Failed"
    assert cron_log.run_status(run("skipped"), now) == "Skipped"


def test_late_needs_an_enabled_scheduled_job_with_no_run_since_the_expected_time():
    now = datetime(2026, 11, 5, 23, 0, tzinfo=UTC)  # payments-daily expected 20:30
    old = CronRun(job="payments-daily", trigger="vercel", status="success",
                  started_at=datetime(2026, 11, 4, 20, 40, tzinfo=UTC), result={"created": 1})
    assert cron_log.job_status("payments-daily", True, old, True, now) == "Late"
    assert cron_log.job_status("payments-daily", True, old, True,
                               datetime(2026, 11, 5, 21, 30, tzinfo=UTC)) == "Success"  # inside grace
    assert cron_log.job_status("payments-daily", False, old, True, now) == "Disabled"
    assert cron_log.job_status("mani-retention", True, old, True, now) == "Success"  # not scheduled


def test_old_rows_are_pruned_after_90_days(api, db):
    now = datetime.now(UTC)
    db.add_all([CronRun(job="x", trigger="vercel", status="success", started_at=now - timedelta(days=91)),
                CronRun(job="x", trigger="vercel", status="success", started_at=now - timedelta(days=89))])
    db.commit()
    api.get("/v1/internal/cron/payments-daily", headers=H)
    assert len(runs(db, "x")) == 1


# ---- the schedule mirror -------------------------------------------------------

def test_expected_equals_vercel_json():
    crons = {c["path"].rsplit("/", 1)[1]: c["schedule"] for c in json.loads(VERCEL.read_text())["crons"]}
    assert crons == cron_log.EXPECTED
    for job in crons:
        assert job in cron.JOBS


# ---- the admin API -------------------------------------------------------------

def test_only_the_admin_can_see_or_switch(api, admin):
    assert api.get(ADMIN_PATH).status_code == 401
    assert api.put(f"{ADMIN_PATH}/freeze-due", json={"enabled": True}).status_code == 401
    for role in ("customer", "crew"):
        h = auth(login(api, role)["access_token"])
        assert api.get(ADMIN_PATH, headers=h).status_code == 403
        assert api.get(f"{ADMIN_PATH}/freeze-due/runs", headers=h).status_code == 403
        assert api.put(f"{ADMIN_PATH}/freeze-due", headers=h, json={"enabled": True}).status_code == 403
    assert api.get(ADMIN_PATH, headers=admin).status_code == 200


def test_the_list_shows_every_job(api, admin, db):
    api.get("/v1/internal/cron/payments-daily", headers=H)
    rows = {r["job"]: r for r in api.get(ADMIN_PATH, headers=admin).json()}
    assert set(rows) == set(cron_log.DEFAULTS)
    pay = rows["payments-daily"]
    assert pay["enabled"] and pay["scheduled_on_vercel"] and pay["status"] == "Did nothing"
    assert pay["schedule_ist"] == "Daily at 02:00 IST (next day)" and pay["schedule_utc"] == "Daily at 20:30 UTC"
    assert pay["last_run"]["what_it_did"] == "Made 0 payments, marked 0 over due, made 0 subscriptions Inactive."
    assert pay["purpose_achieved"] is True
    assert rows["freeze-due"]["status"] == "Disabled" and rows["freeze-due"]["last_run"] is None
    assert rows["mani-retention"]["scheduled_on_vercel"] is False
    assert rows["renewal-reminders"]["purpose_achieved"] is None


def test_the_runs_list_and_its_limit(api, admin):
    for _ in range(3):
        api.get("/v1/internal/cron/payments-daily", headers=H)
    assert len(api.get(f"{ADMIN_PATH}/payments-daily/runs", headers=admin).json()) == 3
    assert len(api.get(f"{ADMIN_PATH}/payments-daily/runs?limit=2", headers=admin).json()) == 2
    assert api.get(f"{ADMIN_PATH}/nope/runs", headers=admin).status_code == 404


def test_the_switch_changes_the_job_and_writes_an_audit_row(api, admin, db):
    r = api.put(f"{ADMIN_PATH}/freeze-due", headers=admin, json={"enabled": True})
    assert r.status_code == 200 and r.json()["enabled"] is True
    assert db.get(CronJob, "freeze-due").enabled is True
    assert "result" in api.get("/v1/internal/cron/freeze-due", headers=H).json()
    api.put(f"{ADMIN_PATH}/freeze-due", headers=admin, json={"enabled": False})
    db.expire_all()
    audits = list(db.scalars(select(DirectoryAudit).where(DirectoryAudit.entity == "cron_job")
                             .order_by(DirectoryAudit.at)))
    assert [a.detail for a in audits] == [{"enabled": [False, True]}, {"enabled": [True, False]}]
    assert audits[0].entity_id == "freeze-due" and audits[0].admin_login_id is not None
    # Setting the same value again writes no new row.
    api.put(f"{ADMIN_PATH}/freeze-due", headers=admin, json={"enabled": False})
    assert len(list(db.scalars(select(DirectoryAudit).where(DirectoryAudit.entity == "cron_job")))) == 2
    assert api.put(f"{ADMIN_PATH}/nope", headers=admin, json={"enabled": True}).status_code == 404


# ---- the migration -------------------------------------------------------------

def test_the_migration_seeds_the_defaults_and_moves_the_old_setting(tmp_path):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from app.platform.db import make_engine

    url = f"sqlite:///{tmp_path / 'm.db'}"
    config = Config("alembic.ini")
    config.cmd_opts = type("Opts", (), {"x": [f"url={url}"]})()
    command.upgrade(config, "0048")
    engine = make_engine(url)
    with engine.begin() as c:
        c.execute(text("INSERT INTO system_settings (key, value, updated_at) "
                       "VALUES ('schedule.auto_enabled', '1', '2026-11-01 00:00:00')"))
    command.upgrade(config, "head")
    with Session(engine) as s:
        rows = {r.job: r.enabled for r in s.scalars(select(CronJob))}
        gone = s.execute(text("SELECT count(*) FROM system_settings "
                              "WHERE key='schedule.auto_enabled'")).scalar()
    assert rows == {**cron_log.DEFAULTS, "automatic-planning": True}  # the admin's 1 is kept
    assert gone == 0
    engine.dispose()
