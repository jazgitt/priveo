"""Ledger-driven Interior demand (SCHS-36, SCHR-INT-01, INT-05, INT-26, EXT-11).

At `scheduler.rules_version` 2 an Interior is planned from the entitlement
ledger, not from the customer's interior care weekday:

* The weekday Interior items of `build_demand` are removed from the demand
  (this provider changes the list it is given; the plan's own Interior only.
  Add-on Interiors, Deep Spa and a next-day retry are not touched).
* For each Active car, the ledger rows of the weeks the period touches are
  created (`entitlements.ensure`, no debt before the period) and fully paused
  weeks are waived.
* Each Pending row of a service week up to the week of a day can be planned on
  that day (INT-01). Rows are taken oldest week first. A row is planned on a
  day of its own week when it can; an overdue row (an older week) goes to the
  first feasible day (INT-13). Among the days of the row's own week, the car's
  preferred day (the interior care day, or the Interior days of a Weekly or
  Cycle pattern, INT-05, INT-26) is chosen if it is feasible; otherwise the
  first feasible day. The preference never removes the entitlement. Weekdays
  come before the weekend when the preference does not decide (SCHS-46).
* A day is feasible when the car is served that day (not before its first
  service date, not skipped or paused), the site has a working slot for the
  Interior that weekday and the car has no other Interior that day (HARD-11).
  A row whose job was missed or deferred is tried again on a later day
  (SCHR-DEF-02). Whether a cleaner has time is the solver's question: a job that does not fit
  stays unassigned and its row stays Planned (DERIVED).
* A Planned row whose job is in this schedule and still open is shown again on
  its day, so a re-run keeps it. A Planned row whose job is gone (Skipped or
  missing) goes back to Pending.

The row of a new job is linked after the day is solved
(`post_solve/entitlement_link.py`); this module only records the choice in
`ctx.interior_rows` as {(vehicle_id, day): row_id}.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func, select

from app.customers.models import WEEKDAYS, Customer, Subscription, Vehicle
from app.customers.schedule_pattern import day_flags, patterns_for
from app.directory import lookup
from app.scheduling import entitlements
from app.scheduling.models import InteriorEntitlement, Job, Schedule, Visit

ORDER = 40
INTERIOR = entitlements.INTERIOR
_OPEN = ("Scheduled", "In progress")
# Derived (tester rule 2, 18.5): an actual Interior on the preferred day or up to
# this many days later, within the plan week, is a small gap and keeps the
# preferred day. Anything else holds the Interior as optional on the preferred day.
SMALL_GAP_DAYS = 2
HELD_NOTE = "Preferred Interior day moved: last Interior on {when}"


def _is_plan_interior(item) -> bool:
    return (item.service == INTERIOR and item.addon_request_id is None
            and item.addon_booking_id is None and item.source_job_id is None)


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def provide(ctx, demand: list):
    from app.scheduling import service

    db = ctx.db
    sched: Schedule = ctx.schedule
    days = _days(sched.start_date, sched.end_date)
    ctx.interior_rows = {}
    ctx.interior_held = {}  # (vehicle id, day) -> note: optional, Unscheduled (18.5)
    demand[:] = [d for d in demand if not _is_plan_interior(d)]

    interior_open = None
    for slot in lookup.working_slots(db, sched.society_id, INTERIOR):
        interior_open = (interior_open or set()) | set(slot.days)

    redo = {}  # vehicle -> Interior retries already in the demand (they cover a row)
    for item in demand:
        if item.service == INTERIOR and item.source_job_id is not None \
                and item.addon_request_id is None and item.addon_booking_id is None:
            redo.setdefault(item.vehicle_id, []).append(item.day)

    jobs = {}  # vehicle -> Interior jobs of this schedule: (job, visit date)
    for job, visit in db.execute(
            select(Job, Visit).join(Visit, Visit.id == Job.visit_id)
            .where(Visit.schedule_id == sched.id, Job.service == INTERIOR,
                   Job.addon_request_id.is_(None), Job.addon_booking_id.is_(None))):
        jobs.setdefault(visit.vehicle_id, []).append((job, visit.date))

    weekend = {int(d) for d in ctx.setting("site.weekend_weekdays")}
    extra = []
    cars = db.execute(
        select(Subscription, Vehicle)
        .join(Vehicle, Subscription.vehicle_id == Vehicle.id)
        .join(Customer, Vehicle.customer_id == Customer.id)
        .where(func.coalesce(Vehicle.society_id, Customer.society_id) == sched.society_id,
               Subscription.status == "Active", Vehicle.active.is_(True))
        .order_by(Vehicle.created_at, Vehicle.id)).all()
    patterns = patterns_for(db, [s.id for s, _ in cars])
    for sub, vehicle in cars:
        entitlements.ensure(db, sub, days[-1], since=days[0])
        entitlements.refresh_waivers(db, sub)
        off, cutoffs = service._customer_changes(db, vehicle.id, days)
        default_cutoff = service.minutes_of(sub.cutoff_time)
        mine = jobs.get(vehicle.id, [])
        rows = list(db.scalars(select(InteriorEntitlement).where(
            InteriorEntitlement.vehicle_id == vehicle.id,
            InteriorEntitlement.status.in_((entitlements.PENDING, entitlements.PLANNED)))
            .order_by(InteriorEntitlement.service_week_start, InteriorEntitlement.seq)))
        used: set[date] = {d for _j, d in mine if _j.status != "Skipped"}

        def cutoff_of(day: date, c=cutoffs, dflt=default_cutoff):
            return c.get(day, dflt)

        pending = []
        for row in rows:
            if row.status == entitlements.PENDING:
                pending.append(row)
                continue
            held = next(((j, d) for j, d in mine if j.id == row.job_id), None)
            if held is None:
                if row.job_id is None or db.get(Job, row.job_id) is None:
                    entitlements.defer(db, row)
                    pending.append(row)
                continue  # planned in another schedule: not this run's business
            job, day = held
            if job.status == "Skipped":
                entitlements.defer(db, row)
                used.discard(day)
                pending.append(row)
            elif job.status == "Scheduled":
                extra.append(_demand(service, day, vehicle.id, cutoff_of(day)))
        # Retries and hand placements already in the plan cover the oldest rows.
        linked = set(db.scalars(select(InteriorEntitlement.job_id).where(
            InteriorEntitlement.vehicle_id == vehicle.id,
            InteriorEntitlement.job_id.is_not(None))))
        covered = len(redo.get(vehicle.id, [])) + sum(
            1 for j, _d in mine if j.manual and j.status in _OPEN and j.id not in linked)
        used |= set(redo.get(vehicle.id, []))
        # A held Interior keeps its day so the next run holds it again (18.5).
        held_prefix = HELD_NOTE.split(":", 1)[0]
        used -= {d for j, d in mine if (j.note or "").startswith(held_prefix)}
        pattern = patterns.get(sub.id)
        last_week = entitlements.week_start(db, days[-1])
        # A job of the week that was not done (missed or deferred) is tried again
        # on a later day, never on or before the day it failed.
        failed = {}
        for j, d in mine:
            if j.status in ("Could not complete", "Deferred") and j.service_week_start:
                failed[j.service_week_start] = max(failed.get(j.service_week_start, d), d)
        for row in pending[covered:]:
            if row.service_week_start > last_week:
                continue
            after = failed.get(row.service_week_start, date.min)
            feasible = [
                d for d in days
                if d >= sub.first_service_date and d not in off and d not in used and d > after
                and entitlements.week_start(db, d) >= row.service_week_start
                and (interior_open is None or d.weekday() in interior_open)]
            if not feasible:
                continue
            own = [d for d in feasible if entitlements.week_start(db, d) == row.service_week_start]
            pool = own or feasible
            # Weekdays before the weekend (INT-10), Derived: the weekend is the
            # fallback. An overdue row (no day of its own week) takes the first
            # feasible weekday and ignores the car's preferred day (INT-13).
            first = next((d for d in pool if d.weekday() not in weekend), pool[0])
            day = first if not own else next(
                (d for d in pool if _prefers(db, sub, pattern, d)), first)
            if own and _prefers(db, sub, pattern, day):
                last = _last_actual_in_week(db, vehicle.id, row.service_week_start)
                if last is not None and not 0 <= (last - day).days <= SMALL_GAP_DAYS:
                    # Held: optional on the preferred day, shown as Unscheduled (18.5).
                    ctx.interior_held[(vehicle.id, day)] = HELD_NOTE.format(when=last.strftime("%d-%b-%y"))
                    used.add(day)
                    extra.append(_demand(service, day, vehicle.id, cutoff_of(day)))
                    continue
            used.add(day)
            ctx.interior_rows[(vehicle.id, day)] = row.id
            extra.append(_demand(service, day, vehicle.id, cutoff_of(day)))
    return extra


def _demand(service, day: date, vehicle_id: uuid.UUID, cutoff: int | None):
    return service.Demand(day, vehicle_id, INTERIOR, cutoff)


def _prefers(db, sub: Subscription, pattern, day: date) -> bool:
    """The car's preferred Interior day: a tie-break only (INT-05, INT-26)."""
    if pattern is None:
        return bool(sub.interior_day) and WEEKDAYS[day.weekday()] == sub.interior_day
    return day_flags(db, sub, pattern, day)[1]


def _last_actual_in_week(db, vehicle_id: uuid.UUID, week: date) -> date | None:
    """The last Interior actually done for the car in the service week, or None."""
    from app.scheduling.models import Job as _Job
    from app.scheduling.models import Visit as _Visit
    last = db.scalar(select(func.max(_Visit.date)).join(_Job, _Job.visit_id == _Visit.id).where(
        _Visit.vehicle_id == vehicle_id, _Job.service == INTERIOR, _Job.status == "Completed",
        _Visit.date >= week, _Visit.date <= week + timedelta(days=6)))
    return last
