"""SCHS-49: the performance harness runs and prints solve seconds per site-day.

The full sizes (30, 60, 120 cars and a 7-day run) are slow and run only when
PRIVEO_BENCH is set. A small sample always runs.
"""
import os

import pytest

from scripts import bench_scheduler as bench


def test_the_harness_times_a_small_site_day_and_prints_the_table():
    rows = bench.run(sizes=(6,), week_cars=6, max_seconds=2)
    # the week run is shortened here by the size, not by the day count
    assert [r.cars for r in rows] == [6, 6] and rows[-1].days == bench.WEEK
    assert all(r.placed > 0 and r.seconds >= 0 for r in rows)
    table = bench.render(rows)
    assert "s/site-day" in table and "6 cars" in table and "7-day run" in table


def test_the_limit_comes_from_the_settings_and_covers_both_passes():
    from app.directory import settings_registry

    row = bench.bench(6, 1)
    assert row.limit == 2 * int(settings_registry.default_for("scheduler.solve_seconds"))


def test_generated_days_are_repeatable():
    first = bench.make_day(30, 7)
    again = bench.make_day(30, 7)
    assert [j.key for j in first[1]] == [j.key for j in again[1]]
    assert first[2] == again[2] and len(first[0]) == 5


def test_main_prints_and_returns_zero_when_within_the_limit(capsys):
    assert bench.main(["--cars", "6", "--seconds", "5"]) == 0
    assert "ok" in capsys.readouterr().out


@pytest.mark.skipif(not os.environ.get("PRIVEO_BENCH"), reason="slow: set PRIVEO_BENCH=1 to run")
def test_full_sizes_stay_within_the_limits():
    rows = bench.run()
    print("\n" + bench.render(rows))
    assert all(r.ok for r in rows)
