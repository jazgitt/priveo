"""Batch moves (POST /admin/scheduling/jobs/batch-move, scheduler board P0-5, P0-7, P0-8).

Decision 5: a drop shifts the cards in its way in the lane, every shifted card is
marked By hand, an overlap refuses the whole batch, late placements are allowed,
and crew-hours or service-hours crossings are warnings only.
"""
from datetime import time

BASE = "/v1/admin/scheduling"
URL = f"{BASE}/jobs/batch-move"


def _board(api, admin, schedule_id):
    r = api.get(f"{BASE}/board", headers=admin, params={"schedule_id": schedule_id})
    assert r.status_code == 200, r.text
    return {j["id"]: j for j in r.json()["jobs"]}


def _lane(jobs, crew_id):
    """The crew's placed jobs in lane order (by start)."""
    rows = [j for j in jobs.values() if j["crew_id"] == crew_id and j["start_minute"] is not None]
    return sorted(rows, key=lambda j: j["start_minute"])


def _planned_lane(api, admin, world, run_week):
    """One crew member with three cars, planned by a one-day run: returns (crew, schedule id, board, lane)."""
    crew = world.add_crew(start=360, end=720)
    for _ in range(3):
        world.add_vehicle(cutoff=time(12, 0))
    world.db.commit()
    schedule_id = run_week(days=1)["schedule_id"]
    jobs = _board(api, admin, schedule_id)
    lane = _lane(jobs, str(crew.id))
    assert len(lane) == 3, "the run should plan all three cars in the one lane"
    return crew, schedule_id, jobs, lane


def _batch(api, admin, moves, override=False):
    return api.post(URL, headers=admin, json={"moves": moves, "override": override})


def _place(job, crew, start):
    return {"job_id": job["id"], "crew_id": str(crew.id), "start_minute": start}


def _free_start(lane, moved_id, duration, low=360, high=660):
    """The first start (5-minute steps) where a card of `duration` fits with no other card of the lane."""
    busy = [(j["start_minute"], j["start_minute"] + j["duration_minutes"])
            for j in lane if j["id"] != moved_id]
    for start in range(low, high - duration + 1, 5):
        if all(start + duration <= b or e <= start for b, e in busy):
            return start
    raise AssertionError("no free time in the lane")


def test_a_batch_places_a_card_in_free_time_and_returns_it(api, admin, world, run_week):
    crew, schedule_id, jobs, lane = _planned_lane(api, admin, world, run_week)
    card = lane[-1]
    start = _free_start(lane, card["id"], card["duration_minutes"])

    r = _batch(api, admin, [_place(card, crew, start)])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["warnings"] == []
    moved = {j["id"]: j for j in body["jobs"]}[card["id"]]
    assert moved["start_minute"] == start and moved["crew_id"] == str(crew.id)
    assert moved["manual"] is True and moved["placed_by_hand"] is True

    after = _board(api, admin, schedule_id)
    for other in lane[:-1]:  # nothing in the way: the others do not move
        assert after[other["id"]]["start_minute"] == other["start_minute"]


def test_a_drop_above_the_first_card_shifts_the_cards_below_and_marks_them_by_hand(
        api, admin, world, run_week):
    crew, schedule_id, jobs, lane = _planned_lane(api, admin, world, run_week)
    card, top = lane[-1], lane[0]

    r = _batch(api, admin, [_place(card, crew, top["start_minute"])])
    assert r.status_code == 200, r.text
    rows = {j["id"]: j for j in r.json()["jobs"]}
    assert rows[card["id"]]["start_minute"] == top["start_minute"]
    assert rows[card["id"]]["manual"] is True

    # The first card sat exactly where the drop lands, so it has to move. Every card that
    # moved is returned marked By hand.
    shifted = [j for j in lane[:-1] if rows[j["id"]]["start_minute"] != j["start_minute"]]
    assert shifted, "the card in the way must shift"
    for j in shifted:
        assert rows[j["id"]]["manual"] is True
        assert rows[j["id"]]["crew_id"] == str(crew.id)

    # The lane is still in order without overlap.
    after = _lane(_board(api, admin, schedule_id), str(crew.id))
    for before_card, next_card in zip(after, after[1:]):
        assert before_card["start_minute"] + before_card["duration_minutes"] <= next_card["start_minute"]


