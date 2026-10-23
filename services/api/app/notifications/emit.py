"""Events other modules emit, in one place.

A module calls one function here from the place where something happened
(each call is a one-line hook marked `# notify hook`). This module decides
who is told, what the message says, and whether the person's switch allows
it, then goes through `NotificationService` and the `PushSender` adapter.

Rules kept here:
- Nothing a hook does may break the action it hooks into: every function
  catches its own errors and logs them.
- No crew message has a customer's name or mobile number in it.
- Customer events follow the customer's switches (NOTIF-03). Crew events and
  admin alerts cannot be switched off.
- Calling twice for the same thing sends once (a `dedupe_key`).

The imports of the other modules are inside the functions, because those
modules import this one.
"""
import functools
import logging
import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.notifications.push import get_default_sender
from app.notifications.service import NotificationService

log = logging.getLogger("priveo.notifications")

REMINDER_FIRST_DAYS = 7  # NOTIF-05: one week before the renewal date
REMINDER_SECOND_DAYS = 1  # then one day before, then every 2 days


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(db: Session, *args, **kwargs):
        try:
            return fn(db, *args, **kwargs)
        except Exception:
            log.exception("notification %s failed; the action it follows is kept",
                          fn.__name__)
            try:
                db.rollback()
            except Exception:
                log.exception("rollback after a failed notification also failed")
            return None

    return wrapper


def _service(db: Session) -> NotificationService:
    return NotificationService(db, get_default_sender())


def _show(day: date) -> str:
    return day.strftime("%d-%b-%y")


def _vehicle_text(vehicle) -> str:
    return " ".join(p for p in (vehicle.model, vehicle.registration) if p) or "your car"


# People ---------------------------------------------------------------------

def crew_login_ids(db: Session, crew_id: uuid.UUID | None) -> list[uuid.UUID]:
    """The crew member's login and the logins of the Trainees paired with
    them, who see the same jobs (CRW-SCH-10, CRW-NOT-05)."""
    from app.scheduling.models import SchedulingCrew

    if crew_id is None:
        return []
    member = db.get(SchedulingCrew, crew_id)
    if member is None or not member.active:
        return []
    ids = [member.login_id]
    ids += list(db.scalars(select(SchedulingCrew.login_id).where(
        SchedulingCrew.paired_member_id == crew_id, SchedulingCrew.active.is_(True))))
    return ids


def _customer_login(db: Session, vehicle_id: uuid.UUID) -> uuid.UUID | None:
    from app.customers.models import Customer, Vehicle

    return db.scalar(select(Customer.login_id).join(Vehicle, Vehicle.customer_id == Customer.id)
                     .where(Vehicle.id == vehicle_id))


def _tell_crew(db: Session, crew_id: uuid.UUID | None, event: str, title: str, body: str,
               ref_id: str | None, key: str | None = None) -> int:
    """Pushes and saves one crew message for the member and their Trainees.
    `body` is built by the caller and holds no customer name or mobile."""
    sent = 0
    for login_id in crew_login_ids(db, crew_id):
        row = _service(db).notify(
            login_id, event, title, body, ref_type="job" if ref_id else None, ref_id=ref_id,
            dedupe_key=f"{key}:{login_id}" if key else None)
        sent += 1 if row is not None else 0
    return sent


def _alert_once(db: Session, kind: str, title: str, body: str, ref_type: str, ref_id: str,
                *, once: bool = True) -> None:
    """An admin alert (ADM-SCH-24) saved for the bell, with the phone push and
    the email through `app.support.alerts`."""
    from app.notifications.bridge import SupportNotifier
    from app.support import alerts
    from app.support.models import AdminAlert

    if once and db.scalar(select(AdminAlert.id).where(
            AdminAlert.kind == kind, AdminAlert.ref_id == ref_id)):
        return
    alerts.raise_alert(db, kind, title, body, ref_type=ref_type, ref_id=ref_id,
                       push=SupportNotifier(db))


def admin_push(db: Session, title: str, body: str = "", data: dict[str, str] | None = None
               ) -> None:
    """A phone push to every admin (ADM-ACC-09). The bell is the alert list.
    It saves nothing and never rolls back, so a module may call it in the
    middle of its own transaction."""
    from app.identity.models import Login

    try:
        ids = list(db.scalars(
            select(Login.id).where(Login.role == "admin", Login.active.is_(True))))
        if ids:
            _service(db).push_only(ids, title, body, data or {"event": "admin_alert"})
    except Exception:
        log.exception("admin push failed")


# Visits and jobs ---------------------------------------------------------------

@_safe
def job_status_changed(db: Session, job) -> None:
    """Called after the crew module (or the Manager) changes a job's status.
    NOTIF-02 Service completed, NOTIF-04 skipped by operations, ADM-CNC-04."""
    if job.status == "Completed":
        _service_completed(db, job)
    elif job.status == "Skipped":
        _skipped_by_operations(db, job)
    elif job.status == "Could not complete":
        _job_missed(db, job)


