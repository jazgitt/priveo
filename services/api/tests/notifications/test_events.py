# ruff: noqa: F811
"""Events other modules emit, crew inbox, preferences and the cron endpoints
(NOTIF-, SET-, CRW-NOT-, CRW-SCH-08, CRW-SVC-09, CRW-MGR-02, CRW-CNC-04)."""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.models import Payment
from app.changes.rules import get_now
from app.customers.models import Customer, Subscription
from app.identity.models import Login
from app.notifications import emit
from app.notifications.bridge import SupportNotifier
from app.notifications.cron import CronSettings, get_cron_settings
from app.notifications.models import DeviceToken, Notification
from app.notifications.push import LoggingPushSender, get_default_sender, set_default_sender
from app.notifications.service import NotificationService
from app.platform.clock import IST
from app.scheduling import service as scheduling
from app.scheduling.models import Job, Schedule
from app.support.models import AdminAlert
from tests.customer_reads.conftest import add_customer, api, headers_for, repo  # noqa: F401
from tests.visits.conftest import (  # noqa: F401
    DAY,
    PASSWORD,
    crew_client,
    make_crew,
    new_visit,
    signin,
    store,
    world,
)

CUSTOMER_LOGIN = "owner@priveo.test"
FORBIDDEN_IN_CREW_TEXT = ("Secret", "Name", "9123456789", "owner@priveo.test")


@pytest.fixture
def push():
    sender = LoggingPushSender()
    before = get_default_sender()
    set_default_sender(sender)
    yield sender
    set_default_sender(before)


@pytest.fixture
def customer_login(db, world):
    return db.scalar(select(Login).where(Login.login_id == CUSTOMER_LOGIN))


@pytest.fixture
def asha(db, headers_for):
    add_customer(db, "asha@example.com", [("HR26DK8337", "Creta", True)])
    return {"headers": headers_for("asha@example.com")}


def inbox(db: Session, login_id) -> list[Notification]:
    db.expire_all()
    return list(db.scalars(select(Notification).where(Notification.login_id == login_id)
                           .order_by(Notification.created_at, Notification.id)))


def events(db, login_id) -> list[str]:
    return [n.event for n in inbox(db, login_id)]


# Visit completed and skipped ---------------------------------------------------

def test_a_visit_completed_tells_the_customer_once(db, world, make_crew, new_visit,
                                                   customer_login, push):
    ravi = make_crew("9000000010", "Ravi")
    visit, (a, b) = new_visit(services=("Cleaning-External", "Cleaning-Internal"), assigned=ravi)
    scheduling.set_job_status(db, a.id, "Completed")
    assert events(db, customer_login.id) == []  # the visit is not Completed yet
    scheduling.set_job_status(db, b.id, "Completed")
    rows = inbox(db, customer_login.id)
    assert [n.event for n in rows] == ["service_completed"]
    assert rows[0].visit_id == str(visit.id) and rows[0].ref_type == "visit"
    scheduling.set_job_status(db, b.id, "Completed")  # again: still one message
    assert len(inbox(db, customer_login.id)) == 1


def test_a_switched_off_event_is_not_sent(db, world, make_crew, new_visit,
                                          customer_login, push):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    NotificationService(db, push).set_preferences(customer_login.id, {"service_completed": False})
    scheduling.set_job_status(db, job.id, "Completed")
    assert events(db, customer_login.id) == []
    assert push.sent == []


def test_skipped_by_operations_tells_the_customer_and_the_crew(
        db, world, make_crew, new_visit, customer_login, push):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    scheduling.set_job_status(db, job.id, "Skipped")
    assert events(db, customer_login.id) == ["service_skipped"]
    assert events(db, ravi.login_id) == ["crew_job_removed"]
    body = inbox(db, ravi.login_id)[0].body
    assert not any(word in body for word in FORBIDDEN_IN_CREW_TEXT)


def test_could_not_complete_alerts_the_admin_only(db, world, make_crew, new_visit,
                                                  customer_login, push):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    scheduling.set_job_status(db, job.id, "Could not complete")
    scheduling.set_job_status(db, job.id, "Could not complete")
    alerts = list(db.scalars(select(AdminAlert).where(AdminAlert.kind == "job_missed")))
    assert len(alerts) == 1
    assert events(db, customer_login.id) == []


# The crew's events -------------------------------------------------------------

