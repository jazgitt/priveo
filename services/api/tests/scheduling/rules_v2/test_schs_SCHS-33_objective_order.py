"""SCHS-33: the order and weights of the objectives come from settings."""
import random
from datetime import date

import pytest

from app.directory import settings_registry
from app.scheduling import passes
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, solve_day
from tests.scheduling.conftest import SUNDAY

CREW = [SolverCrew("a", 480, 540)]


def _params(order=None, **weights):
    settings = {f"scheduler.weight_{k}": v for k, v in weights.items()}
    if order is not None:
        settings["scheduler.objective_order"] = order
    return SolverParams(settings=settings)


def _conflict():
    # A: 60 minutes, only on time if it ends by 08:40, which it cannot, so it is late.
    # B: 30 minutes, on time. One of them fits in the hour.
    return [SolverJob("A", "va", 60, finish_by=520), SolverJob("B", "vb", 30, finish_by=600)]


def test_schr_par_15_the_order_and_weights_are_settings_with_the_requirements_order_seeded():
    order = settings_registry.default_for("scheduler.objective_order").split(",")
    assert order[0] == "placed" and order.index("break") < order.index("late") < order.index("early_capacity")
    assert order.index("late") < order.index("early_capacity") < order.index("early")  # SCHR-HIER-05
    for name in order:
        assert f"scheduler.weight_{name}" in settings_registry.BY_KEY
    assert set(order) == set(settings_registry.OBJECTIVE_NAMES)


def test_schr_hier_04_the_seeded_order_puts_coverage_first():
    result = solve_day(CREW, _conflict(), _params(settings_registry.default_for("scheduler.objective_order")))
    assert set(result.placed) == {"A"} and result.late == {"A"}


def test_schr_hier_03_changing_the_order_changes_the_plan_as_the_new_order_says():
    result = solve_day(CREW, _conflict(), _params("late,placed,early"))
    assert set(result.placed) == {"B"} and not result.late


def test_schr_hier_03_a_higher_objective_is_never_worsened_for_a_lower_one():
    # Even a huge weight on the lower objective cannot buy back the higher one.
    result = solve_day(CREW, _conflict(), _params("placed,late,early", late=1_000_000_000_000))
    assert set(result.placed) == {"A"}
    result = solve_day(CREW, _conflict(), _params("late,placed,early", placed=1_000_000_000_000))
    assert set(result.placed) == {"B"}


def test_schr_hier_06_same_input_gives_the_same_plan():
    crew = [SolverCrew("a", 480, 720), SolverCrew("b", 480, 720)]
    jobs = [SolverJob(f"j{i}", f"v{i}", 30 + 15 * (i % 3), finish_by=600) for i in range(8)]
    params = _params("placed,late,early")
    first = solve_day(crew, jobs, params)
    again = solve_day(crew, jobs, params)
    assert first.placed == again.placed and first.late == again.late


def test_schr_hier_05_lateness_is_ranked_with_the_rest_of_the_order():
    # Both jobs fit, only one can end by 08:30: placing both beats lateness.
    crew = [SolverCrew("a", 480, 540)]
    jobs = [SolverJob("A", "va", 30, finish_by=510), SolverJob("B", "vb", 30, finish_by=510)]
    result = solve_day(crew, jobs, _params("placed,late,early"))
    assert len(result.placed) == 2 and len(result.late) == 1


def test_schr_hier_03_an_objective_the_order_does_not_list_runs_last():
    result = solve_day(CREW, _conflict(), _params("placed"))
    assert set(result.placed) == {"A"}


def test_without_an_order_the_single_weighted_solve_is_kept():
    result = solve_day(CREW, _conflict(), SolverParams())
    assert set(result.placed) == {"A"}


@pytest.mark.parametrize("bad", ["", "placed,placed", "placed,nonsense", ","])
def test_schr_par_15_an_invalid_order_is_refused(bad):
    definition = settings_registry.BY_KEY["scheduler.objective_order"]
    with pytest.raises(ValueError):
        settings_registry.parse(definition, bad)


