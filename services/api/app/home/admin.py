"""The admin's home and the read-only day schedule (ADM-ACC-07, BE-19).

Counts come from the module that owns each list, so the number on the home
always matches the list behind it."""
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import MoneyAlert, Payment
from app.billing.service import customer_name, vehicle_label
from app.customers.models import Customer, Vehicle
from app.directory.models import Society
from app.home.schemas import (
    AdminDayCrew,
    AdminDayJob,
    AdminDaySchedule,
    AdminHome,
    AdminHomeSociety,
    DaySummary,
    DaySummaryItem,
    DaySummaryState,
    PaymentToConfirm,
)
from app.identity.models import Login
from app.scheduling import service as scheduling
from app.scheduling.models import Job, Schedule, Visit
from app.scheduling.outcomes import visit_outcomes
from app.support import alerts as support_alerts
from app.support.models import Complaint

PAYMENTS_ON_HOME = 20
UNASSIGNED = "Not assigned"


def admin_home(db: Session) -> AdminHome:
    support_unread = support_alerts.unread_count(db)
    payment_unread = db.scalar(
        select(func.count()).select_from(MoneyAlert).where(MoneyAlert.read_at.is_(None))) or 0
    initiated = (Payment.status == "Initiated", Payment.voided_at.is_(None))
    to_confirm = db.scalar(select(func.count()).select_from(Payment).where(*initiated)) or 0
    payments = db.scalars(
        select(Payment).where(*initiated)
        .order_by(Payment.initiated_at, Payment.created_at).limit(PAYMENTS_ON_HOME)).all()
    cards = []
    for p in payments:
        customer = db.get(Customer, p.customer_id)
        vehicle = db.get(Vehicle, p.vehicle_id) if p.vehicle_id else None
        society = db.get(Society, (vehicle.society_id if vehicle else None)
                         or customer.society_id) if customer else None
        label = ", ".join(x for x in (
            customer_name(customer) if customer else "",
            f"Flat {customer.flat}" if customer and customer.flat else "") if x)
        cards.append(PaymentToConfirm(
            id=str(p.id), customer_label=label, amount_rupees=p.amount_rupees,
            reference=p.description, vehicle=vehicle_label(vehicle),
            society=society.name if society else ""))
    open_complaints = db.scalar(
        select(func.count()).select_from(Complaint).where(Complaint.status != "Resolved")) or 0
    societies = db.scalars(
        select(Society).where(Society.active.is_(True)).order_by(Society.name)).all()
    return AdminHome(
        alert_count=support_unread + payment_unread,
        payments_to_confirm=cards,
        needs_scheduling_count=len(scheduling.needs_scheduling(db, None)),
        support_alert_count=support_unread,
        payment_alert_count=payment_unread,
        payments_to_confirm_count=to_confirm,
        open_complaints_count=open_complaints,
        societies=[AdminHomeSociety(id=str(s.id), name=s.name) for s in societies],
    )


def day_schedule(db: Session, day: date, society_id: uuid.UUID | None) -> AdminDaySchedule:
    """Every job of one date, grouped by crew member. Read only. With a society,
    crew members with no job that day are listed too."""
    where = [Visit.date == day]
    if society_id is not None:
        where.append(Schedule.society_id == society_id)
    rows = scheduling.job_rows(db, *where)
    groups: dict[str | None, AdminDayCrew] = {}
    if society_id is not None:
        crew = scheduling.load_crew(db, society_id)
        names = {r.id: r.display_name for r in db.scalars(
            select(Login).where(Login.id.in_([c.login_id for c in crew.values()])))}
        for c in crew.values():
            groups[str(c.id)] = AdminDayCrew(
                crew_id=str(c.id), crew_name=names.get(c.login_id, ""), role=c.role, jobs=[])
    for r in rows:
        key = str(r["crew_id"]) if r["crew_id"] else None
        if key not in groups:
            groups[key] = AdminDayCrew(
                crew_id=key, crew_name=r["crew_name"] or UNASSIGNED, role=None, jobs=[])
        groups[key].jobs.append(AdminDayJob(
            id=str(r["id"]), time=r["start_time"], end_time=r["end_time"],
            vehicle=r["vehicle"], registration=r["registration"], service=r["service"],
            status=r["status"], late=r["late"]))
    statuses = {r["schedule_status"] for r in rows}
    done = sum(1 for r in rows if r["status"] in ("Completed", "Skipped"))
    left = sum(1 for r in rows if r["status"] in ("Scheduled", "In progress"))
    ordered = sorted(groups.values(), key=lambda g: (g.crew_id is None, g.crew_name))
    return AdminDaySchedule(
        date=day, society_id=str(society_id) if society_id else None,
        schedule_status=(None if not statuses else
                         statuses.pop() if len(statuses) == 1 else "Mixed"),
        total=len(rows), done=done, left=left, crew=ordered)


