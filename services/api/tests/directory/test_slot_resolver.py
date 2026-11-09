"""P3-3 (ADM-SVS-12): the slot resolver on its own, with no database. An exception
replaces Root for its weekdays and dates only, and beats the weekly off on them;
Root applies everywhere else."""
import uuid
from datetime import date, timedelta

from app.directory import slot_resolver as sr

EXT, INT, SPA = "Cleaning-External", "Cleaning-Internal", "Deep Spa"
MONDAY = date(2026, 11, 9)
WEDNESDAY = MONDAY + timedelta(days=2)  # 11-Nov-26
THURSDAY = WEDNESDAY + timedelta(days=1)
ALL = range(7)
WORKING = [0, 1, 3, 4, 5, 6]  # Wednesday is the weekly off
EXCEPTION_ID = uuid.UUID(int=1)


def root(service, start, end, days):
    return sr.RootSlot(service, start, end, frozenset(days))


def exception(service, start, end, days, windows, exception_id=None):
    return sr.SlotException(service, start, end, frozenset(days), tuple(windows), exception_id)


def site(*rows, exceptions=()):
    return sr.SiteSlots(rows, exceptions)


def test_root_applies_when_no_exception_covers_the_day():
    s = site(root(EXT, 300, 660, ALL))
    eff = s.effective(EXT, WEDNESDAY)
    assert (eff.source, eff.windows, eff.exception_id) == (sr.ROOT, ((300, 660),), None)


def test_an_exception_replaces_root_for_its_weekdays_and_dates_only():
    ex = exception(EXT, MONDAY, MONDAY + timedelta(days=6), [0], [(420, 540)], EXCEPTION_ID)
    s = site(root(EXT, 300, 660, ALL), exceptions=[ex])
    eff = s.effective(EXT, MONDAY)
    assert (eff.source, eff.windows, eff.exception_id) == (sr.EXCEPTION, ((420, 540),), EXCEPTION_ID)
    # Tuesday is in the range but not one of the exception's weekdays: Root.
    assert s.effective(EXT, MONDAY + timedelta(days=1)).windows == ((300, 660),)
    # The Monday after the range: Root.
    assert s.effective(EXT, MONDAY + timedelta(days=7)).source == sr.ROOT


def test_an_exception_with_no_windows_closes_its_weekdays():
    s = site(root(EXT, 300, 660, ALL),
             exceptions=[exception(EXT, MONDAY, MONDAY + timedelta(days=6), [0], [])])
    assert s.effective(EXT, MONDAY).source == sr.EXCEPTION
    assert not s.effective(EXT, MONDAY).open
    assert not s.allows_demand(EXT, MONDAY)
    assert s.allows_demand(EXT, MONDAY + timedelta(days=1))


def test_wednesday_exception_makes_wednesday_a_working_day_for_its_range_only():
    end = WEDNESDAY + timedelta(days=6)
    s = site(root(EXT, 300, 660, WORKING),
             exceptions=[exception(EXT, WEDNESDAY, end, [2], [(300, 660)])])
    assert s.effective(EXT, WEDNESDAY).windows == ((300, 660),)
    assert s.effective(EXT, WEDNESDAY).source == sr.EXCEPTION
    # Outside the range the weekly off applies again.
    assert s.effective(EXT, WEDNESDAY + timedelta(days=7)).source == sr.WEEKLY_OFF
    assert s.effective(EXT, WEDNESDAY - timedelta(days=7)).source == sr.WEEKLY_OFF
    # The other days of the range keep Root.
    assert s.effective(EXT, THURSDAY).source == sr.ROOT


def test_the_exception_beats_the_weekly_off_on_its_dates_only():
    rows = [root(EXT, 300, 660, WORKING)]
    assert site(*rows).closed(WEDNESDAY)
    open_on_wednesday = site(
        *rows, exceptions=[exception(EXT, WEDNESDAY, WEDNESDAY, [2], [(300, 660)])])
    assert not open_on_wednesday.closed(WEDNESDAY)
    assert open_on_wednesday.closed(WEDNESDAY + timedelta(days=7))


def test_the_site_is_closed_only_when_no_service_is_open():
    s = site(root(EXT, 300, 660, WORKING), root(INT, 300, 660, ALL))
    assert not s.closed(WEDNESDAY)
    assert not s.effective(EXT, WEDNESDAY).open
    assert s.allows_demand(INT, WEDNESDAY)


def test_a_site_without_root_slots_has_no_weekly_off():
    assert not site().closed(WEDNESDAY)
    only_an_exception = site(exceptions=[exception(EXT, WEDNESDAY, WEDNESDAY, [2], [])])
    assert not only_an_exception.closed(WEDNESDAY)


def test_a_service_with_no_slot_is_not_filtered_but_has_no_window():
    s = site(root(EXT, 300, 660, WORKING))
    eff = s.effective(SPA, WEDNESDAY)
    assert eff.source == sr.NO_SLOTS and eff.windows == ()
    assert s.allows_demand(SPA, WEDNESDAY)


def test_a_root_weekday_with_no_slot_is_the_weekly_off_default():
    s = site(root(EXT, 300, 660, WORKING))
    eff = s.effective(EXT, WEDNESDAY)
    assert eff.source == sr.WEEKLY_OFF and not eff.open
    assert not s.allows_demand(EXT, WEDNESDAY)


def test_an_exception_for_one_service_does_not_change_another():
    s = site(root(EXT, 300, 660, ALL), root(INT, 300, 660, ALL),
             exceptions=[exception(INT, WEDNESDAY, WEDNESDAY, [2], [])])
    assert s.effective(EXT, WEDNESDAY).windows == ((300, 660),)
    assert s.effective(INT, WEDNESDAY).windows == ()


def test_root_windows_come_back_sorted_and_empty_ones_are_dropped():
    s = site(root(EXT, 1020, 1080, ALL), root(EXT, 300, 360, ALL), root(EXT, 500, 500, ALL))
    assert s.effective(EXT, WEDNESDAY).windows == ((300, 360), (1020, 1080))
