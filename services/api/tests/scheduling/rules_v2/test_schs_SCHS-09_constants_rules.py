"""SCHS-09: freeze hour, customer hour, unfreeze code and retry minutes come
from settings, not constants."""
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.directory.service import save_settings
from app.platform.clock import IST
from app.scheduling import automatic, rules
from app.scheduling.automatic import run_due
from app.scheduling.models import AutomaticPlanningRun
from tests.scheduling.test_automatic_planning import configure


def test_the_old_constants_are_gone():
    for name in ("FREEZE_HOUR", "CUSTOMER_HOUR", "UNFREEZE_CODE"):
        assert not hasattr(rules, name)


def test_seeded_hours_keep_the_old_behaviour():
    assert rules.freeze_deadline(date(2026, 10, 18)) == datetime(2026, 10, 17, 20, tzinfo=IST)
    assert rules.customer_deadline(date(2026, 10, 19)) == datetime(2026, 10, 18, 21, tzinfo=IST)


def test_an_explicit_hour_from_settings_wins():
    assert rules.freeze_deadline(date(2026, 10, 18), 18).hour == 18
    day = date(2026, 10, 19)
    assert rules.customer_can_change(day, datetime(2026, 10, 18, 21, 30, tzinfo=IST), 22)
    assert not rules.customer_can_change(day, datetime(2026, 10, 18, 22, 0, tzinfo=IST), 22)


def test_running_and_error_delays_use_the_settings(world, db, monkeypatch):
    configure(db, world)
    save_settings(db, None, {"scheduler.retry_minutes_running": 45,
                             "scheduler.retry_minutes_error": 11})
    seen = []
    from app.scheduling import service

    def capture(session, schedule, _):
        row = session.scalar(select(AutomaticPlanningRun))
        seen.append(row.next_attempt_at)
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "run_schedule", capture)
    now = datetime(2026, 10, 17, 18, tzinfo=IST)
    assert run_due(db, now)["errors"] == 1
    assert seen[0] - now == timedelta(minutes=45)
    row = db.scalar(select(AutomaticPlanningRun))
    assert row.status == "Error"
    assert row.next_attempt_at - now == timedelta(minutes=11)


def test_module_has_no_literal_retry_delay():
    import inspect
    assert "minutes=30" not in inspect.getsource(automatic)
    assert "minutes=5)" not in inspect.getsource(automatic)
