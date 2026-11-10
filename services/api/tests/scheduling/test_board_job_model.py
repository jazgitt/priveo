"""The board sends each job's car model alone, so the Detail card can show it (owner, 10-Nov-26)."""
from datetime import time

BASE = "/v1/admin/scheduling"


def test_board_jobs_carry_the_car_model(api, admin, world, run_week):
    world.add_crew(end=720)
    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    first = run_week(days=1)
    r = api.get(f"{BASE}/board", headers=admin, params={"schedule_id": first["schedule_id"]})
    assert r.status_code == 200, r.text
    jobs = r.json()["jobs"]
    assert jobs
    for job in jobs:
        assert job["model"] == "Creta"
        assert job["vehicle"] == "Hyundai Creta"
