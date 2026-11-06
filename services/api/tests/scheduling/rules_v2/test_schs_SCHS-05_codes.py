"""SCHS-05: one list of reason and finding codes, carried by the solver result."""

import re

from app.scheduling.codes import REASON_TEXT, ReasonCode
from app.scheduling.solver import SolverCrew, SolverJob, solve_day

TEN = {
    "no_cleaner",
    "shift_too_short",
    "weekly_off",
    "customer_cutoff",
    "capacity_short",
    "break_kept",
    "before_interior_earliest",
    "entitlement_used",
    "home_zone_full",
    "cross_zone",
}


def test_codes_cover_the_ten_cases_with_stable_strings():
    values = {c.value for c in ReasonCode}
    assert TEN <= values
    assert all(re.fullmatch(r"[a-z_]+", v) for v in values)
    assert len(values) == len(list(ReasonCode))


def test_schr_out_existing_texts_are_unchanged():
    assert REASON_TEXT[ReasonCode.NO_CLEANER] == "No crew member works that day."
    assert REASON_TEXT[ReasonCode.NO_SLOT] == "No working slot allows this service that day."
    assert REASON_TEXT[ReasonCode.SHIFT_TOO_SHORT] == "No crew member's hours are long enough for this job."
    assert REASON_TEXT[ReasonCode.NO_PLAN] == "The scheduler found no plan."
    assert REASON_TEXT[ReasonCode.CAPACITY_SHORT] == "Capacity is short for that day."
    assert ReasonCode.CROSS_ZONE.text is None


def test_schr_out_no_cleaner_carries_code_and_old_text():
    result = solve_day([], [SolverJob("a", "v", 20)])
    assert result.unplaced["a"] == "No crew member works that day."
    assert result.unplaced_codes["a"] == ReasonCode.NO_CLEANER


def test_schr_out_shift_too_short():
    result = solve_day([SolverCrew("a", 360, 420)], [SolverJob("spa", "v", 120)])
    assert result.unplaced["spa"] == "No crew member's hours are long enough for this job."
    assert result.unplaced_codes["spa"] == "shift_too_short"


def test_schr_out_no_slot():
    job = SolverJob("x", "v", 60, windows=((360, 400),))
    result = solve_day([SolverCrew("a", 360, 660)], [job])
    assert result.unplaced_codes["x"] == ReasonCode.NO_SLOT
    assert result.unplaced["x"] == REASON_TEXT[ReasonCode.NO_SLOT]


def test_schr_out_capacity_short_and_codes_match_every_unplaced_job():
    jobs = [SolverJob(f"j{i}", f"v{i}", 20) for i in range(8)]
    result = solve_day([SolverCrew("a", 360, 420)], jobs)
    assert result.unplaced
    assert set(result.unplaced_codes) == set(result.unplaced)
    assert all(c == ReasonCode.CAPACITY_SHORT for c in result.unplaced_codes.values())
    assert all(result.unplaced[k] == "Capacity is short for that day." for k in result.unplaced)
