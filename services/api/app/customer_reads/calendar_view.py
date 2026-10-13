"""The calendar and the next service, with dates the scheduler has not planned
yet projected from the subscription (CAL-01, CAL-02, CAL-05 to CAL-10, HOME-04).

A planned visit always wins over a projected day. A projected day follows the
scheduler's own rules (`app.changes.projection`), the customer's pauses and
skips, and the cutoff changes made for single dates."""

import calendar
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.cycle import extension_days, paused_days
from app.changes.models import ScheduleChange
from app.changes.projection import day_services, renewals_between
from app.changes.rules import is_open, today_of
from app.customer_reads.repository import (
    TERMINAL_VISIT_STATUSES,
    Job,
    Visit,
    VisitReadRepository,
)
from app.customer_reads.schemas import (
    CalendarJob,
    CalendarMonth,
    CalendarRenewal,
    CalendarVisit,
    NextServiceItem,
)
from app.customers.models import Subscription, Vehicle
from app.customers.service import show_time
from app.directory import lookup

# How far ahead the Home card looks for the next visit.
NEXT_SERVICE_DAYS = 60
# How far after a Missed visit the make-up date is looked for (CAL-09).
MAKE_UP_DAYS = 14
# A day card can still be changed while its status is one of these (SCHED-01).
CHANGEABLE = ("Scheduled", "Projected", "Skipped")


@dataclass
class _Ctx:
    """What the calendar needs to know about one vehicle's schedule changes."""

    vehicle: Vehicle
    sub: Subscription | None
    paused: set[date]
    skips: dict[date, str] = field(default_factory=dict)  # day -> skip ID
    applied: dict[date, time] = field(default_factory=dict)
    requested: dict[date, time] = field(default_factory=dict)


def _hhmm(minute: int | None) -> str | None:
    return None if minute is None else f"{minute // 60:02d}:{minute % 60:02d}"