def _visit_context(db: Session, job):
    from app.customers.models import Vehicle
    from app.scheduling.models import Visit

    visit = db.get(Visit, job.visit_id)
    vehicle = db.get(Vehicle, visit.vehicle_id)
    return visit, vehicle


def _service_completed(db: Session, job) -> None:
    visit, vehicle = _visit_context(db, job)
    addon = job.addon_request_id is not None or job.addon_booking_id is not None
    # A visit is Completed only when all its jobs are done or skipped. An
    # add-on job is separate from the day's visit and tells on its own
    # (CRW-SVC-09, ADD-13).
    if not addon and visit.status != "Completed":
        return
    login_id = _customer_login(db, visit.vehicle_id)
    if login_id is None:
        return
    key = f"completed:job:{job.id}" if addon else f"completed:visit:{visit.id}"
    what = f"{job.service} for {_vehicle_text(vehicle)}" if addon else _vehicle_text(vehicle)
    _service(db).notify(
        login_id, "service_completed", "Service completed",
        f"{what} was done on {_show(visit.date)}. Tap to see the proof.",
        visit_id=str(visit.id), dedupe_key=key)


def _skipped_by_operations(db: Session, job) -> None:
    visit, vehicle = _visit_context(db, job)
    login_id = _customer_login(db, visit.vehicle_id)
    if login_id is not None:
        _service(db).notify(
            login_id, "service_skipped", "Service skipped",
            f"The visit for {_vehicle_text(vehicle)} on {_show(visit.date)} was skipped "
            "by Priveo.", visit_id=str(visit.id), dedupe_key=f"skipped:visit:{visit.id}")
    _job_removed(db, job, visit, vehicle, "Job removed",
                 "was skipped by operations")


def _job_missed(db: Session, job) -> None:
    from app.directory.models import Society
    from app.scheduling.models import Schedule

    visit, vehicle = _visit_context(db, job)
    schedule = db.get(Schedule, visit.schedule_id)
    society = db.get(Society, schedule.society_id) if schedule else None
    _alert_once(
        db, "job_missed", "A job could not be completed",
        f"{job.service} for {_vehicle_text(vehicle)}"
        f"{' at ' + society.name if society else ''} on {_show(visit.date)}.",
        "job", str(job.id))


def _job_removed(db: Session, job, visit, vehicle, title: str, why: str) -> int:
    return _tell_crew(
        db, job.crew_id, "crew_job_removed", title,
        f"{job.service} for {_vehicle_text(vehicle)} on {_show(visit.date)} {why}. "
        "It is off your cards.", str(job.id))


@_safe
def schedules_frozen(db: Session, schedule_ids: list[uuid.UUID]) -> None:
    """CRW-NOT-01: each crew member with jobs in a frozen schedule is told.
    One push for each crew member and freeze, not one for each job."""
    from app.scheduling.models import Job, Schedule, Visit

    for schedule_id in schedule_ids:
        schedule = db.get(Schedule, schedule_id)
        if schedule is None:
            continue
        stamp = schedule.frozen_at.isoformat() if schedule.frozen_at else ""
        rows = db.execute(
            select(Job.crew_id, func.count(Job.id), func.min(Visit.date), func.max(Visit.date))
            .join(Visit, Visit.id == Job.visit_id)
            .where(Visit.schedule_id == schedule_id, Job.crew_id.is_not(None),
                   Job.status == "Scheduled")
            .group_by(Job.crew_id)).all()
        for crew_id, count, first, last in rows:
            span = _show(first) if first == last else f"{_show(first)} to {_show(last)}"
            noun = "job" if count == 1 else "jobs"
            for login_id in crew_login_ids(db, crew_id):
                _service(db).notify(
                    login_id, "crew_schedule_frozen", "Your schedule is ready",
                    f"You have {count} {noun} on {span}. Open your cards.",
                    ref_type="schedule", ref_id=str(schedule_id),
                    dedupe_key=f"frozen:{schedule_id}:{stamp}:{login_id}")


def assignment_snapshot(db: Session, schedule) -> dict[uuid.UUID, uuid.UUID | None] | None:
    """Who has each job of a Frozen schedule, before a re-run. None when the
    schedule is a Draft (the crew do not see drafts)."""
    from app.scheduling.models import Job, Visit

    if schedule.status != "Frozen":
        return None
    return dict(db.execute(
        select(Job.id, Job.crew_id).join(Visit, Visit.id == Job.visit_id)
        .where(Visit.schedule_id == schedule.id)).all())


