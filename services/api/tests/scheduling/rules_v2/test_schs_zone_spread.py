"""Zone spread (item 10.1): Pass A keeps a zone's cars with that zone's crew.

A home-less cleaner takes zoned cars only at a soft cross-zone cost, and a split
shift counts as one cleaner for the zone objective (SCHR-ZONE-02, SCHR-ZONE-08/11).
"""
from app.scheduling import passes
from app.scheduling.solver import SolverCrew, SolverJob, SolverParams, solve_day

EXT = passes.EXTERIOR
ORDER = "placed,protected_late,zone,break,fifo,cutoff_order,late,early_capacity,early"


def _job(key, zone):
    return SolverJob(key, f"v{key}", 30, service=EXT), (f"v{key}", zone)


def _solve(crew, specs, home, owned):
    home = {k: [v] if isinstance(v, str) else list(v or []) for k, v in home.items()}
    data = {
        "home": home,
        "vehicle_zone": {v: z for _j, (v, z) in specs if z},
        "owned": sorted(owned),
        "cross_allowed": True,
    }
    params = SolverParams(settings={"scheduler.objective_order": ORDER})
    return solve_day(crew, [s[0] for s in specs], params, "exterior", {"zones": data})


def test_item_10_1_z1_cars_stay_with_the_z1_cleaner_not_a_homeless_one():
    # Asha (Z1) and Ravi (no home zone) both have time. The three Z1 cars must all
    # go to Asha: Ravi takes a zoned car only as cross-zone work.
    crew = [SolverCrew("asha", 360, 480), SolverCrew("ravi", 360, 480)]
    specs = [_job("z1a", "Z1"), _job("z1b", "Z1"), _job("z1c", "Z1")]
    result = _solve(crew, specs, {"asha": "Z1", "ravi": None}, owned={"Z1"})
    assert len(result.placed) == 3
    assert {c for c, _s in result.placed.values()} == {"asha"}


def test_item_10_1_a_split_shift_counts_as_one_cleaner_for_zones():
    # Asha has two windows (both Z1). Bala (Z2) has one. Asha's Z1 jobs must go
    # to her windows, whichever window they fall in, and Bala keeps Z2 work.
    crew = [
        SolverCrew("asha|0", 360, 420),
        SolverCrew("asha|1", 450, 510),
        SolverCrew("bala|0", 360, 480),
    ]
    specs = [_job("z1a", "Z1"), _job("z1b", "Z1"), _job("z1c", "Z1"), _job("z2a", "Z2")]
    result = _solve(crew, specs, {"asha|0": "Z1", "asha|1": "Z1", "bala|0": "Z2"},
                    owned={"Z1", "Z2"})
    assert len(result.placed) == 4
    base = {k: c.split("|")[0] for k, (c, _s) in result.placed.items()}
    assert base["z1a"] == base["z1b"] == base["z1c"] == "asha"
    assert base["z2a"] == "bala"