def test_freeze_tells_each_crew_member_and_their_trainee_once(
        db, world, make_crew, new_visit, push):
    ravi = make_crew("9000000010", "Ravi")
    trainee = make_crew("9000000011", "Tina", role="Trainee", member=ravi)
    sunil = make_crew("9000000012", "Sunil")
    new_visit(assigned=ravi, status="Draft")
    new_visit(vehicle=1, assigned=sunil, status="Draft")
    schedule = db.scalar(select(Schedule).where(Schedule.status == "Draft"))
    scheduling.freeze(db, schedule, None)
    assert events(db, ravi.login_id) == ["crew_schedule_frozen"]
    assert events(db, trainee.login_id) == ["crew_schedule_frozen"]
    assert events(db, sunil.login_id) == ["crew_schedule_frozen"]
    emit.schedules_frozen(db, [schedule.id])  # the same freeze again
    assert events(db, ravi.login_id) == ["crew_schedule_frozen"]
    assert not any(w in inbox(db, ravi.login_id)[0].body for w in FORBIDDEN_IN_CREW_TEXT)


def test_freeze_due_tells_the_crew(db, world, make_crew, new_visit, push):
    ravi = make_crew("9000000010", "Ravi")
    new_visit(assigned=ravi, status="Draft")
    after_cutoff = datetime(2026, 11, 6, 21, 0, tzinfo=IST)
    assert len(scheduling.freeze_due(db, after_cutoff)) >= 1
    assert events(db, ravi.login_id) == ["crew_schedule_frozen"]


def test_a_late_assignment_tells_the_new_crew_member_and_alerts_the_admin(
        db, world, make_crew, new_visit, push):
    ravi = make_crew("9000000010", "Ravi")
    sunil = make_crew("9000000012", "Sunil")
    visit, (job,) = new_visit()  # on nobody
    schedule = db.get(Schedule, visit.schedule_id)
    before = emit.assignment_snapshot(db, schedule)
    db.get(Job, job.id).crew_id = ravi.id
    db.commit()
    emit.late_assignments(db, schedule, before)
    assert events(db, ravi.login_id) == ["crew_job_assigned"]
    assert db.scalar(select(AdminAlert).where(AdminAlert.kind == "auto_assigned"))
    # Moved on to Sunil: Ravi loses it, Sunil gets it.
    before = emit.assignment_snapshot(db, schedule)
    db.get(Job, job.id).crew_id = sunil.id
    db.commit()
    emit.late_assignments(db, schedule, before)
    assert events(db, ravi.login_id) == ["crew_job_assigned", "crew_job_removed"]
    assert events(db, sunil.login_id) == ["crew_job_assigned"]


def test_a_visit_nobody_can_take_goes_to_needs_scheduling_alert(
        db, world, make_crew, new_visit, push):
    visit, (job,) = new_visit()
    schedule = db.get(Schedule, visit.schedule_id)
    emit.late_assignments(db, schedule, {})
    emit.late_assignments(db, schedule, {})
    count = len(list(db.scalars(select(AdminAlert).where(AdminAlert.kind == "needs_scheduling"))))
    assert count == 1


def test_a_skip_after_the_freeze_removes_the_job_and_alerts_the_admin(
        db, world, make_crew, new_visit, push):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    db.get(Job, job.id).status = "Skipped"
    db.commit()
    emit.visits_removed(db, world.vehicles[0].id, DAY, DAY, "skip")
    assert events(db, ravi.login_id) == ["crew_job_removed"]
    assert db.scalar(select(AdminAlert).where(AdminAlert.kind == "skip_after_freeze"))


def test_a_paused_job_removes_it_from_the_crew(db, world, make_crew, new_visit, push):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    db.get(Job, job.id).status = "Skipped"
    db.commit()
    emit.visits_removed(db, world.vehicles[0].id, DAY, DAY + timedelta(days=3), "pause")
    assert events(db, ravi.login_id) == ["crew_job_removed"]


def test_a_customer_skip_tells_the_customer(db, world, customer_login, push):
    emit.customer_skipped(db, world.vehicles[0], DAY)
    assert events(db, customer_login.id) == ["service_skipped"]


def test_a_manager_reassign_tells_both_and_the_trainee(
        crew_client, db, make_crew, new_visit, signin, push):
    boss = make_crew("9000000001", "Manju", role="Manager")
    ravi = make_crew("9000000010", "Ravi")
    tina = make_crew("9000000011", "Tina", role="Trainee", member=ravi)
    sunil = make_crew("9000000012", "Sunil")
    _, (job,) = new_visit(assigned=ravi)
    r = crew_client.post(f"/v1/crew/manager/jobs/{job.id}/reassign", headers=signin(boss),
                         json={"crew_id": str(sunil.id)})
    assert r.status_code == 200, r.text
    assert events(db, ravi.login_id) == ["crew_job_reassigned"]
    assert events(db, tina.login_id) == ["crew_job_reassigned"]
    assert events(db, sunil.login_id) == ["crew_job_reassigned"]
    for login_id in (ravi.login_id, sunil.login_id):
        assert not any(w in inbox(db, login_id)[0].body for w in FORBIDDEN_IN_CREW_TEXT)


