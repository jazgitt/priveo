"""The Interior entitlement ledger (scheduler rules v1.2, SCHS-24).

Every service week a subscription touches owes the car one Interior
(SCHR-INT-06, INT-20). Each owed Interior is a row of `interior_entitlements`:

    Pending    owed, not yet planned
    Planned    a job exists (the row keeps the job)
    Completed  done, with the job and the date
    Waived     not owed: the whole week was paused (SCHR-INT-21)
    Cancelled  the subscription ended

A deferral returns Planned to Pending and keeps the service week (SCHR-INT-11).
An operational miss stays owed; a one-day customer skip changes nothing.

This module is a plain service over the tables. Nothing in the planner reads
it yet, so it changes no demand. The caller commits; functions only flush.
The week start and the count a week owes are settings (`schedule.service_week_start`,
`schedule.interior_entitlement_per_week`), never constants here.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.models import ScheduleChange
from app.customers.models import Customer, Subscription, Vehicle
from app.directory import site_settings
from app.directory.models import Plan
from app.scheduling.models import InteriorEntitlement, Job

INTERIOR = "Cleaning-Internal"
PENDING, PLANNED, COMPLETED, WAIVED, CANCELLED = (
    "Pending", "Planned", "Completed", "Waived", "Cancelled")
WAIVED_PAUSED = "paused"
_OPEN = (PENDING, PLANNED)


# ---- the service week (SCHR-PAR-13) ---------------------------------------

def society_of(db: Session, vehicle_id: uuid.UUID) -> uuid.UUID:
    """The society a car belongs to: its own, else its customer's (legacy rows)."""
    vehicle = db.get(Vehicle, vehicle_id)
    customer = db.get(Customer, vehicle.customer_id)
    return vehicle.society_id or customer.society_id


def week_start(db: Session, day: date, society_id: uuid.UUID) -> date:
    """The first date of the service week that holds `day`, for the site's own
    `schedule.service_week_start` (its value, else the global one)."""
    first = int(site_settings.read(db, society_id, "schedule.service_week_start"))
    return day - timedelta(days=(day.weekday() - first) % 7)


def _weeks(db: Session, first: date, through: date, society_id: uuid.UUID) -> list[date]:
    out, week = [], week_start(db, first, society_id)
    while week <= through:
        out.append(week)
        week += timedelta(days=7)
    return out


# ---- which plan owes an Interior ------------------------------------------

def _plan_on(db: Session, sub: Subscription, day: date) -> Plan | None:
    plan_id = (sub.pending_plan_id
               if sub.pending_plan_id and sub.pending_from and day >= sub.pending_from
               else sub.plan_id)
    return db.get(Plan, plan_id) if plan_id else None


def _includes_interior(db: Session, sub: Subscription, day: date) -> bool:
    plan = _plan_on(db, sub, day)
    return plan is None or plan.includes_interior  # no plan: as the demand code treats it


def _owes(db: Session, sub: Subscription, week: date) -> bool:
    """A week owes an Interior when the plan includes it on any day of the week
    the subscription touches (SCHR-INT-20, INT-23)."""
    first = max(week, sub.first_service_date)
    return any(_includes_interior(db, sub, first + timedelta(days=i))
               for i in range((week + timedelta(days=7) - first).days))


def owes(db: Session, sub: Subscription, week: date) -> bool:
    """Whether the plan owes an Interior for the service week (read by the customer calendar)."""
    return _owes(db, sub, week)


def rows_for_week(db: Session, vehicle_id: uuid.UUID, week: date) -> list[InteriorEntitlement]:
    return list(db.scalars(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == vehicle_id,
        InteriorEntitlement.service_week_start == week).order_by(InteriorEntitlement.seq)))


# ---- creation (SCHR-INT-19) -----------------------------------------------

def ensure(db: Session, sub: Subscription, through: date,
           since: date | None = None) -> list[InteriorEntitlement]:
    """Create the missing rows for each service week from the week of the first
    service date (or of `since`, when it is later: no debt for weeks before it)
    to the week of `through`. Repeatable: a second run adds nothing. Returns the
    rows it created."""
    if sub.status != "Active":
        return []
    society_id = society_of(db, sub.vehicle_id)
    count = int(site_settings.read(db, society_id, "schedule.interior_entitlement_per_week"))
    have = {(r.service_week_start, r.seq) for r in db.scalars(
        select(InteriorEntitlement).where(InteriorEntitlement.vehicle_id == sub.vehicle_id))}
    created = []
    for week in _weeks(db, max(sub.first_service_date, since or sub.first_service_date), through,
                        society_id):
        if not _owes(db, sub, week):
            continue
        for seq in range(1, count + 1):
            if (week, seq) in have:
                continue
            row = InteriorEntitlement(subscription_id=sub.id, vehicle_id=sub.vehicle_id,
                                      service_week_start=week, seq=seq, status=PENDING)
            db.add(row)
            created.append(row)
    db.flush()
    return created


