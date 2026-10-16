"""Skip, un-skip, pause and cutoff changes (SKIP-, PAUSE-, SCHED-01)."""
from datetime import date, time

from tests.changes.money_fixtures import at


def base(m):
    return f"/v1/customer/vehicles/{m.vehicle_id}"


def vid(m):
    return m.subscription().vehicle_id


def test_skip_is_accepted_until_9pm_the_evening_before(money):
    m = money
    m.clock.now = at(11, 20, 59)
    r = m.client.post(f"{base(m)}/skips", json={"date": "2026-10-12"}, headers=m.customer)
    assert r.status_code == 201, r.text
    assert (r.json()["kind"], r.json()["status"], r.json()["start_date"]) == (
        "skip", "Active", "2026-10-12")
    assert m.gateway.skipped == {(vid(m), date(2026, 10, 12))}


def test_skip_is_refused_from_9pm_the_evening_before(money):
    m = money
    m.clock.now = at(11, 21, 0)
    r = m.client.post(f"{base(m)}/skips", json={"date": "2026-10-12"}, headers=m.customer)
    assert r.status_code == 409 and r.json()["code"] == "after_cutoff"
    assert "12-Oct-26" in r.json()["message"]
    assert not m.gateway.skipped
    # Today itself is always closed, too.
    r = m.client.post(f"{base(m)}/skips", json={"date": "2026-10-11"}, headers=m.customer)
    assert r.json()["code"] == "after_cutoff"


def test_the_admin_is_not_bound_by_9pm_but_not_by_the_past(money):
    m = money
    m.clock.now = at(11, 22)
    r = m.client.post(f"/v1/admin/vehicles/{m.vehicle_id}/skips",
                      json={"date": "2026-10-12"}, headers=m.admin)
    assert r.status_code == 201 and r.json()["actor"] == "admin"
    r = m.client.post(f"/v1/admin/vehicles/{m.vehicle_id}/skips",
                      json={"date": "2026-10-10"}, headers=m.admin)
    assert r.status_code == 409 and r.json()["code"] == "date_in_past"


def test_skip_twice_or_with_the_same_key_is_one_skip(money):
    m = money
    h = {**m.customer, "Idempotency-Key": "k-1"}
    first = m.client.post(f"{base(m)}/skips", json={"date": "2026-10-14"}, headers=h).json()
    again = m.client.post(f"{base(m)}/skips", json={"date": "2026-10-14"}, headers=h).json()
    plain = m.client.post(f"{base(m)}/skips", json={"date": "2026-10-14"},
                          headers=m.customer).json()
    assert first["id"] == again["id"] == plain["id"]
    skips = m.client.get(f"{base(m)}/changes", headers=m.customer).json()["skips"]
    assert len(skips) == 1


def test_a_customer_skip_does_not_change_the_plan(money):
    """A skipped day adds no day to the plan: the renewal date stays put and no
    plan extension is recorded (only a pause or operations skip moves it)."""
    from sqlalchemy import func, select

    from app.changes.models import PlanExtension

    m = money
    before = m.client.get(f"{base(m)}/changes", headers=m.customer).json()["renewal_date"]
    for day in ("2026-10-13", "2026-10-14", "2026-10-15"):
        r = m.client.post(f"{base(m)}/skips", json={"date": day}, headers=m.customer)
        assert r.status_code == 201, r.text
    after = m.client.get(f"{base(m)}/changes", headers=m.customer).json()["renewal_date"]
    assert after == before == "2026-10-31"
    assert m.db.scalar(select(func.count()).select_from(PlanExtension)) == 0


def test_unskip_follows_the_same_cutoff(money):
    m = money
    skip = m.client.post(f"{base(m)}/skips", json={"date": "2026-10-12"},
                         headers=m.customer).json()
    m.clock.now = at(11, 21, 30)
    r = m.client.delete(f"{base(m)}/skips/{skip['id']}", headers=m.customer)
    assert r.status_code == 409 and r.json()["code"] == "after_cutoff"
    m.clock.now = at(11, 20, 0)
    assert m.client.delete(f"{base(m)}/skips/{skip['id']}",
                           headers=m.customer).status_code == 204
    assert not m.gateway.skipped
    assert m.client.get(f"{base(m)}/changes", headers=m.customer).json()["skips"] == []


