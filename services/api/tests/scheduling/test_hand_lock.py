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



def _exterior_id(api, admin, schedule_id):
    return next(j["id"] for j in _board(api, admin, schedule_id).values()
                if j["service"] == "Cleaning-External")


def test_an_unlocked_hand_placement_loses_by_hand_when_a_run_places_it(api, admin, world, run_week):
    # P2-2: the solver re-places an unlocked hand card, so it is no longer "By hand".
    crew, sid = _one_cleaner_one_car(world, run_week)
    job_id = _exterior_id(api, admin, sid)
    r = _move(api, admin, job_id, crew, 540)
    assert r.status_code == 200, r.text
    assert r.json()["placed_by_hand"] is True
    r = api.put(f"{BASE}/jobs/{job_id}/hand-lock", headers=admin, json={"locked": False})
    assert r.status_code == 200, r.text

    run_week(days=1)
    moved = _board(api, admin, sid)[job_id]
    assert moved["crew_id"] == str(crew.id)
    assert moved["manual"] is False and moved["placed_by_hand"] is False


def test_a_locked_hand_placement_keeps_by_hand_through_a_run(api, admin, world, run_week):
    crew, sid = _one_cleaner_one_car(world, run_week)
    job_id = _exterior_id(api, admin, sid)
    assert _move(api, admin, job_id, crew, 540).status_code == 200

    run_week(days=1)
    kept = _board(api, admin, sid)[job_id]
    assert kept["manual"] is True and kept["placed_by_hand"] is True
    assert kept["hand_locked"] is True and kept["start_time"] == "09:00"


def test_a_card_taken_off_by_hand_is_planned_again_by_a_later_run(api, admin, world, run_week):
    # P2-9 (decision 2): an unlocked card taken off by hand goes back into the plan.
    crew, sid = _one_cleaner_one_car(world, run_week)
    job_id = _exterior_id(api, admin, sid)
    r = api.post(f"{BASE}/jobs/{job_id}/move", headers=admin, json={"crew_id": None})
    assert r.status_code == 200 and r.json()["crew_id"] is None

    run_week(days=1)
    back = _board(api, admin, sid)[job_id]
    assert back["crew_id"] == str(crew.id)
    assert back["manual"] is False and back["hand_locked"] is False


def test_a_locked_card_taken_off_by_hand_stays_off_a_later_run(api, admin, world, run_week):
    crew, sid = _one_cleaner_one_car(world, run_week)
    job_id = _exterior_id(api, admin, sid)
    assert _move(api, admin, job_id, crew, 540).status_code == 200  # locked by default
    r = api.post(f"{BASE}/jobs/{job_id}/move", headers=admin, json={"crew_id": None})
    assert r.status_code == 200 and r.json()["crew_id"] is None

    run_week(days=1)
    off = _board(api, admin, sid)[job_id]
    assert off["crew_id"] is None and off["manual"] is True and off["hand_locked"] is True


def test_a_card_taken_off_by_hand_can_be_locked_and_unlocked(api, admin, world, run_week):
    # The lock shows on a card in Unscheduled: locked stays off a later run, unlocked is planned again.
    crew, sid = _one_cleaner_one_car(world, run_week)
    job_id = _exterior_id(api, admin, sid)
    assert api.post(f"{BASE}/jobs/{job_id}/move", headers=admin, json={"crew_id": None}).status_code == 200
    r = api.put(f"{BASE}/jobs/{job_id}/hand-lock", headers=admin, json={"locked": True})
    assert r.status_code == 200, r.text
    assert r.json()["hand_locked"] is True and r.json()["placed_by_hand"] is True

    run_week(days=1)
    off = _board(api, admin, sid)[job_id]
    assert off["crew_id"] is None and off["hand_locked"] is True

    assert api.put(f"{BASE}/jobs/{job_id}/hand-lock", headers=admin, json={"locked": False}).status_code == 200
    run_week(days=1)
    assert _board(api, admin, sid)[job_id]["crew_id"] == str(crew.id)