def test_a_forward_drop_between_two_cards_closes_the_gap_the_card_left(api, admin, world, run_week):
    """1 2 3 dragged 1 to the start of 3: 2 moves up to where 1 was, and 1 lands after it."""
    crew, schedule_id, jobs, lane = _planned_lane(api, admin, world, run_week)
    first, middle, last = lane

    r = _batch(api, admin, [_place(first, crew, last["start_minute"])])
    assert r.status_code == 200, r.text
    rows = {j["id"]: j for j in r.json()["jobs"]}
    assert rows[middle["id"]]["start_minute"] == first["start_minute"]
    assert rows[middle["id"]]["manual"] is True
    assert rows[first["id"]]["start_minute"] == first["start_minute"] + middle["duration_minutes"]
    assert rows[last["id"]]["start_minute"] == last["start_minute"]


def test_an_overlap_with_a_locked_card_refuses_the_whole_batch(api, admin, world, run_week):
    crew, schedule_id, jobs, lane = _planned_lane(api, admin, world, run_week)
    first, second, last = lane
    # Locking the first card: a hand placement is locked by default.
    r = api.post(f"{BASE}/jobs/{first['id']}/move", headers=admin,
                 json={"crew_id": str(crew.id), "start_minute": first["start_minute"]})
    assert r.status_code == 200, r.text

    before = _board(api, admin, schedule_id)
    r = _batch(api, admin, [
        _place(last, crew, first["start_minute"]),          # lands on the locked card
        {"job_id": second["id"], "crew_id": None},          # a valid take-off in the same batch
    ])
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "overlap"
    assert first["id"] in detail["job_ids"]

    after = _board(api, admin, schedule_id)
    assert after[second["id"]]["crew_id"] == str(crew.id)  # the take-off did not happen
    assert after[last["id"]]["start_minute"] == before[last["id"]]["start_minute"]
    assert after[first["id"]]["start_minute"] == first["start_minute"]


def test_a_placement_outside_hours_is_allowed_with_a_warning(api, admin, world, run_week):
    crew, schedule_id, jobs, lane = _planned_lane(api, admin, world, run_week)
    card = lane[-1]
    # 700 is inside the slot window but the crew member finishes at 720, so the card runs past the hours.
    r = _batch(api, admin, [_place(card, crew, 700)])
    assert r.status_code == 200, r.text
    body = r.json()
    assert {j["id"]: j for j in body["jobs"]}[card["id"]]["start_minute"] == 700
    codes = {w["code"] for w in body["warnings"] if w["job_id"] == card["id"]}
    assert "crew_hours" in codes
    assert all(w["code"] in ("crew_hours", "service_hours") for w in body["warnings"])


def test_a_take_off_leaves_the_others_where_they_are(api, admin, world, run_week):
    crew, schedule_id, jobs, lane = _planned_lane(api, admin, world, run_week)
    taken = lane[1]

    r = _batch(api, admin, [{"job_id": taken["id"], "crew_id": None}])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["warnings"] == []
    row = {j["id"]: j for j in body["jobs"]}[taken["id"]]
    assert row["crew_id"] is None and row["start_minute"] is None
    assert row["manual"] is True and row["placed_by_hand"] is False

    after = _board(api, admin, schedule_id)
    for other in (lane[0], lane[2]):
        assert after[other["id"]]["crew_id"] == str(crew.id)
        assert after[other["id"]]["start_minute"] == other["start_minute"]


def test_the_same_job_twice_in_one_batch_is_refused(api, admin, world, run_week):
    crew, schedule_id, jobs, lane = _planned_lane(api, admin, world, run_week)
    card = lane[0]
    r = _batch(api, admin, [_place(card, crew, 400), _place(card, crew, 420)])
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "validation_failed"