def test_a_skipped_job_leaves_the_crew_cards(crew_client, db, make_crew, new_visit,
                                              signin, push):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    scheduling.set_job_status(db, job.id, "Skipped")
    r = crew_client.get(f"/v1/crew/visits?date={DAY.isoformat()}", headers=signin(ravi))
    assert r.status_code == 200
    assert r.json()["jobs"] == []


# Crew inbox and devices ----------------------------------------------------------

def test_the_crew_inbox_devices_and_read(crew_client, db, make_crew, new_visit, signin,
                                         push):
    ravi = make_crew("9000000010", "Ravi")
    _, (job,) = new_visit(assigned=ravi)
    headers = signin(ravi)
    body = {"token": "crew-token-0001", "platform": "android"}
    assert crew_client.put("/v1/crew/devices", json=body, headers=headers).status_code == 204
    scheduling.set_job_status(db, job.id, "Skipped")
    assert len(push.sent) == 1 and push.sent[0].tokens == ("crew-token-0001",)
    assert push.sent[0].data["event"] == "crew_job_removed"
    items = crew_client.get("/v1/crew/notifications", headers=headers).json()
    assert items["unread_count"] == 1
    assert items["items"][0]["ref_type"] == "job"
    nid = items["items"][0]["id"]
    assert crew_client.post(f"/v1/crew/notifications/{nid}/read",
                            headers=headers).status_code == 204
    assert crew_client.get("/v1/crew/notifications", headers=headers).json()["unread_count"] == 0
    assert crew_client.delete("/v1/crew/devices/crew-token-0001",
                              headers=headers).status_code == 204


def test_a_customer_cannot_open_the_crew_inbox(crew_client, make_crew, signin):
    ravi = make_crew("9000000010", "Ravi")
    assert crew_client.get("/v1/crew/notifications").status_code == 401
    assert crew_client.get("/v1/customer/notifications",
                           headers=signin(ravi)).status_code == 403


def test_a_crew_member_has_no_switches(crew_client, make_crew, signin):
    ravi = make_crew("9000000010", "Ravi")
    r = crew_client.get("/v1/customer/notification-preferences", headers=signin(ravi))
    assert r.status_code == 403


# Preferences -------------------------------------------------------------------

def test_preferences_default_on_and_change_one_at_a_time(api, asha):
    headers = asha["headers"]
    items = api.get("/v1/customer/notification-preferences", headers=headers).json()["items"]
    assert [i["event"] for i in items] == [
        "service_completed", "service_skipped", "complaint_update", "renewal_reminder",
        "monthly_check_in"]
    assert all(i["enabled"] for i in items)
    r = api.put("/v1/customer/notification-preferences", headers=headers,
                json={"items": [{"event": "renewal_reminder", "enabled": False}]})
    assert r.status_code == 200
    by_event = {i["event"]: i["enabled"] for i in r.json()["items"]}
    assert by_event["renewal_reminder"] is False and by_event["service_completed"] is True
    bad = api.put("/v1/customer/notification-preferences", headers=headers,
                  json={"items": [{"event": "crew_job_removed", "enabled": False}]})
    assert bad.status_code == 422


# # Support bridge and the renewal reminders --------------------------------------

def test_the_support_bridge_writes_the_inbox_and_follows_the_switch(
        db, world, customer_login, push):
    bridge = SupportNotifier(db)
    bridge.push_customer(customer_login.id, "Complaint update", "#C-0001: Looking into it",
                         event="complaint_update", ref_type="complaint", ref_id="abc")
    row = inbox(db, customer_login.id)[0]
    assert row.event == "complaint_update" and row.ref_type == "complaint"
    NotificationService(db, push).set_preferences(customer_login.id, {"monthly_check_in": False})
    bridge.push_customer(customer_login.id, "Monthly check-in", "Tell us")
    assert events(db, customer_login.id) == ["complaint_update"]


def test_admin_push_goes_to_admin_phones(db, push):
    admin = Login(role="admin", login_id="priveopapa", display_name="Admin")
    db.add(admin)
    db.flush()
    db.add(DeviceToken(login_id=admin.id, token="admin-token-0001", platform="ios"))
    db.commit()
    emit.admin_push(db, "Payment alert", "Marked as paid")
    assert push.sent[0].tokens == ("admin-token-0001",)


def test_reminder_days():
    assert [d for d in range(-10, 8) if emit.reminder_due(d)] == [-7, -1, 1, 3, 5, 7]


