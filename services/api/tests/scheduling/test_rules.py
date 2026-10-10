from datetime import date, datetime

from app.platform.clock import IST
from app.scheduling import rules


def test_freeze_cutoff_is_8_pm_the_day_before_the_first_day():
    assert rules.freeze_deadline(date(2026, 10, 18)) == datetime(
        2026, 10, 17, 20, 0, tzinfo=IST)


def test_customers_change_until_9_pm_the_day_before():
    day = date(2026, 10, 19)
    assert rules.customer_can_change(day, datetime(2026, 10, 18, 20, 59, tzinfo=IST))
    assert not rules.customer_can_change(day, datetime(2026, 10, 18, 21, 0, tzinfo=IST))


def test_a_visit_is_completed_only_when_all_jobs_are_done_or_skipped():
    assert rules.visit_status(["Completed", "Skipped"]) == "Completed"
    assert rules.visit_status(["Completed", "Scheduled"]) == "In progress"
    assert rules.visit_status(["Scheduled", "Scheduled"]) == "Scheduled"
    assert rules.visit_status(["In progress", "Scheduled"]) == "In progress"
    assert rules.visit_status(["Completed", "Could not complete"]) == "Could not complete"
    assert rules.visit_status(["Skipped", "Skipped"]) == "Skipped"


def test_trainees_and_absent_crew_add_no_capacity():
    assert rules.window_for("Trainee", 360, 660, None, None) is None
    assert rules.window_for("Member", 360, 660, "Sick", None) is None
    assert rules.window_for("Manager", 360, 660, None, None) == (360, 660)
    assert rules.window_for("Member", 360, 660, "Late start", 420) == (420, 660)