def test_a_date_inside_a_pause_cannot_be_skipped(money):
    m = money
    r = m.client.post(f"{base(m)}/pauses",
                      json={"from_date": "2026-10-19", "to_date": "2026-10-25"},
                      headers=m.customer)
    assert r.status_code == 201
    r = m.client.post(f"{base(m)}/skips", json={"date": "2026-10-20"}, headers=m.customer)
    assert r.status_code == 409 and r.json()["code"] == "inside_pause"


def test_pause_shows_the_visits_and_the_new_renewal_date(money):
    m = money
    # First service 01-Oct-26, so the cycle renews on 31-Oct-26.
    before = m.client.get(f"{base(m)}/changes", headers=m.customer).json()
    assert before["renewal_date"] == "2026-10-31"
    r = m.client.post(f"{base(m)}/pauses",
                      json={"from_date": "2026-10-19", "to_date": "2026-10-25"},
                      headers=m.customer)
    body = r.json()
    assert (body["days"], body["visits_paused"], body["renewal_date"]) == (7, 7, "2026-11-07")


def test_a_skip_inside_a_pause_is_counted_once(money):
    m = money
    m.client.post(f"{base(m)}/skips", json={"date": "2026-10-20"}, headers=m.customer)
    r = m.client.post(f"{base(m)}/pauses",
                      json={"from_date": "2026-10-19", "to_date": "2026-10-25"},
                      headers=m.customer)
    assert r.json()["renewal_date"] == "2026-11-07"
    changes = m.client.get(f"{base(m)}/changes", headers=m.customer).json()
    assert changes["skips"] == [] and len(changes["pauses"]) == 1


def test_pause_validation_and_cutoff(money):
    m = money
    r = m.client.post(f"{base(m)}/pauses",
                      json={"from_date": "2026-10-20", "to_date": "2026-10-19"},
                      headers=m.customer)
    assert r.status_code == 422
    m.clock.now = at(11, 21, 5)
    r = m.client.post(f"{base(m)}/pauses",
                      json={"from_date": "2026-10-12", "to_date": "2026-10-14"},
                      headers=m.customer)
    assert r.status_code == 409 and r.json()["code"] == "after_cutoff"
    m.clock.now = at(11, 10)
    ok = {"from_date": "2026-10-19", "to_date": "2026-10-21"}
    assert m.client.post(f"{base(m)}/pauses", json=ok, headers=m.customer).status_code == 201
    r = m.client.post(f"{base(m)}/pauses",
                      json={"from_date": "2026-10-21", "to_date": "2026-10-23"},
                      headers=m.customer)
    assert r.json()["code"] == "pause_overlaps"


def test_ending_a_running_pause_resumes_from_the_next_open_date(money):
    m = money
    pause = m.client.post(f"{base(m)}/pauses",
                          json={"from_date": "2026-10-12", "to_date": "2026-10-25"},
                          headers=m.customer).json()
    assert pause["renewal_date"] == "2026-11-14"
    m.clock.now = at(14, 20, 0)  # The pause has run for a few days.
    r = m.client.delete(f"{base(m)}/pauses/{pause['id']}", headers=m.customer)
    assert r.status_code == 200
    # 15-Oct-26 is still before its 9 PM cutoff, so visits resume then.
    assert r.json()["end_date"] == "2026-10-14"
    assert r.json()["renewal_date"] == "2026-11-03"  # Three days paused.
    assert (vid(m), date(2026, 10, 15)) not in m.gateway.paused


def test_ending_after_9pm_resumes_a_day_later(money):
    m = money
    pause = m.client.post(f"{base(m)}/pauses",
                          json={"from_date": "2026-10-12", "to_date": "2026-10-25"},
                          headers=m.customer).json()
    m.clock.now = at(14, 21, 30)
    r = m.client.delete(f"{base(m)}/pauses/{pause['id']}", headers=m.customer)
    assert r.json()["end_date"] == "2026-10-15"


def test_a_pause_ending_today_says_it_ends_today(money):
    m = money
    pause = m.client.post(f"{base(m)}/pauses",
                          json={"from_date": "2026-10-12", "to_date": "2026-10-17"},
                          headers=m.customer).json()
    m.clock.now = at(17, 1, 0)  # 1 AM on the last day of the pause.
    r = m.client.delete(f"{base(m)}/pauses/{pause['id']}", headers=m.customer)
    assert r.status_code == 409 and r.json()["code"] == "pause_ending"
    assert r.json()["message"] == "That pause ends today already."


