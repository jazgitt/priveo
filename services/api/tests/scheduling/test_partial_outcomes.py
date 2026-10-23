"""Partially Completed visits in the admin missed queue and the Schedule board."""
from app.scheduling import service
from tests.scheduling.test_operations import missed, pinned_today, resolve, setup  # noqa: F401


def queue(api, admin, name="missed"):
    return api.get(f"/v1/admin/operations/jobs?queue={name}", headers=admin).json()


def test_a_partial_visit_is_listed_for_follow_up_with_planned_and_delivered(world, api, admin):
    _, sid, visit, jobs = setup(world, api, admin)
    service.set_job_status(world.db, jobs["Cleaning-External"].id, "Completed")
    missed(world, jobs["Cleaning-Internal"])

    rows = queue(api, admin)
    row = next(r for r in rows if r["id"] == str(jobs["Cleaning-Internal"].id))
    assert row["visit_outcome"] == "Partially Completed" and row["partial"] is True
    assert row["planned_services"] == ["Cleaning-External", "Cleaning-Internal"] or set(
        row["planned_services"]) == {"Cleaning-External", "Cleaning-Internal"}
    assert row["delivered_services"] == ["Cleaning-External"]
    assert row["missed_services"][0]["service"] == "Cleaning-Internal"
    assert row["outcome_summary"].startswith("Exterior done. Interior not done today")
    # Who and when the outcome was recorded, with reason and remark.
    assert row["reported_by"] and row["reported_at"]
    assert (row["reason_key"], row["note"]) == ("other", "Car unavailable")


def test_the_board_shows_the_derived_outcome_of_every_job(world, api, admin):
    _, sid, visit, jobs = setup(world, api, admin)
    service.set_job_status(world.db, jobs["Cleaning-External"].id, "Completed")
    missed(world, jobs["Cleaning-Internal"])
    board = api.get(f"/v1/admin/scheduling/board?schedule_id={sid}", headers=admin).json()
    mine = [j for j in board["jobs"] if j["visit_id"] == str(visit.id)]
    assert {j["visit_outcome"] for j in mine} == {"Partially Completed"}
    assert mine[0]["delivered_services"] == ["Cleaning-External"]


def test_rescheduling_the_missed_job_keeps_the_partial_visit_visible(world, api, admin):
    _, _, visit, jobs = setup(world, api, admin)
    service.set_job_status(world.db, jobs["Cleaning-External"].id, "Completed")
    missed(world, jobs["Cleaning-Internal"])
    assert resolve(api, admin, jobs["Cleaning-Internal"], "Reschedule").status_code == 200
    history = queue(api, admin, "history")
    row = next(r for r in history if r["id"] == str(jobs["Cleaning-Internal"].id))
    assert row["visit_outcome"] == "Partially Completed"
    assert row["missed_services"][0]["rescheduled"] is True


def test_a_wholly_missed_visit_is_not_completed_and_then_rescheduled(world, api, admin):
    _, _, visit, jobs = setup(world, api, admin)
    # Only the Interior job misses; the Exterior job is also missed.
    missed(world, jobs["Cleaning-External"])
    missed(world, jobs["Cleaning-Internal"])
    row = next(r for r in queue(api, admin) if r["id"] == str(jobs["Cleaning-Internal"].id))
    assert row["visit_outcome"] == "Not Completed" and row["partial"] is False
    assert resolve(api, admin, jobs["Cleaning-Internal"], "Reschedule").status_code == 200
    # The Exterior job has no follow-up, so the visit is not Rescheduled yet.
    row = next(r for r in queue(api, admin) if r["id"] == str(jobs["Cleaning-External"].id))
    assert row["visit_outcome"] == "Not Completed"
