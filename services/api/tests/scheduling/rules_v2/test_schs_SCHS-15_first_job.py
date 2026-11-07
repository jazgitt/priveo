"""SCHS-15: the first-job floor, the reporting time and the crew override."""
from app.directory import lookup, rule_seed, site_settings
from app.scheduling import crew_rules, service
from app.scheduling.models import SchedulingCrewException
from tests.scheduling.conftest import SUNDAY


def _site(world, start=300, end=660, **crew_fields):
    member = world.add_crew(start=start, end=end)
    for k, v in crew_fields.items():
        setattr(member, k, v)
    world.db.commit()
    rule_seed.seed_rule_keys(world.db)
    lookup.invalidate()
    return member


def _start(world, member):
    crew = service.load_crew(world.db, world.society.id)
    return service.availability(world.db, crew, [SUNDAY])[SUNDAY][member.id][0][0]


def _set_site(world, key, value):
    site_settings.write(world.db, world.society.id, key, value, None)
    lookup.invalidate()


def test_schr_par_04_default_first_job_is_0530_for_a_window_opening_at_0500(world):
    assert _start(world, _site(world)) == 330


def test_schr_hard_04_a_window_opening_after_the_floor_keeps_its_own_start(world):
    assert _start(world, _site(world, start=360)) == 360


def test_schr_par_04_a_window_ending_before_the_floor_is_dropped(world):
    member = _site(world, start=300, end=320)
    crew = service.load_crew(world.db, world.society.id)
    assert service.availability(world.db, crew, [SUNDAY])[SUNDAY].get(member.id) is None


def test_schr_par_04_the_crew_value_overrides_the_site_value(world):
    member = _site(world, first_job_minute=345)
    assert _start(world, member) == 345
    assert crew_rules.first_job_minute(world.db, member) == 345


def test_schr_par_05_clearing_the_crew_value_returns_to_the_site_value(world):
    member = _site(world, first_job_minute=345)
    member.first_job_minute = None
    world.db.commit()
    assert _start(world, member) == 330


def test_schr_par_05_a_crew_without_override_follows_a_later_site_change(world):
    member = _site(world)
    _set_site(world, "site.first_job_minute", 340)
    assert _start(world, member) == 340


def test_schr_par_04_reporting_time_is_recorded_and_not_a_job_floor(world):
    member = _site(world)
    assert crew_rules.reporting_minute(world.db, member) == 300
    _set_site(world, "site.reporting_minute", 330)
    assert crew_rules.reporting_minute(world.db, member) == 330
    assert _start(world, member) == 330
    member.reporting_minute = 345
    world.db.commit()
    assert crew_rules.reporting_minute(world.db, member) == 345
    assert _start(world, member) == 330


def test_schr_hard_04_a_late_start_after_the_floor_still_moves_the_start(world):
    member = _site(world)
    world.db.add(SchedulingCrewException(crew_id=member.id, on_date=SUNDAY,
                                         kind="Late start", from_minute=400))
    world.db.commit()
    assert _start(world, member) == 400


def test_schr_hard_04_a_late_start_before_the_floor_does_not_lower_it(world):
    member = _site(world)
    world.db.add(SchedulingCrewException(crew_id=member.id, on_date=SUNDAY,
                                         kind="Late start", from_minute=310))
    world.db.commit()
    assert _start(world, member) == 330

