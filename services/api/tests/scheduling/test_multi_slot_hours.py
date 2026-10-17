"""A crew member can work more than one slot in a day, for example 05:00 to
13:00 and 17:00 to 19:00 (ADM-CRW-25)."""
import uuid
from datetime import date
from types import SimpleNamespace

from app.scheduling import rules
from app.scheduling.service import (
    availability,
    base_crew,
    crew_key_for,
    fits_a_window,
    solver_crews,
)
from app.scheduling.solver import SolverJob, solve_day

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def hours(**monday_extra):
    out = [{"day": d, "working": d != "Sunday", "start": "05:00" if d != "Sunday" else "",
            "end": "13:00" if d != "Sunday" else "", "extra_slots": []} for d in DAYS]
    out[0]["extra_slots"] = [{"start": "17:00", "end": "19:00"}]
    return out


def test_a_day_with_two_slots_has_two_windows():
    h = hours()
    assert rules.hours_windows(h, 0, 0, 0) == [(300, 780), (1020, 1140)]
    assert rules.hours_windows(h, 1, 0, 0) == [(300, 780)]  # one slot
    assert rules.hours_windows(h, 6, 0, 0) == []  # Sunday is off
    # Old records have no per-weekday hours: the single window applies.
    assert rules.hours_windows(None, 2, 360, 660) == [(360, 660)]
    # Old records with seven days but no extra_slots still work.
    legacy = [{"day": d, "working": True, "start": "06:00", "end": "12:00"} for d in DAYS]
    assert rules.hours_windows(legacy, 3, 0, 0) == [(360, 720)]


def test_exceptions_apply_to_every_window():
    wins = [(300, 780), (1020, 1140)]
    assert rules.windows_for("Member", wins, None, None) == wins
    assert rules.windows_for("Member", wins, "Sick", None) == []
    assert rules.windows_for("Member", wins, "Leave", None) == []
    assert rules.windows_for("Trainee", wins, None, None) == []
    # A late start at 10:00 shortens the first window only.
    assert rules.windows_for("Member", wins, "Late start", 600) == [(600, 780), (1020, 1140)]
    # A late start at 14:00 drops the morning window and keeps the evening one.
    assert rules.windows_for("Member", wins, "Late start", 840) == [(1020, 1140)]


def test_availability_lists_each_window_and_capacity_adds_them(db):
    cid = uuid.uuid4()
    crew = SimpleNamespace(id=cid, role="Member", working_hours=hours(),
                           start_minute=300, end_minute=1140)
    monday, tuesday = date(2026, 10, 19), date(2026, 10, 20)
    out = availability(db, {cid: crew}, [monday, tuesday])
    assert out[monday][cid] == [(300, 780), (1020, 1140)]
    assert out[tuesday][cid] == [(300, 780)]
    assert sum(e - s for s, e in out[monday][cid]) == 600  # 8 h + 2 h


def test_a_job_must_fit_inside_one_window():
    wins = [(300, 780), (1020, 1140)]
    assert fits_a_window(wins, 1020, 20) and fits_a_window(wins, 300, 20)
    assert not fits_a_window(wins, 770, 20)  # runs past the first window
    assert not fits_a_window(wins, 800, 20)  # in the gap
    assert not fits_a_window(None, 300, 20)


def test_solver_uses_both_windows_of_one_crew_member():
    cid = uuid.uuid4()
    day_windows = {cid: [(300, 320), (600, 620)]}  # two 20-minute windows
    jobs = [SolverJob(f"j{i}", f"v{i}", 20, None, None, ((300, 700),)) for i in range(3)]
    result = solve_day(solver_crews(day_windows), jobs)
    assert len(result.placed) == 2 and len(result.unplaced) == 1
    starts = sorted(start for _key, start in result.placed.values())
    assert starts == [300, 600]
    assert {base_crew(key) for key, _start in result.placed.values()} == {cid}


def test_a_kept_job_stays_in_the_window_it_was_in():
    cid = uuid.uuid4()
    wins = [(300, 780), (1020, 1140)]
    assert crew_key_for(cid, 1030, wins) == f"{cid}|1"
    assert crew_key_for(cid, 310, wins) == f"{cid}|0"
    job = SolverJob("j", "v", 20, None, (crew_key_for(cid, 1030, wins), 1030), None)
    result = solve_day(solver_crews({cid: wins}), [job])
    assert result.placed["j"] == (f"{cid}|1", 1030)
