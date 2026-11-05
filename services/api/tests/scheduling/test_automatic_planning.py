from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.directory.models import Society
from app.directory.service import save_settings
from app.platform.clock import IST
from app.scheduling import service
from app.scheduling.automatic import next_period, run_due
from app.scheduling.models import AutomaticPlanningRun, Schedule
from app.support.models import AdminAlert


def configure(db, world):
    # `world` flushed its rows in its own session. A second session sees them on
    # PostgreSQL only once they are committed (SQLite shares one connection).
    world.db.commit()
    for society in db.scalars(select(Society)):
        society.active = society.id == world.society.id
    db.commit()
    save_settings(db, None, {'schedule.auto_time': '18:00', 'schedule.period': 'Daily'})


def test_only_admin_can_save_the_planning_time(api, admin):
    from tests.test_api import auth, login
    path = '/v1/admin/scheduling/automatic-planning'
    assert api.get(path, headers=admin).json() == {'time_ist': ''}
    assert api.put(path, headers=auth(login(api, 'customer')['access_token']),
                   json={'time_ist': '18:00'}).status_code == 403
    assert api.put(path, headers=admin, json={'time_ist': '18:00'}).status_code == 200
    assert api.get(path, headers=admin).json() == {'time_ist': '18:00'}


def test_the_switch_needs_a_time_and_the_time_cannot_be_cleared_while_on(api, admin):
    switch = '/v1/admin/operations/cron/automatic-planning'
    time_path = '/v1/admin/scheduling/automatic-planning'
    assert api.put(switch, headers=admin, json={'enabled': True}).status_code == 422
    api.put(time_path, headers=admin, json={'time_ist': '18:00'})
    assert api.put(switch, headers=admin, json={'enabled': True}).status_code == 200
    assert api.put(time_path, headers=admin, json={'time_ist': ''}).status_code == 422


def test_without_a_time_planning_is_not_due(world, db):
    assert run_due(db, datetime(2026, 10, 17, 19, tzinfo=IST))['not_due']


def test_draft_is_created_after_ist_time_once_and_never_frozen(world, db):
    configure(db, world)
    now = datetime(2026, 10, 17, 18, tzinfo=IST)
    assert run_due(db, now - timedelta(minutes=1))['not_due']
    assert run_due(db, now)['planned'] == 1
    assert run_due(db, now + timedelta(minutes=1))['planned'] == 0
    schedule = db.scalar(select(Schedule).where(Schedule.society_id == world.society.id))
    assert schedule.status == 'Draft' and schedule.start_date == date(2026, 10, 18)
    assert db.scalar(select(AutomaticPlanningRun)).attempts == 1


def test_existing_manual_schedule_is_preserved(world, db, monkeypatch):
    configure(db, world)
    schedule = service.get_or_create_schedule(db, world.society.id, date(2026, 10, 18), 1)
    db.commit()
    def fail(*_):
        raise AssertionError('must not rerun a manually created schedule')
    monkeypatch.setattr(service, 'run_schedule', fail)
    assert run_due(db, datetime(2026, 10, 17, 18, tzinfo=IST))['planned'] == 0
    assert db.scalar(select(AutomaticPlanningRun)).schedule_id == schedule.id


def test_failure_alerts_and_retries_same_draft(world, db, monkeypatch):
    configure(db, world)
    real = service.run_schedule
    def fail(*_):
        raise RuntimeError('solver unavailable')
    monkeypatch.setattr(service, 'run_schedule', fail)
    now = datetime(2026, 10, 17, 18, tzinfo=IST)
    assert run_due(db, now)['errors'] == 1
    row = db.scalar(select(AutomaticPlanningRun))
    draft_id = row.schedule_id
    assert row.status == 'Error' and db.scalar(select(AdminAlert).where(AdminAlert.kind == 'planning_error'))
    assert run_due(db, now + timedelta(minutes=1))['planned'] == 0
    monkeypatch.setattr(service, 'run_schedule', real)
    assert run_due(db, now + timedelta(minutes=5))['planned'] == 1
    assert db.scalar(select(AutomaticPlanningRun)).schedule_id == draft_id


def test_next_period_handles_week_and_year_and_leap_month():
    assert next_period(date(2026, 10, 18), 'Weekly', 6) == (date(2026, 10, 25), 7)
    assert next_period(date(2026, 12, 31), 'Monthly', 6) == (date(2027, 1, 1), 31)
    assert next_period(date(2028, 1, 30), 'Monthly', 6) == (date(2028, 2, 1), 29)