def test_schr_par_15_a_valid_order_is_stored_trimmed():
    definition = settings_registry.BY_KEY["scheduler.objective_order"]
    assert settings_registry.parse(definition, " late , placed,early ") == "late,placed,early"


def test_schr_par_15_the_run_snapshot_carries_the_order(world, site_cfg):
    from app.scheduling import run_context
    from app.scheduling.models import Schedule
    from tests.scheduling.builders import Scenario

    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.car()
    sc.run(SUNDAY)
    schedule = sc.db.query(Schedule).first()
    ctx = run_context.start(sc.db, schedule, None)
    assert ctx.setting("scheduler.objective_order") == settings_registry.DEFAULT_OBJECTIVE_ORDER


# ---- SCHR-HIER-03 over random days (gap check, 06-Nov-26) ------------------

ORDER = settings_registry.DEFAULT_OBJECTIVE_ORDER.split(",")
HUGE = 1_000_000_000_000


def _random_day(seed):
    rng = random.Random(seed)
    crew = [SolverCrew(f"c{i}", 420, 420 + rng.choice([90, 120, 150]))
            for i in range(rng.randint(1, 2))]
    jobs = [SolverJob(f"j{n}", f"v{n}", rng.choice([30, 45, 60]),
                      finish_by=rng.choice([None, 480, 510, 540]),
                      hard_cutoff=rng.random() < 0.5)
            for n in range(rng.randint(3, 6))]
    return crew, jobs


def _placed_minutes(jobs, result):
    return sum(job.duration for job in jobs if job.key in result.placed)


@pytest.mark.parametrize("seed", range(20))
def test_schr_hier_03_a_lower_objective_never_worsens_placed_minutes_or_lateness(seed):
    # Only placed minutes (first in the order) and late jobs (fifth) can be read
    # from the result. Raising the weight of any lower objective, by a huge
    # amount, must not reduce the placed minutes. When they are equal, lateness
    # must not rise for an objective ranked below lateness.
    crew, jobs = _random_day(seed)
    base = solve_day(crew, jobs, _params(",".join(ORDER)))
    base_minutes, base_late = _placed_minutes(jobs, base), len(base.late)
    for lower in ORDER[1:]:
        result = solve_day(crew, jobs, _params(",".join(ORDER), **{lower: HUGE}))
        minutes = _placed_minutes(jobs, result)
        assert minutes >= base_minutes, f"{lower} reduced placed minutes"
        if minutes == base_minutes and ORDER.index(lower) > ORDER.index("late"):
            assert len(result.late) <= base_late, f"{lower} raised lateness"


# ---- SCHR-HIER-04: each adjacent pair of the seeded order matters (gap check) ----
#
# A witness is a generated day on which swapping two neighbouring objectives
# changes the plan both ways: the higher one is better when it ranks first, and
# the lower one is better when it ranks first. The days below were found by a
# search over seeds 0 to 300 and are fixed here.

PAIR_ORDER = ["placed", "zone", "break", "fifo", "late", "early_capacity", "early"]
PAIR_EARLIEST, PAIR_END, PAIR_BREAK = 420, 600, (510, 540)
PAIR_WEEKS = [date(2026, 10, 19), date(2026, 10, 26)]  # the older week first


