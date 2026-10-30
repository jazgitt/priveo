"""The dataset builds the same way each time, and the expected answers match facts counted by
hand from the scenario catalogue (tools/test-data/scenarios.json), not from the eval code."""
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.mani_eval.dataset import FIXED_NOW, build_dataset, make_engine_at


def sql(world, query: str):
    return world["db"].execute(text(query)).all()


def test_dataset_builds_deterministically(tmp_path):
    reports = []
    for name in ("a.sqlite3", "b.sqlite3"):
        engine = make_engine_at(tmp_path / name)
        with Session(engine) as db:
            reports.append(build_dataset(db, FIXED_NOW))
            # A second build on the same file refreshes the same rows.
            assert build_dataset(db, FIXED_NOW).counts == reports[-1].counts
        engine.dispose()
    assert reports[0] == reports[1]


def test_dataset_shape(eval_world):
    report = eval_world["dataset"]
    assert report.today == "2026-10-30"
    assert report.scenarios == 40
    assert report.counts["customers"] == 40
    assert report.counts["admin logins"] == 1
    assert report.counts["complaints"] == 8  # C12 and A02, four each
    assert report.counts["visit ratings"] == 6  # C22 and A02, three each
    assert "Dataset for 2026-10-30" in report.describe()
    assert len(report.customer_mobiles) == 40


def test_q01_active_subscriptions(eval_world):
    exp = eval_world["expected"]["q01"]
    # 64 subscriptions: 4 Inactive (C20, and three on C14), 1 Activating (C19), 59 Active.
    assert exp.value == {"TEST External + Internal": 57, "TEST External Only": 1,
                         "Unknown plan": 1}  # C17 is external only, C27 is a migrated legacy row
    assert sql(eval_world, "select count(*) from subscriptions where status='Active'")[0][0] == 59


def test_q03_inactive(eval_world):
    exp = eval_world["expected"]["q03"]
    assert exp.value == {"events": 0, "inactive_now": 4}


def test_q05_q06_complaints_and_ratings(eval_world):
    q5, q6 = eval_world["expected"]["q05"], eval_world["expected"]["q06"]
    # C12 and A02 each have four complaints: Raised, In progress, Resolved, Raised.
    assert q5.value == {"by_category": {"Cleaning quality": 8}, "total": 8, "unresolved": 6}
    # C22 and A02 each have ratings 5, 4 and 3.
    assert q6.value["count"] == 6 and q6.value["average"] == 4.0
    assert q6.value["lowest"] == ["TEST A02 Admin complaints and reports",
                                  "TEST C22 Completed service history with ratings and check-in"]


def test_q15_jobs_today(eval_world):
    # R01 and A03 each have five vehicles on the crew day: one job per status.
    assert eval_world["expected"]["q15"].value == {
        "total": 10, "completed": 2, "skipped": 2, "missed": 2, "in_progress": 2, "scheduled": 2}
    assert eval_world["expected"]["q36"].value == 2


def test_q16_q17_crew_and_risk(eval_world):
    q16, q17 = eval_world["expected"]["q16"], eval_world["expected"]["q17"]
    # R03: a Sick and a Leave Member, one Late start. They have no jobs today.
    assert q16.value == {"absent": ["TEST R03 Member 3", "TEST R03 Member 4"],
                         "late": ["TEST R03 Member 5"], "jobs_affected": 0}
    # At 11:30 the Scheduled and In progress jobs of R01 and A03 are past their 11:00 time.
    assert q17.value == {"TEST A03 Admin operations failures and rescheduling": 2,
                         "TEST R01 Crew mixed job outcomes and paired trainee": 2}


def test_q18_pending_deep_spa(eval_world):
    # C05 1, C06 2, C07 2, C21 2, R06 1, and C08 three standalone requests.
    exp = eval_world["expected"]["q18"]
    assert exp.value["count"] == 11
    assert exp.value["dates"] == ["2026-11-02", "2026-11-03", "2026-11-04"]


