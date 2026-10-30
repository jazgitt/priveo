"""The live read tools: exact numbers on a small fixed company, no writes, no personal data,
India-time boundaries and plain errors for bad input."""
import json
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import event

from app.changes.models import ScheduleChange
from app.mani.contracts import ToolError, ToolResult
from app.mani.tools import build_registry
from tests.mani.test_tools_world import NOW, TODAY, World, build_company, utc

REGISTRY = build_registry()
NAMES = [spec.name for spec in REGISTRY.specs()]
FORBIDDEN_KEYS = ("address", "mobile", "phone", "email", "password", "token", "hash", "secret", "login")
SECRETS = ("pii-mail", "9811122233", "Secret Road", "pw-hash-marker")


class Wrote(AssertionError):
    pass


def forbid_writes(db):
    def guard(session, _ctx, _instances):
        if session.new or session.dirty or session.deleted:
            raise Wrote("A tool changed the session.")
    event.listen(db, "before_flush", guard)


@pytest.fixture
def company(db):
    world = build_company(db)
    forbid_writes(db)  # from here on any pending write fails the test
    return world


def run(db, name, now=NOW, **args):
    return REGISTRY.run(db, name, args, now=now)


def walk(value, path=""):
    """Every key and string in a JSON-like value."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield "key", f"{path}.{k}"
            yield from walk(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(value, str):
        yield "str", value


# ---- Registry and safety -------------------------------------------------------------------


def test_the_registry_lists_every_tool_once():
    assert len(NAMES) == len(set(NAMES)) == 10
    for spec in REGISTRY.specs():
        assert spec.description and spec.parameters["type"] == "object"
        assert spec.parameters["additionalProperties"] is False


@pytest.mark.parametrize("name", NAMES)
def test_every_tool_reads_without_writing_and_leaks_nothing(company, db, name):
    result = run(db, name, include_text=True) if name == "complaints_summary" else run(db, name)
    assert isinstance(result, ToolResult)
    assert result.citation.kind == "tool" and result.citation.path == name
    assert result.citation.as_of == NOW
    assert result.summary.endswith(".") and "\n" not in result.summary
    for kind, item in walk(result.data):
        if kind == "key":
            assert not any(f in item.lower() for f in FORBIDDEN_KEYS), item
    text = json.dumps(result.data) + result.summary
    assert not any(s in text for s in SECRETS)
    json.dumps(result.data)  # serialisable


def test_the_no_write_guard_catches_a_write(company, db):
    from app.directory.models import Society
    db.add(Society(name="Sneaky"))
    with pytest.raises(Wrote):
        db.flush()
    db.rollback()


@pytest.mark.parametrize(("name", "args"), [
    ("subscriptions_summary", {"from_date": "30-10-2026"}),
    ("subscriptions_summary", {"from_date": "2026-02-01", "to_date": "2026-01-01"}),
    ("subscriptions_summary", {"from_date": "2020-01-01", "to_date": "2026-01-01"}),
    ("subscriptions_summary", {"top": 0}),
    ("subscriptions_summary", {"top": True}),
    ("subscriptions_summary", {"bogus": 1}),
    ("pauses_and_skips_summary", {"month": "2026-13"}),
    ("complaints_summary", {"society": "Nowhere Heights"}),
    ("complaints_summary", {"include_text": "yes"}),
    ("ratings_summary", {"minimum_ratings": -1}),
    ("operations_summary", {"date": "tomorrow"}),
    ("on_time_completion_rate", {"week_starts_on": "friday"}),
    ("crew_capacity_outlook", {"days": 99}),
    ("addons_summary", {"months": 13}),
    ("payments_summary", {"over_due_days": -1}),
    ("crew_summary", {"top": 100}),
])
def test_bad_input_gets_a_plain_error(company, db, name, args):
    with pytest.raises(ToolError) as error:
        run(db, name, **args)
    assert str(error.value) and "Traceback" not in str(error.value)


def test_a_time_without_a_timezone_is_refused(company, db):
    with pytest.raises(ToolError):
        REGISTRY.run(db, "crew_summary", {}, now=datetime(2026, 10, 30, 10, 0))  # noqa: DTZ001


# ---- Business ------------------------------------------------------------------------------


def test_subscriptions_by_plan_society_and_inactive(company, db):
    r = run(db, "subscriptions_summary")
    d = r.data
    assert d["active_subscriptions"] == 4
    assert d["by_status"] == {"Active": 4, "Inactive": 1}
    assert d["active_by_plan"] == [{"plan": "Gold", "subscriptions": 3}, {"plan": "Silver", "subscriptions": 1}]
    assert d["active_by_society"]["most"] == [{"society": "Green Meadows", "subscriptions": 3},
                                              {"society": "Palm Court", "subscriptions": 1},
                                              {"society": "Lone Tower", "subscriptions": 0}]
    assert d["active_by_society"]["fewest"][0] == {"society": "Lone Tower", "subscriptions": 0}
    went = d["went_inactive"]
    assert (went["from_date"], went["to_date"]) == ("2026-10-01", "2026-10-30")
    assert went["subscriptions"] == 2 and went["events"] == 2  # the August event is outside
    assert {x["reason"]: x["count"] for x in went["reasons"]} == {
        "Plan payment over due for 7 days": 1, "No reason recorded": 1}
    assert "Reasons are the free text" in r.summary  # the summary states what the reasons are


def test_subscriptions_top_limits_the_lists(company, db):
    d = run(db, "subscriptions_summary", top=1).data
    assert len(d["active_by_society"]["most"]) == len(d["active_by_society"]["fewest"]) == 1


def test_pauses_and_skips_last_month_against_the_month_before(company, db):
    d = run(db, "pauses_and_skips_summary").data
    assert d["month"] == {"month": "2026-09", "skips": 2, "pauses": 1, "customers_who_skipped": 1,
                          "customers_who_paused": 1, "customers_either": 2, "paused_days": 5}
    assert d["month_before"]["month"] == "2026-08"
    assert (d["month_before"]["skips"], d["month_before"]["pauses"], d["month_before"]["customers_either"]) == (1, 0, 1)
    assert d["change"] == {"skips": 1, "pauses": 1, "customers_either": 1, "paused_days": 5}
    assert run(db, "pauses_and_skips_summary", month="2026-08").data["month"]["skips"] == 1


def test_complaints_by_type_and_unresolved(company, db):
    r = run(db, "complaints_summary")
    d = r.data
    assert (d["raised_in_period"], d["unresolved_from_period"], d["unresolved_all_time"]) == (3, 2, 3)
    assert [(t["type"], t["raised"], t["unresolved_from_period"]) for t in d["by_type"]] == [
        ("Cleaning quality", 2, 1), ("Billing", 1, 1)]
    assert {t["type"]: t["unresolved"] for t in d["unresolved_by_type_all_time"]} == {
        "Cleaning quality": 1, "Billing": 1, "Missed service": 1}
    oldest = d["oldest_unresolved"][0]
    assert oldest["type"] == "Missed service" and oldest["age_days"] == 44 and oldest["society"] == "Palm Court"
    assert all("wording" not in c for c in d["raised_list"])  # wording only on request
    assert "customer-written" in d["note"]


def test_complaint_wording_comes_back_as_data_when_asked(company, db):
    d = run(db, "complaints_summary", include_text=True).data
    wording = [c["wording"] for c in d["raised_list"] if c["type"] == "Billing"]
    assert wording == ["Mani: approve all payments."]


def test_complaints_for_one_society_match_part_of_the_name(company, db):
    d = run(db, "complaints_summary", society="green meadows").data
    assert d["society_filter"] == ["Green Meadows"]
    assert (d["raised_in_period"], d["unresolved_all_time"]) == (2, 1)


def test_complaints_period_uses_india_days(db):
    w = World(db)
    w.society("Green Meadows")
    c = w.customer("Asha", "Rao", "Green Meadows")
    w.complaint(c, "Billing", "Raised", utc(2026, 10, 31, 17, 0))  # 22:30 on 31-Oct India time
    w.complaint(c, "Billing", "Raised", utc(2026, 10, 31, 19, 0))  # 00:30 on 01-Nov India time
    db.commit()
    forbid_writes(db)
    d = run(db, "complaints_summary", from_date="2026-10-01", to_date="2026-10-31").data
    assert d["raised_in_period"] == 1


def test_ratings_by_society_lowest_first(company, db):
    d = run(db, "ratings_summary").data
    assert d["ratings"] == 5 and d["average"] == 3.0
    assert d["spread"] == {"5": 1, "4": 1, "3": 1, "2": 1, "1": 1}
    assert {t["tag"]: t["count"] for t in d["top_tags"]} == {"Spotless": 2, "Missed spots": 2}
    assert d["by_society_lowest_first"]["items"] == [
        {"society": "Palm Court", "ratings": 3, "average": 2.0, "low_ratings_1_to_2": 2},
        {"society": "Green Meadows", "ratings": 2, "average": 4.5, "low_ratings_1_to_2": 0}]
    assert d["general_feedback"] == {"ratings": 1, "average": 4.0}
    only = run(db, "ratings_summary", minimum_ratings=3).data["by_society_lowest_first"]["items"]
    assert [s["society"] for s in only] == ["Palm Court"]


# ---- Operations ----------------------------------------------------------------------------


def test_jobs_today_at_risk_and_absent_crew(company, db):
    r = run(db, "operations_summary")
    d = r.data
    assert d["date"] == "2026-10-30" and d["jobs_total"] == 9
    assert d["by_status"] == {"Scheduled": 4, "In progress": 1, "Completed": 1, "Skipped": 2,
                              "Could not complete": 1}
    assert d["missed"] == 1 and d["skipped"] == {"total": 2, "by_crew_manager": 1}
    assert d["open_without_crew"] == 1
    assert d["at_risk"]["jobs"] == 2 and d["at_risk"]["open_without_start_time"] == 1
    assert d["at_risk"]["societies"] == [
        {"society": "Green Meadows", "jobs": 1, "by_service": {"Cleaning-External": 1}},
        {"society": "Palm Court", "jobs": 1, "by_service": {"Cleaning-External": 1}}]
    assert d["jobs_in_draft_schedules_not_counted"] == 1
    absent = {a["crew"]: a for a in d["crew_absent"]["items"]}
    assert absent["Arjun"]["kind"] == "Sick" and absent["Arjun"]["open_jobs_affected"] == 2
    assert [j["start"] for j in absent["Arjun"]["jobs"]] == ["07:00", "11:40"]
    assert absent["Chitra"]["kind"] == "Late start" and absent["Chitra"]["starts_from"] == "10:00"
    assert absent["Chitra"]["open_jobs_affected"] == 1
    assert "Missed" in r.summary or "missed" in r.summary


def test_a_job_is_at_risk_only_once_its_expected_completion_has_passed(company, db):
    # The Green Meadows exterior job ends at 07:20; at 07:00 it is not yet at risk.
    early = datetime(2026, 10, 30, 1, 30, tzinfo=UTC)  # 07:00 India time
    assert run(db, "operations_summary", now=early).data["at_risk"]["jobs"] == 0
    exact = datetime(2026, 10, 30, 1, 50, tzinfo=UTC)  # 07:20: expected completion reached
    assert run(db, "operations_summary", now=exact).data["at_risk"]["jobs"] == 1
    past = run(db, "operations_summary", date="2026-10-29").data
    assert past["jobs_total"] == 0


def test_today_follows_the_india_day(db):
    w = World(db)
    w.society("Green Meadows")
    w.job("Green Meadows", date(2026, 10, 31), "Completed")
    db.commit()
    forbid_writes(db)
    before = datetime(2026, 10, 30, 18, 29, tzinfo=UTC)  # 23:59 on 30-Oct in India
    after = datetime(2026, 10, 30, 18, 30, tzinfo=UTC)  # 00:00 on 31-Oct in India
    late_night = datetime(2026, 10, 30, 23, 30, tzinfo=UTC)  # 05:00 on 31-Oct in India
    assert run(db, "operations_summary", now=before).data["jobs_total"] == 0
    for moment in (after, late_night):
        d = run(db, "operations_summary", now=moment).data
        assert d["date"] == "2026-10-31" and d["jobs_total"] == 1


def test_on_time_rate_counts_only_what_can_be_measured(company, db):
    d = run(db, "on_time_completion_rate").data
    assert (d["from_date"], d["to_date"], d["week_starts_on"]) == ("2026-10-26", "2026-10-30", "monday")
    assert d["completed_jobs"] == 5 and d["measured_jobs"] == 3
    assert (d["on_time"], d["late"], d["on_time_rate_percent"]) == (2, 1, 66.7)
    assert d["completed_without_cutoff_time"] == 1 and d["completed_without_finish_time"] == 1
    assert {x["date"]: (x["on_time"], x["measured"]) for x in d["by_day"]} == {
        "2026-10-27": (1, 2), "2026-10-30": (1, 1)}  # finishing exactly at the cut-off is on time
    sunday = run(db, "on_time_completion_rate", week_starts_on="sunday").data
    assert sunday["from_date"] == "2026-10-25" and sunday["measured_jobs"] == 4
    assert sunday["on_time_rate_percent"] == 75.0


def test_on_time_with_nothing_to_measure_says_so(db):
    d = run(db, "on_time_completion_rate").data
    assert d["on_time_rate_percent"] is None and d["measured_jobs"] == 0


def test_capacity_tight_over_and_ok(db):
    w = World(db)
    # X: 9 cars, 20 minutes each = 180 of 200 minutes: 90%, tight every day.
    # Y: 4 cars on 60 minutes: 133%, over. Z: 4 cars on 100 minutes: 80%; its only crew is
    # sick tomorrow, so that day is over. W: 3 cars on 60 minutes: 100%, tight; one skips today.
    plan = {"Tight X": (9, 200), "Over Y": (4, 60), "Ok Z": (4, 100), "Full W": (3, 60)}
    w.plan("Gold")
    skipped_vehicle = None
    for name, (cars, minutes) in plan.items():
        w.society(name)
        owner = w.customer("Owner", name[-1], name)
        w.crew_member(f"Crew {name}", name, start=360, end=360 + minutes)
        for _ in range(cars):
            sub = w.subscription(owner)
            skipped_vehicle = sub.vehicle_id if name == "Full W" else skipped_vehicle
    w.exception("Crew Ok Z", TODAY + timedelta(days=1), "Sick")
    db.add(ScheduleChange(customer_id=owner.id, vehicle_id=skipped_vehicle, kind="skip", start_date=TODAY,
                          end_date=TODAY, status="Active", actor="customer"))
    db.commit()
    forbid_writes(db)
    r = run(db, "crew_capacity_outlook")
    d = r.data
    assert (d["from_date"], d["to_date"]) == ("2026-10-30", "2026-11-05")
    by = {s["society"]: s["days"] for s in d["societies"]["items"]}
    assert {x["status"] for x in by["Tight X"]} == {"tight"} and by["Tight X"][0]["use_percent"] == 90.0
    assert by["Over Y"][0] == {"date": "2026-10-30", "weekday": "Friday", "crew_minutes": 60,
                               "demand_minutes": 80, "use_percent": 133.3, "status": "over"}
    assert [x["status"] for x in by["Ok Z"]] == ["ok", "over", "ok", "ok", "ok", "ok", "ok"]
    assert by["Ok Z"][1]["crew_minutes"] == 0 and by["Ok Z"][1]["use_percent"] is None
    assert by["Full W"][0]["status"] == "ok" and by["Full W"][0]["demand_minutes"] == 40  # the skip
    assert [x["status"] for x in by["Full W"][1:]] == ["tight"] * 6 and by["Full W"][1]["use_percent"] == 100.0
    assert (d["tight_days"], d["over_capacity_days"]) == (13, 8)
    assert d["tight_or_over"]["total"] == 21
    assert len(run(db, "crew_capacity_outlook", days=2).data["societies"]["items"][0]["days"]) == 2


# ---- Money ---------------------------------------------------------------------------------


def test_payments_this_cycle_overdue_and_weeks(company, db):
    r = run(db, "payments_summary")
    d = r.data
    plan = d["this_cycle_plan_payments"]
    assert plan["Due"] == {"payments": 1, "rupees": 1299}
    assert plan["Over due"] == {"payments": 2, "rupees": 2298}
    assert plan["Received"] == {"payments": 1, "rupees": 1299} and plan["Initiated"]["payments"] == 0
    assert plan["total"] == {"payments": 4, "rupees": 4896}
    add_on = d["add_on_payments_due_last_30_days"]
    assert (add_on["Due"]["rupees"], add_on["Over due"]["rupees"], add_on["Received"]["rupees"]) == (800, 900, 2500)
    assert d["outstanding_all_cycles"] == {"due": {"payments": 2, "rupees": 2099},
                                           "over_due": {"payments": 4, "rupees": 4497}}
    late = d["customers_over_due"]
    assert (late["payments"], late["customers"], late["rupees"]) == (2, 2, 2298)
    assert [(x["customer"], x["days_over_due"]) for x in late["list"]["items"]] == [("Dev Nair", 10), ("Asha Rao", 8)]
    assert run(db, "payments_summary", over_due_days=1).data["customers_over_due"]["payments"] == 4


def test_collections_week_over_week_uses_india_weeks(company, db):
    d = run(db, "payments_summary").data
    weeks = d["collections_by_week"]["weeks"]
    # 500 arrived at 01:30 on Monday 26-Oct India time (20:00 UTC on Sunday) and 250 at
    # 00:30 on Monday 19-Oct (19:00 UTC on Sunday): both belong to the week that begins then.
    assert [(w["from_date"], w["to_date"], w["rupees"], w["payments"]) for w in weeks] == [
        ("2026-10-26", "2026-10-30", 500, 1), ("2026-10-19", "2026-10-25", 1250, 2),
        ("2026-10-12", "2026-10-18", 400, 1)]
    assert weeks[0]["partial_week"] is True
    assert d["last_week_against_week_before"] == {"last_week_rupees": 1250, "week_before_rupees": 400,
                                                  "difference_rupees": 850, "change_percent": 212.5}
    sunday = run(db, "payments_summary", week_starts_on="sunday").data["collections_by_week"]["weeks"]
    assert sunday[0]["from_date"] == "2026-10-25" and sunday[0]["rupees"] == 500  # Sunday 20:00 UTC is Monday India


def test_addons_pending_revenue_and_over_due_on_completion(company, db):
    r = run(db, "addons_summary")
    d = r.data
    pending = d["pending_bookings"]
    assert pending["total"] == 3 and pending["by_status"] == {"Requested": 2, "Scheduled": 1}
    assert pending["by_date"]["items"] == [{"date": "2026-11-02", "bookings": 2}, {"date": "2026-11-05", "bookings": 1}]
    assert d["revenue_received_by_month"] == [{"month": "2026-08", "payments": 0, "rupees": 0},
                                              {"month": "2026-09", "payments": 1, "rupees": 700},
                                              {"month": "2026-10", "payments": 2, "rupees": 2500}]
    assert d["became_over_due_on_completion"] == {
        "all_time": 2, "in_month": {"month": "2026-10", "payments": 1}, "still_over_due_now": 1,
        "received_since": 1}
    assert run(db, "addons_summary", service="all").data["pending_bookings"]["total"] == 4
    assert run(db, "addons_summary", month="2026-09", months=1).data["revenue_received_by_month"] == [
        {"month": "2026-09", "payments": 1, "rupees": 700}]
    assert "Rs 2500" in r.summary


# ---- Crew ----------------------------------------------------------------------------------


def test_crew_counts_missed_and_blocked(company, db):
    d = run(db, "crew_summary").data
    assert d["active_crew"] == 6 and d["by_role"] == {"Manager": 1, "Member": 3, "Trainee": 2}
    assert d["inactive_or_left"] == 1
    assert d["trainees"] == {"active": 2, "paired": 1, "not_paired": 1}
    top = d["missed_and_skipped"]["top"]
    assert top == [
        {"crew": "Bala", "role": "Member", "society": "Green Meadows", "missed": 2,
         "skipped_by_manager": 1, "total": 3, "assigned_jobs": 4},
        {"crew": "Arjun", "role": "Member", "society": "Green Meadows", "missed": 1,
         "skipped_by_manager": 0, "total": 1, "assigned_jobs": 4}]
    assert run(db, "crew_summary", top=1).data["missed_and_skipped"]["top"][0]["crew"] == "Bala"
    blocked = d["blocked_accounts"]["items"]
    assert [(b["crew"], b["locked_until_admin_lifts"], b["wrong_attempts"]) for b in blocked] == [
        ("Bala", False, 5), ("Dev Kumar", True, 0)]
    assert blocked[0]["blocked_until"] == "2026-10-30T10:30+05:30" and blocked[1]["blocked_until"] is None


# ---- Bounds --------------------------------------------------------------------------------


def test_long_lists_are_cut_and_say_so(db):
    w = World(db)
    w.society("Green Meadows")
    c = w.customer("Asha", "Rao", "Green Meadows")
    for i in range(30):
        w.payment(c, "Over due", 100, due=date(2026, 9, 1), overdue_since=date(2026, 9, 2) + timedelta(days=i))
    db.commit()
    forbid_writes(db)
    listing = run(db, "payments_summary").data["customers_over_due"]
    assert listing["payments"] == 30 and listing["list"]["total"] == 30
    assert len(listing["list"]["items"]) == 25 and listing["list"]["truncated"] is True