def _plan_payment(db, world, due: date, status="Due") -> Payment:
    vehicle = world.vehicles[0]
    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == vehicle.id))
    customer = db.scalar(select(Customer).where(Customer.id == vehicle.customer_id))
    p = Payment(customer_id=customer.id, vehicle_id=vehicle.id, subscription_id=sub.id,
                kind="Plan", description="Plan", amount_rupees=999, status=status,
                due_date=due, cycle_start=due, cycle_end=due + timedelta(days=30))
    db.add(p)
    db.commit()
    return p


def test_renewal_reminders_follow_the_schedule_and_stop(db, world, customer_login, push):
    due = date(2026, 11, 20)
    p = _plan_payment(db, world, due)
    assert emit.renewal_reminders(db, due - timedelta(days=8)) == 0
    assert emit.renewal_reminders(db, due - timedelta(days=7)) == 1
    assert emit.renewal_reminders(db, due - timedelta(days=7)) == 0  # same day again
    assert emit.renewal_reminders(db, due - timedelta(days=1)) == 1
    assert emit.renewal_reminders(db, due) == 0
    assert emit.renewal_reminders(db, due + timedelta(days=1)) == 1
    p.status = "Initiated"  # the customer says they paid: the reminders stop
    db.commit()
    assert emit.renewal_reminders(db, due + timedelta(days=3)) == 0
    p.status = "Over due"  # the admin moves it back: they start again
    db.commit()
    assert emit.renewal_reminders(db, due + timedelta(days=3)) == 1
    assert set(events(db, customer_login.id)) == {"renewal_reminder"}
    assert inbox(db, customer_login.id)[0].ref_type == "payment"


# Cron ----------------------------------------------------------------------------

@pytest.fixture
def cron(crew_client):
    """The app with a CRON_SECRET and a fixed clock."""
    state = {"now": datetime(2026, 11, 13, 10, 0, tzinfo=IST)}
    client = crew_client
    client.app.dependency_overrides[get_cron_settings] = lambda: CronSettings(cron_secret="s3cret")
    client.app.dependency_overrides[get_now] = lambda: (lambda: state["now"])
    client.state = state
    return client


JOBS = ("freeze-due", "payments-generate", "payments-overdue", "renewal-reminders",
        "checkin-notify", "complaints-overdue")


def test_cron_needs_the_secret(cron):
    assert cron.get("/v1/internal/cron/freeze-due").status_code == 401
    wrong = cron.get("/v1/internal/cron/freeze-due", headers={"Authorization": "Bearer nope"})
    assert wrong.status_code == 401
    cron.app.dependency_overrides[get_cron_settings] = lambda: CronSettings(cron_secret="")
    r = cron.get("/v1/internal/cron/freeze-due", headers={"Authorization": "Bearer "})
    assert r.status_code == 503


def test_every_cron_job_runs_and_can_run_again(cron):
    headers = {"Authorization": "Bearer s3cret"}
    for job in JOBS:
        first = cron.get(f"/v1/internal/cron/{job}", headers=headers)
        assert first.status_code == 200, (job, first.text)
        assert first.json()["job"] == job
        again = cron.post(f"/v1/internal/cron/{job}", headers=headers)
        assert again.status_code == 200, (job, again.text)
    assert cron.get("/v1/internal/cron/unknown", headers=headers).status_code == 404


def test_the_cron_jobs_do_their_work(cron, db, world, customer_login, make_crew, new_visit):
    headers = {"Authorization": "Bearer s3cret"}
    ravi = make_crew("9000000010", "Ravi")
    new_visit(assigned=ravi, status="Draft")
    # Freeze at 8 PM.
    cron.state["now"] = datetime(2026, 11, 6, 20, 30, tzinfo=IST)
    r = cron.get("/v1/internal/cron/freeze-due", headers=headers)
    assert r.json()["result"]["frozen"] >= 1
    assert events(db, ravi.login_id) == ["crew_schedule_frozen"]
    # A Due payment past its date becomes Over due.
    due = date(2026, 11, 10)
    p = _plan_payment(db, world, due)
    cron.state["now"] = datetime(2026, 11, 12, 1, 0, tzinfo=IST)
    r = cron.get("/v1/internal/cron/payments-overdue", headers=headers)
    assert r.json()["result"]["marked_overdue"] == 1
    db.expire_all()
    assert db.get(Payment, p.id).status == "Over due"
    # Day 2 after the due date: a reminder (every 2 days from the day before).
    cron.state["now"] = datetime(2026, 11, 11, 10, 0, tzinfo=IST)
    r = cron.get("/v1/internal/cron/renewal-reminders", headers=headers)
    assert r.json()["result"]["sent"] == 1
    r = cron.get("/v1/internal/cron/renewal-reminders", headers=headers)
    assert r.json()["result"]["sent"] == 0
    assert "renewal_reminder" in events(db, customer_login.id)