def test_q19_on_time(eval_world):
    # Today 8 non-skipped jobs, 2 completed on time; 5 history visits and 4 completed Deep Spa
    # jobs on time; 2 late (C21 and C08 missed add-ons). 11 of 19.
    exp = eval_world["expected"]["q19"]
    assert (exp.extras["on_time"], exp.extras["due"]) == (11, 19)
    assert exp.value["rate"] == 57.9


def test_q20_capacity(eval_world):
    exp = eval_world["expected"]["q20"]
    # R05 has two counted crew with 10 minutes each: one 20-minute job a day uses 100% (tight)
    # from 31-Oct to 05-Nov and 40 minutes on Friday 06-Nov (over). The shared secondary
    # society has an active vehicle and no crew, so it is over capacity every day.
    assert [d for s, d in exp.value["tight"]] == [
        "2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"]
    assert {s for s, _ in exp.value["tight"]} == {"TEST R05 Capacity shortage and unassigned jobs"}
    assert len(exp.value["over"]) == 8
    assert ("TEST R05 Capacity shortage and unassigned jobs", "2026-11-06") in exp.value["over"]


def test_q21_to_q24_money(eval_world):
    q21, q23, q24 = (eval_world["expected"][k] for k in ("q21", "q23", "q24"))
    rows = sql(eval_world, "select status, sum(amount_rupees) from payments "
                           "where voided_at is null group by status")
    totals = dict(rows)
    assert q21.value["over_due"] == totals["Over due"] == 7494
    assert q21.value["received"] <= totals["Received"]
    # Nine add-on payments are Received at 1,500 each; none is voided.
    assert q24.value == {"revenue": 13500}
    # Every seeded Received payment is stamped today, so last week and the week before are 0.
    assert q23.value["last_week"] == 0 and q23.value["week_before"] == 0
    assert q23.value["this_week"] == totals["Received"]
    assert eval_world["expected"]["q35"].cannot_say


def test_q22_q37_overdue(eval_world):
    # C20 and C14 went Over due 35 days ago. C08, C09 and C15 are Over due for 3 days.
    assert eval_world["expected"]["q22"].value == {"Test C14": 35, "Test C20": 35}
    assert eval_world["expected"]["q37"].value == 5


def test_q26_to_q28_crew(eval_world):
    q26, q27, q28 = (eval_world["expected"][k] for k in ("q26", "q27", "q28"))
    # 40 scenarios x (Manager, Member, Trainee), R03 and R04 add three Members each, and one
    # R04 Member has an inactive login.
    assert q26.value == {"active": 125, "by_role": {"Manager": 40, "Member": 45, "Trainee": 40},
                         "paired_trainees": 40}
    # A03 and R01 have one Skipped and one Could not complete job each; the missed Deep Spa
    # add-ons of C08 and C21 add one each.
    assert q27.value == {"TEST A03 Member 1": 2, "TEST R01 Member 1": 2, "TEST C08 Member 1": 1,
                         "TEST C21 Member 1": 1}
    assert q28.value == ["TEST R04 Member 5"]


def test_q04_q50_q42_and_missing(eval_world):
    expected = eval_world["expected"]
    assert expected["q04"].value["last"] == 0 and expected["q04"].value["before"] == 0
    # All four completed Deep Spa add-ons (C03, C04 x2, C07) are Received.
    assert expected["q50"].value == {"over_due": 0, "completed": 4, "unpaid": 0}
    assert expected["q42"].cannot_say and expected["q38"].cannot_say
    assert date(2026, 1, 1).isoformat() == "2026-01-01"


def test_q02_q49(eval_world):
    q2, q49 = eval_world["expected"]["q02"], eval_world["expected"]["q49"]
    assert q2.extras["top_count"] == 5 and len(q2.value["top"]) == 5
    assert q49.value["customers"] == ["Test A02", "Test C22"]
