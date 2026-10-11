"""Skip, un-skip, pause, end a pause and cutoff-time changes.

Customers are bound by the 9 PM rule (SCHED-01); the admin is not
(ADM-CUS-11, ADM-ACC-07 e). Visits are changed through the gateway."""
import uuid
from dataclasses import dataclass
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.access import parse_id
from app.changes.cycle import cycle_window, paused_days, shift_days
from app.changes.gateway import ScheduleChangeGateway, ServiceDay
from app.changes.models import ScheduleChange
from app.changes.projection import day_services
from app.changes.rules import Clock, is_open, require_open, today_of
from app.changes.schemas import ChangeOut, ChangesOut, PreferencesOut, UpcomingDay
from app.customers.models import WEEKDAYS, Customer, Subscription, Vehicle
from app.customers.service import read_cutoff, show_time
from app.notifications import emit  # notify hook
from app.platform.db import utcnow
from app.platform.errors import ApiError


@dataclass(frozen=True)
class Actor:
    role: str  # customer | admin
    login_id: uuid.UUID

    @property
    def bound(self) -> bool:
        return self.role == "customer"


def renewal_for(db: Session, vehicle: Vehicle, sub: Subscription | None,
                today: date) -> date | None:
    if sub is None:
        return None
    return cycle_window(sub.first_service_date, shift_days(db, vehicle.id), today)[1]