# ---- waiver (SCHR-INT-21) -------------------------------------------------

def _paused_days(db: Session, vehicle_id: uuid.UUID, start: date, end: date) -> set[date]:
    days: set[date] = set()
    for change in db.scalars(select(ScheduleChange).where(
            ScheduleChange.vehicle_id == vehicle_id, ScheduleChange.kind == "pause",
            ScheduleChange.status == "Active",
            ScheduleChange.start_date <= end, ScheduleChange.end_date >= start)):
        d = max(change.start_date, start)
        while d <= min(change.end_date, end):
            days.add(d)
            d += timedelta(days=1)
    return days


def refresh_waivers(db: Session, sub: Subscription) -> None:
    """Waive a Pending week that is fully paused; return a week waived for a
    pause that no longer covers it to Pending. Completed, Planned and
    Cancelled rows are left alone. A one-day skip or an operational miss
    changes nothing: the row stays owed."""
    for row in db.scalars(select(InteriorEntitlement).where(
            InteriorEntitlement.vehicle_id == sub.vehicle_id,
            InteriorEntitlement.status.in_((PENDING, WAIVED)))):
        first = max(row.service_week_start, sub.first_service_date)
        end = row.service_week_start + timedelta(days=6)
        wanted = {first + timedelta(days=i) for i in range((end - first).days + 1)}
        paused = wanted <= _paused_days(db, sub.vehicle_id, first, end)
        if paused and row.status == PENDING:
            row.status, row.waived_reason = WAIVED, WAIVED_PAUSED
        elif not paused and row.status == WAIVED and row.waived_reason == WAIVED_PAUSED:
            row.status, row.waived_reason = PENDING, None
    db.flush()


def cancel_open(db: Session, sub: Subscription, from_day: date) -> None:
    """The subscription ended: its Pending and Planned rows for service weeks
    starting on or after `from_day` become Cancelled."""
    for row in db.scalars(select(InteriorEntitlement).where(
            InteriorEntitlement.vehicle_id == sub.vehicle_id,
            InteriorEntitlement.status.in_(_OPEN),
            InteriorEntitlement.service_week_start >= from_day)):
        row.status, row.job_id = CANCELLED, None
    db.flush()


# ---- reading and moving a row --------------------------------------------

def claim(db: Session, vehicle_id: uuid.UUID, week: date) -> InteriorEntitlement | None:
    """The next Pending row of a service week, or None when the week owes no
    more. A week is never planned past its count (SCHR-INT-06)."""
    return db.scalar(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == vehicle_id,
        InteriorEntitlement.service_week_start == week,
        InteriorEntitlement.status == PENDING).order_by(InteriorEntitlement.seq))


def oldest_owed(db: Session, vehicle_id: uuid.UUID) -> InteriorEntitlement | None:
    """The oldest Pending row of the car: the carry-forward (SCHR-INT-21)."""
    return db.scalar(select(InteriorEntitlement).where(
        InteriorEntitlement.vehicle_id == vehicle_id, InteriorEntitlement.status == PENDING)
        .order_by(InteriorEntitlement.service_week_start, InteriorEntitlement.seq))


def uses_entitlement(job: Job) -> bool:
    """Only the plan's own Interior uses the entitlement. An Interior bought
    as an extra, a Deep Spa and Exterior do not (SCHR-INT-22)."""
    return (job.service == INTERIOR and job.addon_request_id is None
            and job.addon_booking_id is None)


def plan(db: Session, row: InteriorEntitlement, job: Job) -> None:
    """Pending to Planned: a job exists. The job carries the service week."""
    row.status, row.job_id = PLANNED, job.id
    job.service_week_start = row.service_week_start
    db.flush()


def defer(db: Session, row: InteriorEntitlement) -> None:
    """Planned back to Pending, keeping the service week."""
    row.status, row.job_id, row.completed_on = PENDING, None, None
    db.flush()


def complete(db: Session, row: InteriorEntitlement, job: Job, on: date) -> None:
    """Done: the row keeps the job and the date, and the original week."""
    row.status, row.job_id, row.completed_on = COMPLETED, job.id, on
    job.service_week_start = row.service_week_start
    db.flush()