class CalendarView:
    def __init__(self, db: Session, visits: VisitReadRepository, now_fn: Callable[[], datetime]):
        self._db = db
        self._visits = visits
        self._now = now_fn

    def _jobs_by_visit(self, visits: Sequence[Visit]) -> dict[str, list[Job]]:
        grouped: dict[str, list[Job]] = {v.id: [] for v in visits}
        for job in self._visits.jobs([v.id for v in visits]):
            grouped.setdefault(job.visit_id, []).append(job)
        return grouped

    def _ctx(self, vehicle: Vehicle, sub: Subscription | None, first: date, last: date) -> _Ctx:
        ctx = _Ctx(vehicle, sub, paused_days(self._db, vehicle.id))
        rows = self._db.scalars(
            select(ScheduleChange)
            .where(
                ScheduleChange.vehicle_id == vehicle.id,
                ScheduleChange.kind.in_(("skip", "cutoff")),
                ScheduleChange.status.in_(("Active", "Applied", "Requested")),
                ScheduleChange.start_date >= first,
                ScheduleChange.start_date <= last,
            )
            .order_by(ScheduleChange.created_at)
        ).all()
        for c in rows:
            if c.kind == "skip":
                ctx.skips[c.start_date] = str(c.id)
            elif c.cutoff_time is not None:
                target = ctx.applied if c.status == "Applied" else ctx.requested
                target[c.start_date] = c.cutoff_time
        return ctx

    def _make_up(
        self, ctx: _Ctx, visit: Visit, jobs: list[Job], today: date
    ) -> tuple[date | None, date | None]:
        """(covered on, rescheduled on) for a Missed visit (CAL-09).

        DERIVED: a missed Cleaning-External is covered by the next regular
        visit. A missed Cleaning-Internal or Deep Spa is rescheduled when a
        later visit has the same service again, off the usual interior day
        (Cleaning-Internal) or for the same add-on request (Deep Spa)."""
        missed = [j for j in jobs if j.status == "Missed"]
        later = self._visits.visits_in_range(
            [visit.vehicle_id],
            visit.date + timedelta(days=1),
            visit.date + timedelta(days=MAKE_UP_DAYS),
        )
        later_jobs = self._jobs_by_visit(later)
        for lv in later:
            if any(j.source_job_id in {m.id for m in missed} for j in later_jobs[lv.id]):
                return None, lv.date
        other = [j for j in missed if j.service != "Cleaning-External"]
        if other:
            interior = ctx.sub.interior_day if ctx.sub else None
            for lv in later:
                for j in later_jobs[lv.id]:
                    if j.status in ("Skipped", "Missed"):
                        continue
                    for m in other:
                        if j.service != m.service:
                            continue
                        if m.service == "Deep Spa":
                            same = bool(
                                j.addon_request_id and j.addon_request_id == m.addon_request_id
                            )
                        else:
                            same = lv.date.strftime("%A") != interior
                        if same:
                            return None, lv.date
            return None, None
        for lv in later:
            if lv.date == visit.date + timedelta(days=1) and any(
                j.service == "Cleaning-External" and j.status not in ("Skipped", "Missed")
                for j in later_jobs[lv.id]
            ):
                return lv.date, None
        d = visit.date + timedelta(days=1)
        actual_exterior = any(
            lv.date == d and any(j.service == "Cleaning-External" for j in later_jobs[lv.id])
            for lv in later
        )
        if (
            not actual_exterior
            and d > today
            and day_services(ctx.sub, d)
            and d not in ctx.paused
            and d not in ctx.skips
        ):
            return d, None
        return None, None

    @staticmethod
    def _cutoff(ctx: _Ctx, day: date, jobs: list[Job]) -> str | None:
        if day in ctx.applied:
            return show_time(ctx.applied[day])
        for j in jobs:
            if j.finish_by_minute is not None:
                return _hhmm(j.finish_by_minute)
        return show_time(ctx.sub.cutoff_time) if ctx.sub else None

    def _day(
        self,
        ctx: _Ctx,
        day: date,
        visit: Visit | None,
        jobs: list[Job],
        services: list[str],
        now: datetime,
    ) -> CalendarVisit:
        today = today_of(now)
        if visit is None:
            status = (
                "Paused" if day in ctx.paused else "Skipped" if day in ctx.skips else "Projected"
            )
            visit_id, frozen = None, False
        else:
            status, visit_id, frozen = visit.status, visit.id, visit.frozen
            # A pause skips the planned jobs: say Paused, not Skipped.
            if (
                status == "Skipped"
                and day in ctx.paused
                and any(j.service != "Deep Spa" for j in jobs)
            ):
                status = "Paused"
        active = ctx.sub is not None and ctx.sub.status == "Active"
        spa_only = bool(jobs) and all(j.service == "Deep Spa" for j in jobs)
        requested = not spa_only and day in ctx.requested and status in ("Scheduled", "Projected")
        covered = rescheduled = None
        if visit is not None and status == "Missed":
            covered, rescheduled = self._make_up(ctx, visit, jobs, today)
        state = (
            "Change requested"
            if requested
            else "Covered"
            if covered
            else "Rescheduled"
            if rescheduled
            else status
        )
        shown = []
        for j in jobs:
            # The crew member and time show once the schedule is frozen (CAL-10).
            placed = frozen and j.crew_name is not None and j.start_minute is not None
            shown.append(
                CalendarJob(
                    service=j.service,
                    status=j.status,
                    crew_name=j.crew_name if placed else None,
                    start_time=_hhmm(j.start_minute) if placed else None,
                    end_time=_hhmm(j.start_minute + j.duration_minutes) if placed else None,
                )
            )
        first_placed = next((j for j in shown if j.crew_name), None)
        return CalendarVisit(
            finished_at=max((j.finished_at for j in jobs if j.finished_at), default=None)
                if status == "Completed" else None,
            checklist_total=sum(len(j.checklist) for j in jobs),
            checklist_done=sum(i.checked_at is not None for j in jobs for i in j.checklist),
            visit_id=visit_id,
            vehicle_id=str(ctx.vehicle.id),
            date=day,
            status=status,
            services=services,
            source="visit" if visit else "projected",
            state=state,
            cutoff_time=self._cutoff(ctx, day, jobs),
            change_requested=requested,
            requested_cutoff_time=show_time(ctx.requested.get(day)) if requested else None,
            skip_id=ctx.skips.get(day) if status == "Skipped" else None,
            can_change=active
            and not spa_only
            and status in CHANGEABLE
            and day > today
            and is_open(day, now, lookup.setting(self._db, "schedule.customer_change_hour")),
            frozen=frozen,
            covered_on=covered,
            rescheduled_on=rescheduled,
            jobs=shown,
            crew_name=first_placed.crew_name if first_placed else None,
            start_time=first_placed.start_time if first_placed else None,
            end_time=first_placed.end_time if first_placed else None,
        )

    def month(
        self,
        year: int,
        number: int,
        ids: Sequence[str],
        owned: dict[str, tuple[Vehicle, Subscription | None]],
    ) -> CalendarMonth:
        first = date(year, number, 1)
        last = date(year, number, calendar.monthrange(year, number)[1])
        now = self._now()
        today = today_of(now)
        visits = self._visits.visits_in_range(ids, first, last)
        jobs = self._jobs_by_visit(visits)
        out: list[CalendarVisit] = []
        renewals: list[CalendarRenewal] = []
        for vid in ids:
            vehicle, sub = owned[vid]
            ctx = self._ctx(vehicle, sub, first, last)
            planned: set[date] = set()
            for v in (x for x in visits if x.vehicle_id == vid):
                if not jobs[v.id] or not all(j.service == "Deep Spa" for j in jobs[v.id]):
                    planned.add(v.date)
                out.append(
                    self._day(ctx, v.date, v, jobs[v.id], [j.service for j in jobs[v.id]], now)
                )
            if sub is None or sub.status != "Active":
                continue
            # Dates the scheduler has not planned: from the subscription.
            day = max(first, today + timedelta(days=1))
            while day <= last:
                services = day_services(sub, day)
                if day not in planned and services:
                    out.append(self._day(ctx, day, None, [], services, now))
                day += timedelta(days=1)
            renewals.extend(
                CalendarRenewal(vehicle_id=vid, date=d)
                for d in renewals_between(
                    sub.first_service_date,
                    len(ctx.paused) + extension_days(self._db, vehicle.id),
                    first,
                    last,
                    lookup.setting(self._db, "billing.cycle_days"),
                )
            )
        order = {vid: i for i, vid in enumerate(ids)}
        out.sort(key=lambda c: (c.date, order[c.vehicle_id], c.visit_id or ""))
        return CalendarMonth(month=f"{year:04d}-{number:02d}", visits=out, renewals=renewals)

    def next_services(
        self, today: date, ids: Sequence[str], owned: dict[str, tuple[Vehicle, Subscription | None]]
    ) -> list[NextServiceItem]:
        """The next visit that is not over, for each vehicle. When the
        scheduler has not planned it yet, the next service day the
        subscription implies (HOME-04)."""
        horizon = today + timedelta(NEXT_SERVICE_DAYS)
        visits = self._visits.visits_in_range(ids, today, horizon)
        jobs = self._jobs_by_visit(visits)
        now = self._now()
        result: dict[str, NextServiceItem] = {}
        for v in visits:
            if v.status in TERMINAL_VISIT_STATUSES or v.vehicle_id in result:
                continue
            vehicle, sub = owned[v.vehicle_id]
            ctx = self._ctx(vehicle, sub, v.date, v.date)
            vjobs = jobs[v.id]
            card = self._day(ctx, v.date, v, vjobs, [j.service for j in vjobs], now)
            result[v.vehicle_id] = NextServiceItem(
                vehicle_id=v.vehicle_id,
                visit_id=v.id,
                date=v.date,
                service=vjobs[0].service if vjobs else "",
                status=v.status,
                services=card.services,
                cutoff_time=card.cutoff_time,
                crew_name=card.crew_name,
                start_time=card.start_time,
                end_time=card.end_time,
            )
        for vid in ids:
            vehicle, sub = owned[vid]
            if sub is None or sub.status != "Active":
                continue
            ctx = self._ctx(vehicle, sub, today, horizon)
            have = result.get(vid)
            day = today + timedelta(days=1)
            while day <= horizon and (have is None or day < have.date):
                services = day_services(sub, day)
                if services and day not in ctx.paused and day not in ctx.skips:
                    result[vid] = NextServiceItem(
                        vehicle_id=vid,
                        visit_id=None,
                        date=day,
                        service=services[0],
                        status="Scheduled",
                        services=services,
                        source="projected",
                        cutoff_time=self._cutoff(ctx, day, []),
                    )
                    break
                day += timedelta(days=1)
        return [result[i] for i in ids if i in result]
