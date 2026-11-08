"""SCHS-39: the weekly summary (SCHR-OUT-02, SCHR-INT-17). Read only.

For one service week of a site:

* Exteriors: completed against the mandatory ones (every Exterior job that was
  not skipped), and how many are still open or missed.
* Interiors grouped by their ORIGINAL service week (the ledger rows of the
  week) with the number of overdue days and the completion date, and the
  Interiors that were COMPLETED in the week with the week they belong to. A
  catch-up Interior is one completed in this week for an earlier week.
* Completions on weekdays and on weekend days (`site.weekend_weekdays`).
* Carry-over: Interiors owed from earlier weeks that were still open or were
  done in this week, and Interiors still owed now.
* Missed breaks: the `break_missed` findings of the week.

Everything is computed from the jobs, the ledger and the findings; nothing is
stored (SCHR-OUT-05). Overdue days of an Interior: days from the last day of its
service week to the day it was done, or to `as_of` (today by default) while it is
still owed. A week is the service week that holds the date asked for.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.customers.models import Customer, Vehicle
from app.directory import lookup
from app.directory.site_settings import SettingMissing
from app.identity.service import User
from app.platform import clock
from app.platform.db import get_db
from app.platform.deps import require_role
from app.scheduling import entitlements, service
from app.scheduling.models import (
    SERVICES,
    InteriorEntitlement,
    Job,
    Schedule,
    ScheduleFinding,
    Visit,
)

router = APIRouter(prefix="/v1/admin/scheduling/reports", tags=["scheduling"])

EXTERIOR = SERVICES[0]
BREAK_MISSED = "break_missed"
OPEN_LEDGER = (entitlements.PENDING, entitlements.PLANNED)


class ExteriorTotals(BaseModel):
    due: int
    completed: int
    missed: int
    open: int


class InteriorLine(BaseModel):
    vehicle_id: uuid.UUID
    registration: str
    service_week_start: date
    status: str
    completed_on: date | None
    overdue_days: int
    catch_up: bool


class DayCounts(BaseModel):
    weekday: int
    weekend: int


class CarryOver(BaseModel):
    carried_in: int
    still_owed: int


class WeeklySummary(BaseModel):
    society_id: uuid.UUID
    week_start: date
    week_end: date
    exteriors: ExteriorTotals
    interiors_by_service_week: list[InteriorLine]
    interiors_completed_in_week: list[InteriorLine]
    completions: DayCounts
    catch_up_services: int
    carry_over: CarryOver
    missed_breaks: int


def _weekend_days(db: Session, society_id: uuid.UUID) -> set[int]:
    try:
        return set(lookup.site_setting(db, society_id, "site.weekend_weekdays"))
    except SettingMissing:
        return set()


def _line(row: InteriorEntitlement, registration: str, week_start: date, as_of: date) -> InteriorLine:
    last_day = row.service_week_start + timedelta(days=6)
    end = row.completed_on if row.completed_on is not None else as_of
    return InteriorLine(
        vehicle_id=row.vehicle_id, registration=registration,
        service_week_start=row.service_week_start, status=row.status,
        completed_on=row.completed_on, overdue_days=max(0, (end - last_day).days),
        catch_up=row.service_week_start < week_start)


def weekly_summary(db: Session, society_id: uuid.UUID, on: date,
                   as_of: date | None = None) -> WeeklySummary:
    as_of = as_of or clock.today_ist()
    start = entitlements.week_start(db, on, society_id)
    end = start + timedelta(days=6)

    jobs = [r for r in service.job_rows(
        db, Schedule.society_id == society_id, Visit.date >= start, Visit.date <= end)
        if r["status"] != "Skipped"]
    exteriors = [r for r in jobs if r["service"] == EXTERIOR]
    done = sum(1 for r in exteriors if r["status"] == "Completed")
    missed = sum(1 for r in exteriors if r["status"] in ("Could not complete", "Deferred"))
    exterior = ExteriorTotals(due=len(exteriors), completed=done, missed=missed,
                              open=len(exteriors) - done - missed)
    weekend = _weekend_days(db, society_id)
    finished = [r for r in jobs if r["status"] == "Completed"]
    counts = DayCounts(weekday=sum(1 for r in finished if r["date"].weekday() not in weekend),
                       weekend=sum(1 for r in finished if r["date"].weekday() in weekend))

    ledger = db.execute(
        select(InteriorEntitlement, Vehicle.registration)
        .join(Vehicle, Vehicle.id == InteriorEntitlement.vehicle_id)
        .join(Customer, Customer.id == Vehicle.customer_id)
        .where(func.coalesce(Vehicle.society_id, Customer.society_id) == society_id,
               InteriorEntitlement.status.in_(
                   (entitlements.PENDING, entitlements.PLANNED, entitlements.COMPLETED)))
        .order_by(InteriorEntitlement.service_week_start, Vehicle.registration,
                  InteriorEntitlement.seq)).all()
    by_week = [_line(r, reg or "", start, as_of) for r, reg in ledger if r.service_week_start == start]
    in_week = [_line(r, reg or "", start, as_of) for r, reg in ledger
               if r.completed_on is not None and start <= r.completed_on <= end]
    carried_in = sum(
        1 for r, _ in ledger if r.service_week_start < start and (
            r.status in OPEN_LEDGER or (r.completed_on is not None and r.completed_on >= start)))
    still_owed = sum(1 for r, _ in ledger if r.service_week_start <= start and r.status in OPEN_LEDGER)

    breaks = 0
    for f, _s in db.execute(
            select(ScheduleFinding, Schedule).join(Schedule, Schedule.id == ScheduleFinding.schedule_id)
            .where(Schedule.society_id == society_id, ScheduleFinding.code == BREAK_MISSED,
                   Schedule.start_date <= end, Schedule.end_date >= start)):
        if f.job_id is None:
            breaks += 1
        else:
            day = db.scalar(select(Visit.date).join(Job, Job.visit_id == Visit.id)
                            .where(Job.id == f.job_id))
            breaks += 1 if day is not None and start <= day <= end else 0

    return WeeklySummary(
        society_id=society_id, week_start=start, week_end=end, exteriors=exterior,
        interiors_by_service_week=by_week, interiors_completed_in_week=in_week,
        completions=counts, catch_up_services=sum(1 for ln in in_week if ln.catch_up),
        carry_over=CarryOver(carried_in=carried_in, still_owed=still_owed), missed_breaks=breaks)


@router.get("/weekly", response_model=WeeklySummary)
def weekly(
    society_id: uuid.UUID,
    week_start: date,
    as_of: date | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return weekly_summary(db, society_id, week_start, as_of)
