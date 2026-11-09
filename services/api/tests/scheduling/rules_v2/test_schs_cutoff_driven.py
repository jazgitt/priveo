"""Cutoff-driven scheduling (owner decisions of 09-Nov-26): ascending cutoff order in
the normal rules (SCHR-CUT-10), a protected Exterior placed late as the last resort
(SCHR-CUT-09), an Interior that misses a weekday cutoff unplaced rather than late
(SCHR-CUT-11), the cross-zone rescue of a protected job (SCHR-ZONE-12) and the order
that puts protected lateness above the home zone (SCHR-HIER-09).
"""
from app.directory import settings_registry
from app.scheduling import passes
from app.scheduling.codes import ReasonCode
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, solve_day

EXT = passes.EXTERIOR
INT = "Cleaning-Internal"
PRODUCTION = SolverParams(settings={
    "scheduler.objective_order": settings_registry.DEFAULT_OBJECTIVE_ORDER})


def _ext(key, vehicle, finish_by, duration=30):
    return SolverJob(key, vehicle, duration, service=EXT, finish_by=finish_by,
                     hard_cutoff=True, protected=True)


def _zones(home, vehicle_zone):
    """The day input of the zones rule: home zones per cleaner and each car's zone."""
    return {"zones": {
        "home": {k: [v] for k, v in home.items()},
        "vehicle_zone": vehicle_zone,
        "owned": sorted(set(home.values())),
        "cross_allowed": True,
    }}


def test_schr_cut_10_placement_follows_the_ascending_cutoff_within_a_cleaner():
    # Both fit in 08:00 to 10:00 in either order. The 60 minute job has the earlier
    # cutoff (09:30); the 30 minute job has the later one (10:00). Taken alone, the
    # start-time objective would put the 30 minute job first (less total start time),
    # so only the cutoff order puts the earlier cutoff first.
    crew = [SolverCrew("a", 480, 600)]
    jobs = [SolverJob("late", "v0", 30, finish_by=600), SolverJob("early", "v9", 60, finish_by=570)]
    result = solve_day(crew, jobs, PRODUCTION)
    assert not result.late and not result.unplaced
    assert result.placed["early"][1] < result.placed["late"][1]


def test_schr_cut_10_the_order_chains_over_three_jobs():
    crew = [SolverCrew("a", 480, 600)]
    jobs = [SolverJob("c", "v3", 30, finish_by=600), SolverJob("a", "v1", 30, finish_by=550),
            SolverJob("b", "v2", 30, finish_by=570)]
    result = solve_day(crew, jobs, PRODUCTION)
    assert [k for k, _ in sorted(result.placed.items(), key=lambda kv: kv[1][1])] == ["a", "b", "c"]


def test_schr_cut_09_a_protected_exterior_that_cannot_be_on_time_is_placed_late_and_flagged():
    crew = [SolverCrew("a", 480, 510)]
    result = solve_day(crew, [_ext("e", "ve", finish_by=470)], PRODUCTION)
    assert set(result.placed) == {"e"} and result.late == {"e"}
    assert not result.unplaced


def test_schr_cut_09_a_protected_exterior_is_placed_late_in_the_single_weighted_solve_too():
    # No objective order (a direct call): the placed weight still beats the lateness.
    crew = [SolverCrew("a", 480, 510)]
    result = solve_day(crew, [_ext("e", "ve", finish_by=470)])
    assert set(result.placed) == {"e"} and result.late == {"e"}


def test_schr_cut_09_a_protected_exterior_is_unplaced_only_when_there_is_no_capacity():
    # One 30 minute slot for two Exteriors: one is placed late, the other has no
    # capacity left and is reported as capacity, not as a cutoff.
    crew = [SolverCrew("a", 480, 510)]
    result = solve_day(crew, [_ext("e1", "v1", finish_by=490), _ext("e2", "v2", finish_by=500)],
                       PRODUCTION)
    assert len(result.placed) == 1 and len(result.unplaced) == 1
    (left,) = result.unplaced
    assert result.unplaced_codes[left] == ReasonCode.CAPACITY_SHORT
    assert result.late == set(result.placed)
    # With room for both, both are placed, and both are late: nothing is left out.
    roomy = solve_day([SolverCrew("a", 480, 540)],
                      [_ext("e1", "v1", finish_by=490), _ext("e2", "v2", finish_by=490)],
                      PRODUCTION)
    assert not roomy.unplaced and roomy.late == {"e1", "e2"}


def test_schr_cut_11_an_interior_that_misses_its_weekday_cutoff_is_unplaced_not_late():
    crew = [SolverCrew("a", 480, 510)]
    interior = SolverJob("i", "vi", 30, service=INT, finish_by=470, hard_cutoff=True, interior=True)
    result = solve_day(crew, [interior], PRODUCTION)
    assert not result.placed and not result.late
    assert result.unplaced_codes["i"] == ReasonCode.CUSTOMER_CUTOFF


def test_schr_zone_12_a_cleaner_takes_a_protected_job_of_another_zone_when_its_own_cleaner_would_be_late():
    # b (zone Z3) starts at 07:10, so the Z3 Exterior with a 07:00 cutoff is late
    # if b does it. a (zone Z1) is free from 06:00, can do it on time and then do its
    # own Z1 Exterior, which has a later cutoff. The rescue is the only way to have
    # no late protected job, and protected lateness ranks above the home zone.
    crew = [SolverCrew("a", 360, 600), SolverCrew("b", 430, 600)]
    jobs = [_ext("z3", "v3", finish_by=420), _ext("z1", "v1", finish_by=600)]
    data = _zones({"a": "Z1", "b": "Z3"}, {"v3": "Z3", "v1": "Z1"})
    result = solve_day(crew, jobs, PRODUCTION, "exterior", data)
    assert not result.late and not result.unplaced
    assert result.placed["z3"][0] == "a"  # the rescue
    assert result.placed["z1"][0] == "a"


def test_schr_zone_12_no_rescue_is_needed_so_the_home_cleaner_keeps_the_job():
    crew = [SolverCrew("a", 360, 600), SolverCrew("b", 360, 600)]
    jobs = [_ext("z3", "v3", finish_by=600), _ext("z1", "v1", finish_by=600)]
    data = _zones({"a": "Z1", "b": "Z3"}, {"v3": "Z3", "v1": "Z1"})
    result = solve_day(crew, jobs, PRODUCTION, "exterior", data)
    assert not result.late
    assert result.placed["z3"][0] == "b" and result.placed["z1"][0] == "a"


def test_schr_hier_09_a_protected_job_is_placed_late_when_the_rescue_is_not_allowed():
    # The same set-up with cross-zone help off: no rescue, so the protected job is
    # placed late by its own cleaner and flagged; the other job stays with a.
    crew = [SolverCrew("a", 360, 600), SolverCrew("b", 430, 600)]
    jobs = [_ext("z3", "v3", finish_by=420), _ext("z1", "v1", finish_by=600)]
    data = _zones({"a": "Z1", "b": "Z3"}, {"v3": "Z3", "v1": "Z1"})
    data["zones"]["cross_allowed"] = False
    result = solve_day(crew, jobs, PRODUCTION, "exterior", data)
    assert result.placed["z3"][0] == "b" and result.late == {"z3"}
    assert result.placed["z1"][0] == "a"
