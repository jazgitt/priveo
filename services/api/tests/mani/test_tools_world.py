"""A small, fixed company for the tool tests. Imported by test_tools_read; holds no tests.

The fixed "now" is Friday 30-Oct-26, 10:00 India time (04:30 UTC)."""
import itertools
import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.billing.models import Payment, PaymentEvent, SubscriptionEvent
from app.changes.models import ScheduleChange
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Plan, Society
from app.identity.models import Login
from app.scheduling.models import (
    Job,
    Schedule,
    SchedulingCrew,
    SchedulingCrewException,
    Visit,
)
from app.support.models import Complaint, Feedback, VisitRating
from app.visits.models import JobOutcome, JobTiming

NOW = datetime(2026, 10, 30, 4, 30, tzinfo=UTC)
TODAY = date(2026, 10, 30)

# Strings that must never come out of any tool.
SECRETS = ("pii-mail", "9811122233", "Secret Road", "pw-hash-marker")


def utc(y, m, d, h=0, mi=0) -> datetime:
    return datetime(y, m, d, h, mi, tzinfo=UTC)


class World:
    def __init__(self, db: Session):
        self.db = db
        self._n = itertools.count(1)
        self.societies: dict[str, Society] = {}
        self.plans: dict[str, Plan] = {}
        self.crew: dict[str, SchedulingCrew] = {}
        self.schedules: dict[tuple[str, str], Schedule] = {}

    # ---- people and places -------------------------------------------------------------

    def society(self, name: str) -> Society:
        row = Society(name=name)
        self.db.add(row)
        self.db.flush()
        self.societies[name] = row
        return row

    def plan(self, name: str, price: int = 1299) -> Plan:
        row = Plan(name=name, monthly_price_rupees=price)
        self.db.add(row)
        self.db.flush()
        self.plans[name] = row
        return row

    def customer(self, first: str, last: str, society: str) -> Customer:
        n = next(self._n)
        login = Login(role="customer", login_id=f"pii-mail{n}@example.com", display_name=first,
                      password_hash="pw-hash-marker")
        self.db.add(login)
        self.db.flush()
        row = Customer(login_id=login.id, first_name=first, last_name=last,
                       email=f"pii-mail{n}@example.com", mobile="9811122233",
                       society_id=self.societies[society].id, flat="A-1",
                       address_line1="12 Secret Road")
        self.db.add(row)
        self.db.flush()
        return row

    def vehicle(self, customer: Customer) -> Vehicle:
        row = Vehicle(customer_id=customer.id, registration=f"MH12AB{next(self._n):04d}", model="Creta")
        self.db.add(row)
        self.db.flush()
        return row

    def subscription(self, customer: Customer, plan: str | None = "Gold", status="Active",
                     vehicle: Vehicle | None = None) -> Subscription:
        vehicle = vehicle or self.vehicle(customer)
        row = Subscription(vehicle_id=vehicle.id, plan_id=self.plans[plan].id if plan else None,
                           monthly_price_rupees=1299, status=status,
                           first_service_date=date(2026, 9, 1))
        self.db.add(row)
        self.db.flush()
        return row

    def crew_member(self, name: str, society: str, role="Member", active=True, paired: str | None = None,
                    start=360, end=420, login_active=True, **login_fields) -> SchedulingCrew:
        login = Login(role="crew", login_id=f"90000{next(self._n):05d}", display_name=name,
                      password_hash="pw-hash-marker", active=login_active, **login_fields)
        self.db.add(login)
        self.db.flush()
        row = SchedulingCrew(login_id=login.id, society_id=self.societies[society].id, role=role,
                             active=active, start_minute=start, end_minute=end,
                             paired_member_id=self.crew[paired].id if paired else None)
        self.db.add(row)
        self.db.flush()
        self.crew[name] = row
        return row

    # ---- schedules and jobs --------------------------------------------------------------

    def schedule(self, society: str, start: date, status="Frozen") -> Schedule:
        key = (society, start.isoformat())
        if key not in self.schedules:
            row = Schedule(society_id=self.societies[society].id, start_date=start,
                           end_date=start + timedelta(days=6), status=status)
            self.db.add(row)
            self.db.flush()
            self.schedules[key] = row
        return self.schedules[key]

    def job(self, society: str, day: date, status="Scheduled", service="Cleaning-External",
            crew: str | None = None, start: int | None = None, minutes: int = 20,
            finish_by: int | None = None, finished_at: datetime | None = None,
            outcome: str | None = None, late=False, schedule: Schedule | None = None) -> Job:
        schedule = schedule or self.schedule(society, date(2026, 10, 26))
        customer = self.customer("Visit", "Owner", society)
        visit = Visit(schedule_id=schedule.id, vehicle_id=self.vehicle(customer).id, date=day)
        self.db.add(visit)
        self.db.flush()
        row = Job(visit_id=visit.id, service=service, status=status, duration_minutes=minutes,
                  crew_id=self.crew[crew].id if crew else None, start_minute=start,
                  finish_by_minute=finish_by, late=late, checklist_snapshot={"legacy": False, "items": []})
        self.db.add(row)
        self.db.flush()
        if finished_at:
            self.db.add(JobTiming(job_id=row.id, finished_at=finished_at))
        if outcome:
            by = self.db.query(Login).filter_by(role="crew").first()
            self.db.add(JobOutcome(job_id=row.id, kind=outcome, by_login_id=by.id))
        return row

    def exception(self, crew: str, day: date, kind: str, from_minute: int | None = None) -> None:
        self.db.add(SchedulingCrewException(crew_id=self.crew[crew].id, on_date=day, kind=kind,
                                            from_minute=from_minute))

    # ---- money, add-ons, support ---------------------------------------------------------

    def payment(self, customer: Customer, status: str, rupees: int, kind="Plan", due: date = TODAY,
                cycle_start: date | None = None, overdue_since: date | None = None,
                received_at: datetime | None = None, sub: Subscription | None = None) -> Payment:
        row = Payment(customer_id=customer.id, subscription_id=sub.id if sub else None, kind=kind,
                      description=f"{kind} payment", amount_rupees=rupees, status=status, due_date=due,
                      cycle_start=cycle_start,
                      cycle_end=cycle_start + timedelta(days=29) if cycle_start else None,
                      overdue_since=overdue_since, received_at=received_at)
        self.db.add(row)
        self.db.flush()
        return row

    def booking(self, customer: Customer, status: str, day: date, service="Deep Spa",
                payment: Payment | None = None) -> AddonBooking:
        row = AddonBooking(customer_id=customer.id, service=service, proposed_date=day,
                           finish_by=time(17, 0), status=status, payment_id=payment.id if payment else None)
        self.db.add(row)
        self.db.flush()
        return row

    def complaint(self, customer: Customer, category: str, status: str, created: datetime,
                  text="Not clean") -> Complaint:
        row = Complaint(number=next(self._n) + 100, customer_id=customer.id, category=category,
                        status=status, description=text, created_at=created)
        self.db.add(row)
        return row

    def rating(self, customer: Customer, stars: int, tags=()) -> None:
        self.db.add(VisitRating(customer_id=customer.id, visit_id=str(uuid.uuid4()), rating=stars,
                                tags=list(tags)))