SUMMARY_LIST_LIMIT = 20
# Visit outcome (WP2) to the state shown. DERIVED: a Cancelled visit whose jobs
# were all skipped is shown as Skipped; any other Cancelled visit stays Cancelled.
_STATE_OF = {
    "Scheduled": "pending",
    "Completed": "completed",
    "Not Completed": "missed",
    "Partially Completed": "partially_completed",
    "Rescheduled": "rescheduled",
    "Cancelled": "cancelled",
}


def day_summary(db: Session, day: date, crew_id: uuid.UUID | None = None,
                vehicle_id: uuid.UUID | None = None,
                society_id: uuid.UUID | None = None,
                registration: str | None = None) -> DaySummary:
    """A-02. Counts the visits of one date by their derived outcome. A missed
    or partial visit is counted and listed, never dropped (C-06)."""
    where = [Visit.date == day]
    if crew_id is not None:
        where.append(Job.crew_id == crew_id)
    if vehicle_id is not None:
        where.append(Visit.vehicle_id == vehicle_id)
    if society_id is not None:
        where.append(Schedule.society_id == society_id)
    if registration:
        # Derived: the portal has no vehicle list, so it filters by registration.
        where.append(func.upper(Vehicle.registration) == registration.strip().upper())
    rows = scheduling.job_rows(db, *where)
    visit_ids = {r["visit_id"] for r in rows}
    derived = visit_outcomes(db, visit_ids)
    all_status: dict = {}
    if visit_ids:
        for vid, status in db.execute(
                select(Job.visit_id, Job.status).where(Job.visit_id.in_(visit_ids))):
            all_status.setdefault(vid, []).append(status)
    by_visit: dict = {}
    for r in rows:  # job_rows is ordered by date then start time
        by_visit.setdefault(r["visit_id"], []).append(r)
    states: dict[str, list[DaySummaryItem]] = {k: [] for k in (
        "completed", "pending", "missed", "partially_completed", "skipped",
        "rescheduled", "cancelled")}
    for vid, jobs in by_visit.items():
        outcome = derived[vid]
        state = _STATE_OF[outcome.outcome]
        if state == "cancelled" and all_status.get(vid) and all(
                x == "Skipped" for x in all_status[vid]):
            state = "skipped"
        crews = sorted({j["crew_name"] for j in jobs if j["crew_name"]})
        times = [j["start_time"] for j in jobs if j["start_time"]]
        # The reason label only; the free-text remark can hold personal data.
        reasons = sorted({m["reason"] for m in outcome.missed if m["reason"]})
        states[state].append(DaySummaryItem(
            id=str(vid), registration=jobs[0]["registration"],
            crew=", ".join(crews) or UNASSIGNED, reason=", ".join(reasons),
            time=min(times) if times else None))
    out = {k: DaySummaryState(count=len(v), items=v[:SUMMARY_LIST_LIMIT],
                              more=max(0, len(v) - SUMMARY_LIST_LIMIT))
           for k, v in states.items()}
    return DaySummary(date=day, total=len(by_visit), **out)