@_safe
def late_assignments(db: Session, schedule, before) -> None:
    """After a run on a Frozen schedule: tell the crew who got a job
    (CRW-NOT-04) or lost one, and alert the admin (ADM-SCH-27, ADM-SCH-28)."""
    from app.customers.models import Vehicle
    from app.scheduling.models import Job, Visit

    if before is None:
        return
    rows = db.execute(
        select(Job, Visit).join(Visit, Visit.id == Job.visit_id)
        .where(Visit.schedule_id == schedule.id, Job.status == "Scheduled")).all()
    for job, visit in rows:
        previous = before.get(job.id)
        if job.id in before and previous == job.crew_id:
            continue  # nothing changed for this job
        # A job the run just created and nobody could take falls through to
        # the "needs scheduling" alert.
        vehicle = db.get(Vehicle, visit.vehicle_id)
        label = f"{job.service} for {_vehicle_text(vehicle)} on {_show(visit.date)}"
        if previous is not None and previous != job.crew_id:
            _tell_crew(db, previous, "crew_job_removed", "Job removed",
                       f"{label} was moved off your cards.", str(job.id),
                       key=f"removed:{job.id}:{previous}")
        if job.crew_id is not None:
            at = f" at {job.start_minute // 60:02d}:{job.start_minute % 60:02d}" \
                if job.start_minute is not None else ""
            _tell_crew(db, job.crew_id, "crew_job_assigned", "New job on your cards",
                       f"{label}{at} was added to your cards.", str(job.id),
                       key=f"assigned:{job.id}:{job.crew_id}")
            _alert_once(db, "auto_assigned", "Visit assigned after the freeze",
                        f"{label} was given to a crew member automatically.", "job",
                        str(job.id))
        else:
            _alert_once(db, "needs_scheduling", "A visit needs scheduling",
                        f"{label} has no crew member.", "job", str(job.id))


@_safe
def job_taken_off(db: Session, job, previous_crew_id: uuid.UUID | None) -> None:
    """The admin took a job off a crew member on a Frozen schedule
    (ADM-SCH-29): the crew member is told it is off their cards."""
    from app.scheduling.models import Schedule

    if previous_crew_id is None:
        return
    visit, vehicle = _visit_context(db, job)
    schedule = db.get(Schedule, visit.schedule_id)
    if schedule is None or schedule.status != "Frozen":
        return
    _tell_crew(db, previous_crew_id, "crew_job_removed", "Job removed",
               f"{job.service} for {_vehicle_text(vehicle)} on {_show(visit.date)} was taken "
               "off your cards.", str(job.id), key=f"removed:{job.id}:{previous_crew_id}")


@_safe
def job_reassigned(db: Session, job) -> None:
    """CRW-NOT-05: both crew members, and a paired Trainee, are told when a
    Manager moves a job."""
    from app.visits.models import JobReassignment

    move = db.scalar(select(JobReassignment).where(JobReassignment.job_id == job.id)
                     .order_by(JobReassignment.at.desc()))
    if move is None:
        return
    visit, vehicle = _visit_context(db, job)
    label = f"{job.service} for {_vehicle_text(vehicle)} on {_show(visit.date)}"
    if move.from_crew_id is not None:
        _tell_crew(db, move.from_crew_id, "crew_job_reassigned", "Job moved to someone else",
                   f"{label} was moved off your cards.", str(job.id),
                   key=f"reassigned:{move.id}:from")
    _tell_crew(db, move.to_crew_id, "crew_job_reassigned", "A job was given to you",
               f"{label} was added to your cards.", str(job.id),
               key=f"reassigned:{move.id}:to")


@_safe
def queue_changed(db: Session, crew_id: uuid.UUID, day: date, text: str, key: str) -> None:
    """B-06: the crew member (and a paired Trainee) is told when the admin
    reorders or unlocks their day's queue. The text holds no customer detail."""
    _tell_crew(db, crew_id, "crew_queue_changed", "Your job order changed",
               f"{text} ({_show(day)})", None, key=f"queue:{key}")


# Skip, pause and add-ons ----------------------------------------------------


@_safe
def cutoff_requested(db: Session, change, vehicle) -> None:
    _alert_once(db, "cutoff_requested", "Cutoff change requested",
                f"{_vehicle_text(vehicle)} on {_show(change.start_date)}: "
                f"finish by {change.cutoff_time:%H:%M}.", "cutoff_request", str(change.id))

@_safe
def customer_skipped(db: Session, vehicle, day: date, *, actor: str = "customer") -> None:
    """NOTIF-04: the customer gets "Service skipped" when they skip a visit
    themselves too. ADM-CUS-14 keeps plan/preferences edits silent; explicit
    customer/admin skips and operations outcomes retain the skip notification."""
    login_id = _customer_login(db, vehicle.id)
    if login_id is None:
        return
    _service(db).notify(
        login_id, "service_skipped", "Service skipped",
        f"The visit for {_vehicle_text(vehicle)} on {_show(day)} is skipped"
        f"{' by Priveo' if actor == 'admin' else ''}.")


