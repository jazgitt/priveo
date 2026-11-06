"""SCHS-35: the break is drawn in the crew day and on the Board as a block that holds
no job (SCHR-BRK-09). Version 2 only."""
from app.directory import lookup, rule_seed, site_settings
from app.directory.models import WorkingSlot
from app.scheduling import capacity, service
from app.scheduling.models import BreakRule
from tests.scheduling.conftest import SUNDAY


def _site(world, version=2, end=660, role="Member", paired=None):
    member = world.add_crew(start=300, end=end, role=role, paired=paired)
    for name in ("Cleaning-External", "Cleaning-Internal", "Deep Spa"):
        world.db.add(WorkingSlot(society_id=world.society.id, service=name,
                                 start_minute=300, end_minute=end, days=list(range(7))))
    world.db.commit()
    rule_seed.seed_rule_keys(world.db)
    site_settings.write(world.db, world.society.id, "scheduler.rules_version", version, None)
    lookup.invalidate()
    return member


def test_schr_brk_09_the_crew_day_carries_the_break_at_the_cleaners_break_time(world):
    member = _site(world)
    day = service.crew_day(world.db, member.login_id, SUNDAY)
    assert day["day_break"] == {"start_time": "09:30", "end_time": "10:00"}


def test_schr_brk_09_a_date_rule_moves_the_break(world):
    member = _site(world)
    world.db.add(BreakRule(society_id=world.society.id, crew_id=member.id, start_date=SUNDAY,
                           end_date=SUNDAY, start_minute=600, end_minute=630))
    world.db.commit()
    assert service.crew_day(world.db, member.login_id, SUNDAY)["day_break"] == {
        "start_time": "10:00", "end_time": "10:30"}


def test_schr_brk_09_a_cleaner_without_a_break_shows_none(world):
    member = _site(world, end=540)  # the shift ends before 09:30
    assert service.crew_day(world.db, member.login_id, SUNDAY)["day_break"] is None


def test_schr_brk_09_nothing_is_drawn_at_rules_version_1(world):
    member = _site(world, version=1)
    assert service.crew_day(world.db, member.login_id, SUNDAY)["day_break"] is None


def test_schr_brk_09_a_trainee_shows_the_members_break(world):
    boss = _site(world)
    trainee = world.add_crew(role="Trainee", paired=boss.id, name="Tara")
    world.db.commit()
    assert service.crew_day(world.db, trainee.login_id, SUNDAY)["day_break"] == {
        "start_time": "09:30", "end_time": "10:00"}


def test_schr_brk_09_the_board_availability_carries_the_break_minutes(world):
    member = _site(world)
    row = capacity.capacity(world.db, world.society.id, SUNDAY, SUNDAY)[0]["availability"][0]
    assert row["crew_id"] == member.id
    assert (row["break_start"], row["break_end"]) == (570, 600)