def _pair_day(seed):
    rng = random.Random(seed)
    crew, home = [], {}
    for i in range(rng.randint(1, 2)):
        start = rng.choice([420, 450])
        crew.append(SolverCrew(f"c{i}", start, start + rng.choice([90, 120, 150])))
        home[f"c{i}"] = rng.choice(["Z1", "Z2"])
    jobs, vehicle_zone = [], {}
    for n in range(rng.randint(3, 6)):
        vehicle_zone[f"v{n}"] = rng.choice(["Z1", "Z2"])
        jobs.append(SolverJob(f"e{n}", f"v{n}", rng.choice([30, 60]), service=passes.EXTERIOR,
                              finish_by=rng.choice([None, 480, 510, 540, 570]),
                              hard_cutoff=rng.random() < 0.4))
    for n in range(rng.randint(0, 3)):
        vehicle_zone[f"w{n}"] = rng.choice(["Z1", "Z2"])
        jobs.append(SolverJob(f"i{n}", f"w{n}", 30, service="Cleaning-Internal", interior=True,
                              week=rng.choice(PAIR_WEEKS), finish_by=rng.choice([None, 540, 600])))
    inputs = {
        "zones": {"home": {k: [v] for k, v in home.items()}, "vehicle_zone": vehicle_zone,
                  "owned": sorted(set(home.values())), "cross_allowed": True},
        "break_block": {k: PAIR_BREAK for k in home if rng.random() < 0.8},
        "fifo": {"weeks": {j.vehicle: j.week.isoformat() for j in jobs if j.interior}, "created": {}},
    }
    return crew, jobs, vehicle_zone, home, inputs


def _pair_solve(crew, jobs, inputs, order):
    params = SolverParams(settings={"scheduler.objective_order": ",".join(order),
                                    "site.interior_earliest_minute": PAIR_EARLIEST})
    return passes.solve_passes(crew, jobs, params, inputs)


def _pair_costs(result, jobs, vehicle_zone, home, inputs):
    """Each objective as a cost: lower is better."""
    by = {j.key: j for j in jobs}
    breaks = inputs["break_block"]
    minutes = [m for k, (_c, start) in result.placed.items()
               for m in range(start, start + by[k].duration)]
    return {
        "zone": sum(1 for k, (c, _s) in result.placed.items() if vehicle_zone[by[k].vehicle] != home[c]),
        "break": sum(1 for k, (c, s) in result.placed.items()
                     if c in breaks and s < breaks[c][1] and s + by[k].duration > breaks[c][0]),
        "fifo": -sum(1 for k in result.placed if by[k].interior and by[k].week == PAIR_WEEKS[0]),
        "late": len(result.late),
        "early_capacity": sum(max(0, PAIR_END - m) for m in minutes if m >= PAIR_EARLIEST),
        "early": sum(start for _c, start in result.placed.values()),
    }


def _swapped(higher, lower):
    order = list(PAIR_ORDER)
    i, j = order.index(higher), order.index(lower)
    order[i], order[j] = order[j], order[i]
    return order


def _both_ways(higher, lower, seed):
    crew, jobs, vehicle_zone, home, inputs = _pair_day(seed)
    seeded = _pair_costs(_pair_solve(crew, jobs, inputs, PAIR_ORDER), jobs, vehicle_zone, home, inputs)
    swapped = _pair_costs(_pair_solve(crew, jobs, inputs, _swapped(higher, lower)),
                          jobs, vehicle_zone, home, inputs)
    return seeded, swapped


@pytest.mark.parametrize("higher, lower, seed", [
    ("zone", "break", 11),
    ("fifo", "late", 170),
    ("late", "early_capacity", 17),
    ("early_capacity", "early", 7),
])
def test_schr_hier_04_a_higher_objective_wins_over_its_neighbour(higher, lower, seed):
    seeded, swapped = _both_ways(higher, lower, seed)
    # Seeded order: the higher objective is at its best.
    assert seeded[higher] < swapped[higher], f"{higher} is not ranked above {lower}"
    # Swapped order: the lower objective is at its best, so the swap really matters.
    assert swapped[lower] < seeded[lower], f"{lower} never changes the plan against {higher}"


def test_schr_hier_04_break_and_fifo_never_compete_so_their_order_changes_nothing():
    # The break is a hard limit in the Interior pass (SCHR-BRK-02) and it is a soft
    # cost only in the Exterior pass, where FIFO does not act. So swapping the two
    # changes neither's cost on any day.
    for seed in range(60):
        seeded, swapped = _both_ways("break", "fifo", seed)
        assert seeded["break"] == swapped["break"] and seeded["fifo"] == swapped["fifo"], seed
