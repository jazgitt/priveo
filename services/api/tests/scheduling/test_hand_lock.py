"""Hand placements are locked by default (item 15). A locked placement keeps its
crew, day and time through a run. An unlocked one is planned again like any open job."""
from datetime import time

BASE = "/v1/admin/scheduling"


def _board(api, admin, schedule_id):
    r = api.get(f"{BASE}/board", headers=admin, params={"schedule_id": schedule_id})
    assert r.status_code == 200, r.text
    return {j["id"]: j for j in r.json()["jobs"]}


def _one_cleaner_one_car(world, run_week):
    crew = world.add_crew(end=720)
    world.add_vehicle(cutoff=time(9, 0))
    world.db.commit()
    first = run_week(days=1)
    return crew, first["schedule_id"]


def _move(api, admin, job_id, crew, start, **extra):
    return api.post(f"{BASE}/jobs/{job_id}/move", headers=admin,
                    json={"crew_id": str(crew.id), "start_minute": start, **extra})


def test_a_hand_placement_is_locked_by_default_and_a_rerun_keeps_it(api, admin, world, run_week):
    crew, sid = _one_cleaner_one_car(world, run_week)
    job_id = next(iter(_board(api, admin, sid)))
    r = _move(api, admin, job_id, crew, 540)
    assert r.status_code == 200, r.text
    assert r.json()["hand_locked"] is True and r.json()["placed_by_hand"] is True

    again = run_week(days=1)
    assert again["schedule_id"] == sid
    after = _board(api, admin, sid)[job_id]
    assert after["crew_id"] == str(crew.id) and after["start_time"] == "09:00"
    assert after["hand_locked"] is True


def test_an_unlocked_hand_placement_is_planned_again_in_a_run(api, admin, world, run_week):
    crew, sid = _one_cleaner_one_car(world, run_week)
    job_id = next(iter(_board(api, admin, sid)))
    # 60 is outside the cleaner's hours: an override places it and stores the breach.
    r = _move(api, admin, job_id, crew, 60, override=True)
    assert r.status_code == 200, r.text
    assert r.json()["start_minute"] == 60 and r.json()["hand_breaches"]

    r = api.put(f"{BASE}/jobs/{job_id}/hand-lock", headers=admin, json={"locked": False})
    assert r.status_code == 200, r.text
    assert r.json()["hand_locked"] is False and r.json()["placed_by_hand"] is True

    run_week(days=1)
    moved = _board(api, admin, sid)[job_id]
    assert moved["crew_id"] == str(crew.id)
    assert moved["start_minute"] >= 360  # back inside the hours: the run planned it
    assert moved["hand_breaches"] == []  # the breach belonged to the old time


def test_the_lock_can_be_toggled_and_only_a_hand_placement_takes_it(api, admin, world, run_week):
    crew, sid = _one_cleaner_one_car(world, run_week)
    jobs = _board(api, admin, sid)
    planned_id, planned = next(iter(jobs.items()))
    assert planned["placed_by_hand"] is False and planned["hand_locked"] is False

    r = api.put(f"{BASE}/jobs/{planned_id}/hand-lock", headers=admin, json={"locked": True})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "not_hand_placed"

    r = _move(api, admin, planned_id, crew, 540)
    assert r.status_code == 200, r.text
    for locked in (False, True, False):
        r = api.put(f"{BASE}/jobs/{planned_id}/hand-lock", headers=admin, json={"locked": locked})
        assert r.status_code == 200, r.text
        assert r.json()["hand_locked"] is locked
        assert r.json()["start_time"] == "09:00"  # toggling a lock does not move the job
    assert api.put(f"{BASE}/jobs/{planned_id}/hand-lock", headers=admin,
                   json={"locked": True}).json()["hand_locked"] is True