class ChangesService:
    def __init__(self, db: Session, gateway: ScheduleChangeGateway, now_fn: Clock):
        self._db = db
        self._gateway = gateway
        self._now = now_fn

    # --- reading -----------------------------------------------------------

    def _out(self, c: ScheduleChange, *, visits: int | None = None,
             renewal: date | None = None) -> ChangeOut:
        return ChangeOut(
            id=str(c.id), vehicle_id=str(c.vehicle_id), kind=c.kind, status=c.status,
            start_date=c.start_date, end_date=c.end_date,
            days=(c.end_date - c.start_date).days + 1,
            cutoff_time=c.cutoff_time.strftime("%H:%M") if c.cutoff_time else None,
            actor=c.actor, visits_paused=visits, renewal_date=renewal, created_at=c.created_at)

    def _active(self, vehicle_id: uuid.UUID, kind: str, today: date) -> list[ScheduleChange]:
        ok = ("Active",) if kind != "cutoff" else ("Applied", "Requested")
        return list(self._db.scalars(
            select(ScheduleChange).where(
                ScheduleChange.vehicle_id == vehicle_id, ScheduleChange.kind == kind,
                ScheduleChange.status.in_(ok), ScheduleChange.end_date >= today)
            .order_by(ScheduleChange.start_date, ScheduleChange.created_at)))

    def overview(self, vehicle: Vehicle, sub: Subscription | None) -> ChangesOut:
        today = today_of(self._now())
        return ChangesOut(
            vehicle_id=str(vehicle.id),
            skips=[self._out(c) for c in self._active(vehicle.id, "skip", today)],
            pauses=[self._out(c) for c in self._active(vehicle.id, "pause", today)],
            cutoff_changes=[self._out(c) for c in self._active(vehicle.id, "cutoff", today)],
            renewal_date=renewal_for(self._db, vehicle, sub, today))

    def upcoming(self, vehicle: Vehicle, count: int = 14,
                 sub: Subscription | None = None) -> list[UpcomingDay]:
        """The next service days with what has been done to each (SKIP-01, SKIP-06).
        Days the scheduler has not planned yet come from the subscription."""
        now = self._now()
        today = today_of(now)
        skips = {c.start_date: c for c in self._active(vehicle.id, "skip", today)}
        pauses = self._active(vehicle.id, "pause", today)
        cutoffs = {c.start_date: c for c in self._active(vehicle.id, "cutoff", today)}
        planned = {d.day: d for d in self._gateway.upcoming_days(
            vehicle.id, today + timedelta(days=1), count)}
        days = []
        for i in range(1, count + 1):
            day = today + timedelta(days=i)
            known = planned.get(day)
            services = list(known.services) if known else day_services(sub, day)
            if not services:
                continue
            d = ServiceDay(day, tuple(services))
            pause = next((p for p in pauses if p.start_date <= d.day <= p.end_date), None)
            skip = skips.get(d.day)
            cut = cutoffs.get(d.day)
            days.append(UpcomingDay(
                date=d.day, services=list(d.services),
                state="Paused" if pause else "Skipped" if skip else "Scheduled",
                skip_id=str(skip.id) if skip and not pause else None,
                pause_id=str(pause.id) if pause else None,
                cutoff_time=cut.cutoff_time.strftime("%H:%M") if cut else None,
                can_change=is_open(d.day, now),
                frozen=self._gateway.is_frozen(vehicle.id, d.day)))
        return days

    # --- rules shared by the changes ---------------------------------------

    def _require_active(self, sub: Subscription | None) -> None:
        if sub is None or sub.status != "Active":
            raise ApiError("subscription_not_active",
                           "Skip and pause are for an active subscription.", 409)

    def _existing_by_key(self, actor: Actor, key: str | None) -> ScheduleChange | None:
        if not key:
            return None
        found = self._db.scalar(select(ScheduleChange).where(
            ScheduleChange.idempotency_key == key))
        if found is not None and found.actor_login_id != actor.login_id:
            raise ApiError("idempotency_conflict", "That request key was used already.", 409)
        return found

    def _inside_pause(self, vehicle_id: uuid.UUID, day: date) -> bool:
        return day in paused_days(self._db, vehicle_id)

    def _save(self, change: ScheduleChange) -> ScheduleChange:
        self._db.add(change)
        self._db.commit()
        return change

    # --- skip and un-skip --------------------------------------------------

    def skip(self, actor: Actor, customer: Customer, vehicle: Vehicle,
             sub: Subscription | None, day: date, key: str | None) -> ChangeOut:
        now = self._now()
        again = self._existing_by_key(actor, key)
        if again is not None:
            return self._out(again)
        self._require_active(sub)
        require_open(day, now, bound=actor.bound)  # SKIP-02
        if self._inside_pause(vehicle.id, day):
            raise ApiError("inside_pause",
                           "That date is inside a pause, so it is already not serviced.",
                           409, {"date": "inside_pause"})  # SKIP-08
        same = self._db.scalar(select(ScheduleChange).where(
            ScheduleChange.vehicle_id == vehicle.id, ScheduleChange.kind == "skip",
            ScheduleChange.status == "Active", ScheduleChange.start_date == day))
        if same is not None:
            return self._out(same)
        first = self._gateway.upcoming_days(vehicle.id, day, 1)
        planned = bool(first) and first[0].day == day
        # A date beyond the planned weeks is a service day the subscription implies.
        if not planned and not day_services(sub, day):
            raise ApiError("not_a_service_day", "There is no service on that date.", 409,
                           {"date": "not_a_service_day"})
        self._gateway.skip_day(vehicle.id, day)
        change = self._save(ScheduleChange(
            customer_id=customer.id, vehicle_id=vehicle.id, kind="skip", start_date=day,
            end_date=day, status="Active", actor=actor.role, actor_login_id=actor.login_id,
            idempotency_key=key or None))
        emit.visits_removed(self._db, vehicle.id, day, day, "skip")  # notify hook
        emit.customer_skipped(self._db, vehicle, day)  # notify hook
        return self._out(change)

    def unskip(self, actor: Actor, vehicle: Vehicle, change_id: str) -> None:
        change = self._change(vehicle, change_id, "skip")
        if change.status != "Active":
            raise ApiError("not_found", "That skip was not found.", 404)
        require_open(change.start_date, self._now(), bound=actor.bound)  # SKIP-07
        self._gateway.unskip_day(vehicle.id, change.start_date)
        change.status = "Cancelled"
        change.ended_at = utcnow()
        self._db.commit()

    def _change(self, vehicle: Vehicle, change_id: str, kind: str) -> ScheduleChange:
        change = self._db.get(ScheduleChange, parse_id(change_id, kind))
        if change is None or change.vehicle_id != vehicle.id or change.kind != kind:
            raise ApiError("not_found", f"That {kind} was not found.", 404)
        return change

    # --- pause -------------------------------------------------------------

    def pause(self, actor: Actor, customer: Customer, vehicle: Vehicle,
              sub: Subscription | None, start: date, end: date, key: str | None) -> ChangeOut:
        now = self._now()
        again = self._existing_by_key(actor, key)
        if again is not None:
            return self._out(again, renewal=renewal_for(self._db, vehicle, sub, today_of(now)))
        self._require_active(sub)
        if end < start:
            raise ApiError("validation_failed", "The end date is before the start date.",
                           422, {"to_date": "before_start"})
        require_open(start, now, bound=actor.bound)  # PAUSE-07
        wanted = {start + timedelta(days=i) for i in range((end - start).days + 1)}
        if wanted & paused_days(self._db, vehicle.id):
            raise ApiError("pause_overlaps", "Those dates overlap a pause you already have.",
                           409, {"from_date": "pause_overlaps"})
        # A skip inside the pause becomes part of the pause (PAUSE-06).
        for s in self._db.scalars(select(ScheduleChange).where(
                ScheduleChange.vehicle_id == vehicle.id, ScheduleChange.kind == "skip",
                ScheduleChange.status == "Active", ScheduleChange.start_date >= start,
                ScheduleChange.start_date <= end)):
            s.status = "Merged"
            s.ended_at = utcnow()
        visits = self._gateway.pause_range(vehicle.id, start, end)
        change = self._save(ScheduleChange(
            customer_id=customer.id, vehicle_id=vehicle.id, kind="pause", start_date=start,
            end_date=end, status="Active", actor=actor.role, actor_login_id=actor.login_id,
            idempotency_key=key or None))
        emit.visits_removed(self._db, vehicle.id, start, end, "pause")  # notify hook
        return self._out(change, visits=visits,
                         renewal=renewal_for(self._db, vehicle, sub, today_of(now)))

    def end_pause(self, actor: Actor, vehicle: Vehicle, sub: Subscription | None,
                  change_id: str) -> ChangeOut:
        """A pause not started yet is cancelled. One that is running ends: the
        visits resume from the next date still before its 9 PM cutoff (PAUSE-05)."""
        now = self._now()
        today = today_of(now)
        pause = self._change(vehicle, change_id, "pause")
        if pause.status != "Active" or pause.end_date < today:
            raise ApiError("pause_over", "That pause is over already.", 409)
        if pause.start_date > today:
            require_open(pause.start_date, now, bound=actor.bound)
            self._gateway.resume_range(vehicle.id, pause.start_date, pause.end_date)
            pause.status = "Cancelled"
        else:
            resume = today + timedelta(days=1)
            if actor.bound and not is_open(resume, now):
                resume += timedelta(days=1)
            if resume > pause.end_date:
                raise ApiError("pause_ending", "That pause ends tomorrow already.", 409)
            self._gateway.resume_range(vehicle.id, resume, pause.end_date)
            pause.end_date = resume - timedelta(days=1)
        pause.ended_at = utcnow()
        self._db.commit()
        return self._out(pause, renewal=renewal_for(self._db, vehicle, sub, today))

    # --- cutoff time for one date (CAL-08) ---------------------------------

    def change_cutoff(self, actor: Actor, customer: Customer, vehicle: Vehicle,
                      sub: Subscription | None, day: date, cutoff_text: str,
                      key: str | None) -> ChangeOut:
        again = self._existing_by_key(actor, key)
        if again is not None:
            return self._out(again)
        self._require_active(sub)
        cutoff: time | None = read_cutoff(cutoff_text)
        if cutoff is None:
            raise ApiError("validation_failed", "Please select your service cutoff time.",
                           422, {"cutoff_time": "invalid"})
        require_open(day, self._now(), bound=actor.bound)  # SCHED-01
        if self._inside_pause(vehicle.id, day):
            raise ApiError("inside_pause", "That date is inside a pause.", 409,
                           {"date": "inside_pause"})
        # After a freeze a customer's change is only a request (CAL-07).
        requested = actor.bound and self._gateway.is_frozen(vehicle.id, day)
        if not requested:
            self._gateway.set_cutoff(vehicle.id, day, cutoff)
        return self._out(self._save(ScheduleChange(
            customer_id=customer.id, vehicle_id=vehicle.id, kind="cutoff", start_date=day,
            end_date=day, cutoff_time=cutoff, status="Requested" if requested else "Applied",
            actor=actor.role, actor_login_id=actor.login_id, idempotency_key=key or None)))

    # --- the default cutoff time and interior day (SUB-08) -------------------

    def update_preferences(self, actor: Actor, vehicle: Vehicle, sub: Subscription | None,
                           cutoff_text: str | None, interior_day: str | None) -> PreferencesOut:
        """DERIVED: the new default is saved at once and applies from the next
        date still before its 9 PM cutoff. Planned dates of a draft schedule
        get the new cutoff time now; a frozen date is not touched (the admin
        re-runs it), and a date with its own cutoff change keeps that."""
        self._require_active(sub)
        assert sub is not None
        now = self._now()
        if cutoff_text is None and interior_day is None:
            raise ApiError("validation_failed", "Nothing to change.", 422)
        cutoff: time | None = None
        if cutoff_text is not None:
            cutoff = read_cutoff(cutoff_text)
            if cutoff is None:
                raise ApiError("validation_failed", "Please select your service cutoff time.",
                               422, {"cutoff_time": "invalid"})
        if interior_day is not None and interior_day not in WEEKDAYS:
            raise ApiError("validation_failed", "Please select your interior care day.",
                           422, {"interior_day": "invalid"})
        start = today_of(now) + timedelta(days=1)
        if actor.bound and not is_open(start, now):
            start += timedelta(days=1)
        frozen = 0
        if cutoff is not None:
            own = {c.start_date for c in self._db.scalars(select(ScheduleChange).where(
                ScheduleChange.vehicle_id == vehicle.id, ScheduleChange.kind == "cutoff",
                ScheduleChange.status.in_(("Applied", "Requested")),
                ScheduleChange.start_date >= start))}
            for d in self._gateway.upcoming_days(vehicle.id, start, 120):
                if d.day in own:
                    continue
                if self._gateway.is_frozen(vehicle.id, d.day):
                    frozen += 1
                else:
                    self._gateway.set_cutoff(vehicle.id, d.day, cutoff)
            sub.cutoff_time = cutoff
        if interior_day is not None:
            sub.interior_day = interior_day
        self._db.commit()
        return PreferencesOut(
            vehicle_id=str(vehicle.id), cutoff_time=show_time(sub.cutoff_time),
            interior_day=sub.interior_day, applies_from=start, frozen_days_unchanged=frozen)
