"""The scheduler as a pure function: capacity is respected and hand-made
placements stay (ADM-SCH-05, ADM-SCH-14)."""
from app.scheduling.solver import SolverCrew, SolverJob, solve_day


def jobs(n, duration=20, **kw):
    return [SolverJob(f"j{i}", f"v{i}", duration, **kw) for i in range(n)]


def overlaps(result, jobs_by_key):
    by_crew = {}
    for key, (crew, start) in result.placed.items():
        by_crew.setdefault(crew, []).append((start, start + jobs_by_key[key].duration))
    for spans in by_crew.values():
        spans.sort()
        for (_, a_end), (b_start, _) in zip(spans, spans[1:], strict=False):
            if b_start < a_end:
                return True
    return False


def test_capacity_is_respected():
    crew = [SolverCrew("a", 360, 420), SolverCrew("b", 360, 420)]  # 2 x 60 min
    work = jobs(8)
    result = solve_day(crew, work)
    assert len(result.placed) == 6
    assert len(result.unplaced) == 2
    assert not overlaps(result, {j.key: j for j in work})
    for _crew, start in result.placed.values():
        assert 360 <= start and start + 20 <= 420


def test_a_hand_made_placement_is_kept_and_blocks_its_time():
    crew = [SolverCrew("a", 360, 420)]
    work = [SolverJob("fixed", "vx", 20, fixed=("a", 380))] + jobs(2)
    result = solve_day(crew, work)
    assert result.placed["fixed"] == ("a", 380)
    assert len(result.placed) == 3
    starts = sorted(s for _c, s in result.placed.values())
    assert starts == [360, 380, 400]


def test_a_deep_spa_does_not_fit_a_short_window():
    crew = [SolverCrew("a", 360, 420)]
    result = solve_day(crew, [SolverJob("spa", "v", 120)])
    assert "spa" in result.unplaced and not result.placed


def test_a_job_that_misses_its_cutoff_is_placed_and_flagged_late():
    crew = [SolverCrew("a", 360, 420)]
    result = solve_day(crew, [SolverJob("j", "v", 20, finish_by=370)])
    assert "j" in result.placed and result.late == {"j"}


def test_jobs_that_can_meet_the_cutoff_do():
    crew = [SolverCrew("a", 360, 480)]
    work = [SolverJob(f"j{i}", f"v{i}", 20, finish_by=420) for i in range(3)]
    result = solve_day(crew, work)
    assert len(result.placed) == 3 and not result.late


def test_one_vehicle_is_not_worked_on_twice_at_once():
    crew = [SolverCrew("a", 360, 480), SolverCrew("b", 360, 480)]
    work = [SolverJob("ext", "same", 20), SolverJob("int", "same", 20)]
    result = solve_day(crew, work)
    (_, s1), (_, s2) = result.placed["ext"], result.placed["int"]
    assert abs(s1 - s2) >= 20


def test_no_crew_leaves_everything_unplaced():
    result = solve_day([], jobs(2))
    assert len(result.unplaced) == 2


def test_the_same_input_gives_the_same_plan():
    crew = [SolverCrew("a", 360, 420), SolverCrew("b", 360, 420)]
    assert solve_day(crew, jobs(5)).placed == solve_day(crew, jobs(5)).placed