def test_a_pause_ending_tomorrow_says_it_ends_tomorrow(money):
    m = money
    pause = m.client.post(f"{base(m)}/pauses",
                          json={"from_date": "2026-10-12", "to_date": "2026-10-18"},
                          headers=m.customer).json()
    m.clock.now = at(17, 21, 30)  # After 9 PM, so visits could only resume on the 19th.
    r = m.client.delete(f"{base(m)}/pauses/{pause['id']}", headers=m.customer)
    assert r.status_code == 409
    assert r.json()["message"] == "That pause ends tomorrow already."


def test_a_pause_that_has_not_started_is_cancelled(money):
    m = money
    pause = m.client.post(f"{base(m)}/pauses",
                          json={"from_date": "2026-10-19", "to_date": "2026-10-25"},
                          headers=m.customer).json()
    r = m.client.delete(f"{base(m)}/pauses/{pause['id']}", headers=m.customer)
    assert (r.json()["status"], r.json()["renewal_date"]) == ("Cancelled", "2026-10-31")
    assert not m.gateway.paused


def test_cutoff_time_change_is_applied_or_requested_when_frozen(money):
    m = money
    r = m.client.post(f"{base(m)}/cutoff-changes",
                      json={"date": "2026-10-13", "cutoff_time": "06:30"},
                      headers=m.customer)
    assert (r.json()["status"], r.json()["cutoff_time"]) == ("Applied", "06:30")
    assert m.gateway.cutoffs[(vid(m), date(2026, 10, 13))] == time(6, 30)

    m.gateway.frozen_days.add(date(2026, 10, 14))
    r = m.client.post(f"{base(m)}/cutoff-changes",
                      json={"date": "2026-10-14", "cutoff_time": "08:00"},
                      headers=m.customer)
    assert r.json()["status"] == "Requested"
    assert (vid(m), date(2026, 10, 14)) not in m.gateway.cutoffs

    r = m.client.post(f"{base(m)}/cutoff-changes",
                      json={"date": "2026-10-15", "cutoff_time": "06:15"},
                      headers=m.customer)
    assert r.status_code == 422
    m.clock.now = at(11, 21, 1)
    r = m.client.post(f"{base(m)}/cutoff-changes",
                      json={"date": "2026-10-12", "cutoff_time": "07:00"},
                      headers=m.customer)
    assert r.json()["code"] == "after_cutoff"


def test_upcoming_days_show_skips_pauses_and_what_can_still_change(money):
    m = money
    m.clock.now = at(11, 20, 30)
    m.client.post(f"{base(m)}/skips", json={"date": "2026-10-13"}, headers=m.customer)
    m.client.post(f"{base(m)}/pauses",
                  json={"from_date": "2026-10-15", "to_date": "2026-10-16"},
                  headers=m.customer)
    days = m.client.get(f"{base(m)}/upcoming", headers=m.customer).json()
    by = {d["date"]: d for d in days}
    assert by["2026-10-12"]["state"] == "Scheduled" and by["2026-10-12"]["can_change"] is True
    assert by["2026-10-13"]["state"] == "Skipped" and by["2026-10-13"]["skip_id"]
    assert by["2026-10-15"]["state"] == "Paused"
    # 16-Oct-26 is a Friday: exterior and interior.
    assert by["2026-10-16"]["services"] == ["Cleaning-External", "Cleaning-Internal"]
    m.clock.now = at(11, 21, 0)
    days = m.client.get(f"{base(m)}/upcoming", headers=m.customer).json()
    assert days[0]["date"] == "2026-10-12" and days[0]["can_change"] is False


def test_only_active_subscriptions_and_own_vehicles(money):
    m = money
    activating = m.add_vehicle(subscribed=True, status="Activating")
    r = m.client.post(f"/v1/customer/vehicles/{activating}/skips",
                      json={"date": "2026-10-13"}, headers=m.customer)
    assert r.json()["code"] == "subscription_not_active"
    none = m.add_vehicle(subscribed=False)
    r = m.client.post(f"/v1/customer/vehicles/{none}/pauses",
                      json={"from_date": "2026-10-19", "to_date": "2026-10-20"},
                      headers=m.customer)
    assert r.json()["code"] == "subscription_not_active"
    assert m.client.get("/v1/customer/vehicles/not-a-uuid/changes",
                        headers=m.customer).status_code == 404
    assert m.client.post(f"{base(m)}/skips", json={"date": "2026-10-13"},
                         headers=m.admin).status_code == 403
    assert m.client.post(f"{base(m)}/skips", json={"date": "2026-10-13"}).status_code == 401
