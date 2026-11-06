"""SCHS-33: the order and weights of the objectives come from settings."""
import pytest

from app.directory import settings_registry
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


def test_schr_hier_06_an_objective_the_order_does_not_list_runs_last():
    result = solve_day(CREW, _conflict(), _params("placed"))
    assert set(result.placed) == {"A"}


def test_without_an_order_the_single_weighted_solve_of_version_1_is_kept():
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

    site_cfg({"scheduler.rules_version": 2})
    sc = Scenario(world)
    sc.slots()
    sc.cleaner(shift=(480, 600))
    sc.car()
    sc.run(SUNDAY)
    schedule = sc.db.query(Schedule).first()
    ctx = run_context.start(sc.db, schedule, None)
    assert ctx.setting("scheduler.objective_order") == settings_registry.DEFAULT_OBJECTIVE_ORDER