@_safe
def visits_removed(db: Session, vehicle_id: uuid.UUID, start: date, end: date,
                   reason: str) -> None:
    """CRW-NOT-02, CRW-SCH-08, ADM-SCH-21: jobs of a Frozen schedule that a
    skip or a pause just removed. `reason` is "skip" or "pause"."""
    from app.customers.models import Vehicle
    from app.scheduling.models import Job, Schedule, Visit

    vehicle = db.get(Vehicle, vehicle_id)
    rows = db.execute(
        select(Job, Visit).join(Visit, Visit.id == Job.visit_id)
        .join(Schedule, Schedule.id == Visit.schedule_id)
        .where(Visit.vehicle_id == vehicle_id, Visit.date >= start, Visit.date <= end,
               Schedule.status == "Frozen", Job.status == "Skipped",
               Job.crew_id.is_not(None))).all()
    why = "was skipped by the customer" if reason == "skip" else "is paused"
    for job, visit in rows:
        _job_removed(db, job, visit, vehicle, "Job removed", why)
    if rows:
        first = min(v.date for _, v in rows)
        _alert_once(
            db, f"{reason}_after_freeze",
            "Skip after the freeze" if reason == "skip" else "Pause after the freeze",
            f"{_vehicle_text(vehicle)}: {len(rows)} job(s) from {_show(first)} were removed "
            "from the crew's cards.", "vehicle", str(vehicle_id), once=False)


@_safe
def addon_cancelled(db: Session, booking) -> None:
    """CRW-SCH-08, ADM-SCH-31: a cancelled add-on's job leaves the crew's
    cards. Works on the job an add-on request created, if the scheduler made
    one; an add-on that was never scheduled changes nothing here."""
    from app.customers.models import Vehicle
    from app.scheduling.models import Job, Schedule, Visit
    from app.scheduling.service import refresh_visit_status

    rows = db.execute(
        select(Job, Visit, Schedule).join(Visit, Visit.id == Job.visit_id)
        .join(Schedule, Schedule.id == Visit.schedule_id)
        .where(Job.addon_booking_id == booking.id, Job.status == "Scheduled")).all()
    for job, visit, schedule in rows:
        vehicle = db.get(Vehicle, visit.vehicle_id)
        job.status = "Skipped"
        db.commit()
        refresh_visit_status(db, visit.id)
        db.commit()
        if schedule.status == "Frozen":
            _job_removed(db, job, visit, vehicle, "Job removed", "was cancelled")
            _alert_once(db, "addon_cancelled_after_freeze", "Add-on cancelled after the freeze",
                        f"{job.service} for {_vehicle_text(vehicle)} on {_show(visit.date)}.",
                        "job", str(job.id))


# Payments ---------------------------------------------------------------------

def reminder_due(offset_days: int) -> bool:
    """NOTIF-05. `offset_days` is today minus the renewal date: a reminder one
    week before (-7), one day before (-1), then every 2 days (1, 3, 5, ...)."""
    if offset_days in (-REMINDER_FIRST_DAYS, -REMINDER_SECOND_DAYS):
        return True
    return offset_days > 0 and offset_days % 2 == 1


@_safe
def renewal_reminders(db: Session, today: date) -> int:
    """The daily job: "Renewal reminder" for each plan payment still Due or
    Over due on an Active subscription. It stops by itself when the payment
    becomes Initiated or Received or the subscription Inactive, and starts
    again if the admin moves the payment back to Due or Over due (ADM-PAY-07),
    with no extra message. Safe to run again the same day."""
    from app.billing.models import Payment
    from app.customers.models import Customer, Subscription

    rows = db.execute(
        select(Payment, Customer.login_id)
        .join(Customer, Customer.id == Payment.customer_id)
        .join(Subscription, Subscription.id == Payment.subscription_id)
        .where(Payment.kind == "Plan", Payment.status.in_(("Due", "Over due")),
               Payment.voided_at.is_(None), Subscription.status == "Active")).all()
    sent = 0
    for payment, login_id in rows:
        if not reminder_due((today - payment.due_date).days):
            continue
        when = f"is due on {_show(payment.due_date)}" if payment.due_date >= today \
            else f"was due on {_show(payment.due_date)}"
        row = _service(db).notify(
            login_id, "renewal_reminder", "Renewal reminder",
            f"Your plan payment of Rs {payment.amount_rupees} {when}. Pay now to keep "
            "your service going.", ref_type="payment", ref_id=str(payment.id),
            dedupe_key=f"reminder:{payment.id}:{today.isoformat()}")
        sent += 1 if row is not None else 0
    return sent


def today_in_india(now: datetime) -> date:
    from app.platform.clock import IST

    return now.astimezone(IST).date()