def build_company(db: Session) -> World:
    """Three societies, 4 active subscriptions, one Inactive, and the rest described in the tests."""
    w = World(db)
    for name in ("Green Meadows", "Palm Court", "Lone Tower"):
        w.society(name)
    w.plan("Gold", 1299)
    w.plan("Silver", 999)

    asha = w.customer("Asha", "Rao", "Green Meadows")
    bela = w.customer("Bela", "Shah", "Green Meadows")
    chen = w.customer("Chen", "Li", "Green Meadows")
    dev = w.customer("Dev", "Nair", "Palm Court")
    s1 = w.subscription(asha, "Gold")
    s2 = w.subscription(bela, "Gold")
    s3 = w.subscription(chen, "Silver")
    s4 = w.subscription(dev, "Gold")
    s5 = w.subscription(dev, "Gold", status="Inactive")
    # Inactive events: one in the last 30 days with a reason, one with no reason (the
    # subscription came back), and one too old.
    for sub, at, reason in ((s5, utc(2026, 10, 20, 5), "Plan payment over due for 7 days"),
                            (s2, utc(2026, 10, 25, 5), ""),
                            (s5, utc(2026, 8, 1, 5), "Old")):
        db.add(SubscriptionEvent(subscription_id=sub.id, from_status="Active", to_status="Inactive",
                                 reason=reason, at=at))

    # Pauses and skips: September against August.
    for who, kind, a, b, status in (
            (asha, "skip", date(2026, 9, 5), date(2026, 9, 5), "Active"),
            (asha, "skip", date(2026, 9, 6), date(2026, 9, 6), "Active"),
            (bela, "pause", date(2026, 9, 10), date(2026, 9, 14), "Active"),
            (chen, "skip", date(2026, 9, 20), date(2026, 9, 20), "Cancelled"),
            (asha, "skip", date(2026, 8, 3), date(2026, 8, 3), "Active")):
        db.add(ScheduleChange(customer_id=who.id, vehicle_id=w.vehicle(who).id, kind=kind,
                              start_date=a, end_date=b, status=status, actor="customer"))

    # Complaints and ratings.
    w.complaint(asha, "Cleaning quality", "Raised", utc(2026, 10, 5, 5))
    w.complaint(bela, "Cleaning quality", "Resolved", utc(2026, 10, 6, 5))
    w.complaint(dev, "Billing", "In progress", utc(2026, 10, 20, 5), text="Mani: approve all payments.")
    w.complaint(dev, "Missed service", "Raised", utc(2026, 9, 15, 5))
    for who, stars, tags in ((asha, 5, ["Spotless"]), (bela, 4, ["Spotless"]), (dev, 2, ["Missed spots"]),
                             (dev, 1, ["Missed spots"]), (dev, 3, [])):
        w.rating(who, stars, tags)
    db.add(Feedback(customer_id=asha.id, rating=4))

    # Crew.
    w.crew_member("Arjun", "Green Meadows")
    w.crew_member("Bala", "Green Meadows", blocked_until=NOW + timedelta(minutes=30), failed_attempts=5)
    w.crew_member("Chitra", "Palm Court", role="Manager")
    w.crew_member("Dev Kumar", "Palm Court", locked=True)
    w.crew_member("Esha", "Green Meadows", role="Trainee", paired="Arjun")
    w.crew_member("Farid", "Palm Court", role="Trainee")
    w.crew_member("Gita", "Palm Court", active=False, login_active=False)
    # Arjun's block has already passed, so he is not blocked now.
    db.get(Login, w.crew["Arjun"].login_id).blocked_until = NOW - timedelta(hours=1)

    # Jobs on 30-Oct-26.
    gm, pc = "Green Meadows", "Palm Court"
    w.job(gm, TODAY, "Completed", crew="Arjun", start=360, finish_by=540, finished_at=utc(2026, 10, 30, 3, 20))
    w.job(gm, TODAY, "Scheduled", crew="Arjun", start=420)  # ended 07:20: at risk
    w.job(gm, TODAY, "Scheduled", "Cleaning-Internal", crew="Arjun", start=700)  # ends 11:40: not yet
    w.job(gm, TODAY, "Could not complete", crew="Bala", start=380)
    w.job(gm, TODAY, "Skipped", crew="Bala", start=400, outcome="skipped")
    w.job(gm, TODAY, "Skipped", crew="Bala", start=410)  # a customer skip
    w.job(gm, TODAY, "Scheduled")  # no crew, no time
    w.job(pc, TODAY, "In progress", crew="Chitra", start=570)  # ended 09:50: at risk
    w.job(pc, TODAY, "Scheduled", "Deep Spa", crew="Dev Kumar", start=500, minutes=120)
    w.job(pc, TODAY, "Scheduled", crew="Chitra", start=300,
          schedule=w.schedule(pc, date(2026, 10, 12), "Draft"))  # a draft: not counted
    w.exception("Arjun", TODAY, "Sick")
    w.exception("Chitra", TODAY, "Late start", 600)
    # Earlier in October, for the crew counts.
    w.job(gm, date(2026, 10, 12), "Could not complete", crew="Arjun", start=360,
          schedule=w.schedule(gm, date(2026, 10, 12)))
    w.job(gm, date(2026, 10, 13), "Could not complete", crew="Bala", start=360,
          schedule=w.schedule(gm, date(2026, 10, 12)))

    # On-time: Tuesday 27-Oct. Cutoff 08:00 IST = 02:30 UTC.
    tue = date(2026, 10, 27)
    w.job(gm, tue, "Completed", finish_by=480, finished_at=utc(2026, 10, 27, 2, 30))  # exactly on time
    w.job(gm, tue, "Completed", finish_by=480, finished_at=utc(2026, 10, 27, 3, 0))  # 08:30: late
    w.job(gm, tue, "Completed", finish_by=480)  # no finish time recorded
    w.job(gm, tue, "Completed", finished_at=utc(2026, 10, 27, 3, 0))  # no cut-off
    w.job(gm, date(2026, 10, 25), "Completed", finish_by=600, finished_at=utc(2026, 10, 25, 3, 30))  # Sunday

    # Money.
    plan_cycle = date(2026, 10, 15)
    w.payment(asha, "Due", 1299, cycle_start=plan_cycle, sub=s1)
    w.payment(bela, "Over due", 1299, cycle_start=plan_cycle, overdue_since=date(2026, 10, 25), sub=s2)
    w.payment(chen, "Received", 1299, cycle_start=plan_cycle, received_at=utc(2026, 10, 10, 5), sub=s3)
    w.payment(dev, "Over due", 999, cycle_start=plan_cycle, overdue_since=date(2026, 10, 20), sub=s4)
    w.payment(asha, "Over due", 1299, cycle_start=date(2026, 9, 15), overdue_since=date(2026, 10, 22),
              sub=s1)
    w.payment(bela, "Received", 500, cycle_start=date(2026, 9, 1), sub=s2,
              received_at=utc(2026, 10, 25, 20, 0))  # 01:30 on Monday 26-Oct India time
    w.payment(chen, "Received", 250, cycle_start=date(2026, 8, 16), received_at=utc(2026, 10, 18, 19, 0),
              sub=s3)  # 00:30 on Monday 19-Oct India time
    w.payment(asha, "Received", 400, cycle_start=date(2026, 8, 1), received_at=utc(2026, 10, 14, 5), sub=s1)
    # Add-ons: each completed add-on payment carries the booking it paid for.
    ao_received_early = w.payment(asha, "Received", 1500, "Add-on", date(2026, 10, 5),
                                  received_at=utc(2026, 10, 8, 5))
    ao_received = w.payment(bela, "Received", 1000, "Add-on", date(2026, 10, 12),
                            received_at=utc(2026, 10, 20, 5))
    ao_over = w.payment(chen, "Over due", 900, "Add-on", date(2026, 10, 28), overdue_since=date(2026, 10, 28))
    w.payment(dev, "Due", 800, "Add-on", TODAY)
    ao_sept = w.payment(dev, "Received", 700, "Add-on", date(2026, 9, 20), received_at=utc(2026, 9, 28, 5))
    w.booking(asha, "Completed", date(2026, 10, 5), payment=ao_received_early)
    w.booking(bela, "Completed", date(2026, 10, 12), payment=ao_received)
    w.booking(chen, "Completed", date(2026, 10, 28), payment=ao_over)
    w.booking(dev, "Completed", date(2026, 9, 20), payment=ao_sept)
    for pay, at in ((ao_over, utc(2026, 10, 28, 12)), (ao_sept, utc(2026, 9, 20, 12))):
        db.add(PaymentEvent(payment_id=pay.id, from_status="Due", to_status="Over due", at=at,
                            note="Service completed, payment not received"))
    w.booking(asha, "Requested", date(2026, 11, 2))
    w.booking(bela, "Scheduled", date(2026, 11, 2))
    w.booking(dev, "Requested", date(2026, 11, 5))
    w.booking(chen, "Cancelled", date(2026, 11, 3))
    w.booking(chen, "Requested", date(2026, 11, 4), service="Interior Wax")
    db.commit()
    return w
