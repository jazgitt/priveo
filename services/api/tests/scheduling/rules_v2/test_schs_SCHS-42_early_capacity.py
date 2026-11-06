"""SCHS-42: among plans with the same coverage, more usable early capacity wins."""
from app.scheduling import passes
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, solve_day

EXT, INT = passes.EXTERIOR, "Cleaning-Internal"
CREW = [SolverCrew("a", 330, 600)]  # 05:30 to 10:00
ORDER = "placed,late,early_capacity,early"


def _params(**weights):
    settings = {"scheduler.objective_order": ORDER, "site.interior_earliest_minute": 420}
    settings.update({f"scheduler.weight_{k}": v for k, v in weights.items()})
    return SolverParams(settings=settings)


def _exteriors(n=5, **kw):
    return [SolverJob(f"e{i}", f"v{i}", 30, service=EXT, **kw) for i in range(n)]


def _pending(cutoff=600):
    return {"pending_interiors": [SolverJob("i", "vi", 60, service=INT, finish_by=cutoff, hard_cutoff=True)]}


def _starts(result):
    return sorted(t for _, t in result.placed.values())


def test_schr_ext_05_the_plan_with_more_usable_early_minutes_wins():
    result = solve_day(CREW, _exteriors(), _params(), "exterior", _pending())
    # Three Exteriors fill the unusable band before 07:00; the rest go to the end
    # of the usable range, leaving 07:00 to 09:00 free for the Interior.
    assert _starts(result) == [330, 360, 390, 540, 570]


def test_schr_ext_05_without_the_objective_the_exteriors_run_one_after_another():
    result = solve_day(CREW, _exteriors(), _params(early_capacity=0), "exterior", _pending())
    assert _starts(result) == [330, 360, 390, 420, 450]


def test_schr_ext_05_free_time_after_the_last_pending_cutoff_is_not_counted():
    result = solve_day(CREW, _exteriors(), _params(), "exterior", _pending(cutoff=480))
    starts = _starts(result)
    assert starts[:3] == [330, 360, 390]
    assert all(t + 15 >= 480 for t in starts[3:])  # the cost is charged on the job's middle


def test_schr_ext_05_no_pending_interior_adds_no_objective():
    result = solve_day(CREW, _exteriors(), _params(), "exterior", {})
    assert _starts(result) == [330, 360, 390, 420, 450]


def test_schr_ext_05_version_1_settings_add_nothing():
    result = solve_day(CREW, _exteriors(), SolverParams(), "exterior", _pending())
    assert _starts(result) == [330, 360, 390, 420, 450]


def test_schr_ext_06_no_cutoff_is_given_up_for_early_capacity():
    jobs = _exteriors(5)
    jobs[0] = SolverJob("e0", "v0", 30, service=EXT, finish_by=480)
    result = solve_day(CREW, jobs, _params(), "exterior", _pending())
    assert not result.late and result.placed["e0"][1] + 30 <= 480


def test_schr_ext_06_coverage_is_never_given_up_for_it():
    crew = [SolverCrew("a", 330, 480)]  # room for exactly five jobs
    result = solve_day(crew, _exteriors(5), _params(), "exterior", _pending(cutoff=480))
    assert len(result.placed) == 5


def test_schr_ext_07_an_eligible_interior_takes_the_free_slot():
    jobs = _exteriors(5) + [SolverJob("i", "vi", 60, service=INT, finish_by=600, hard_cutoff=True)]
    result = passes.solve_passes(CREW, jobs, _params(), {})
    assert not result.unplaced
    start = result.placed["i"][1]
    assert start >= 420 and start + 60 <= 600
