"""Expected answers for the live questions, computed from the dataset.

Every figure here comes from queries written for the eval. This module imports no Mani
tool, so the eval never checks Mani against itself. Definitions (owner, 30-Oct-26):

- "at risk": a job today that is not completed and, going by its expected completion time
  (`finish_by_minute`), cannot finish in time: its projected finish is after that time.
- "on time": a job completed before the customer's cut-off time (the subscription's cut-off,
  or an add-on's finish-by time).
- capacity "tight": use between 90% and 100% of crew minutes; "over": demand above capacity.
- Days and weeks are Asia/Kolkata. A week runs Monday to Sunday.

Where the data has no such concept, the expected answer is "the system cannot say"."""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.billing.models import Payment, SubscriptionEvent
from app.changes.models import ScheduleChange
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Plan, Society
from app.identity.models import Login
from app.platform.clock import IST
from app.scheduling.models import Job, SchedulingCrew, SchedulingCrewException, Visit
from app.support.models import Complaint, VisitRating
from app.visits.models import JobTiming

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
UNKNOWN_PLAN = "Unknown plan"
TIGHT_FROM = 0.90
MINUTES = {"Cleaning-External": 20, "Cleaning-Internal": 20, "Deep Spa": 120}


@dataclass(frozen=True)
class Num:
    """A number the answer must contain. `tol` is the allowed absolute difference."""

    label: str
    value: float
    tol: float = 0.0


@dataclass(frozen=True)
class Expected:
    key: str
    statement: str  # one plain line, also used in the review file
    value: Any = None  # the structured result
    numbers: tuple[Num, ...] = ()
    names_all: tuple[str, ...] = ()  # every name must appear
    names_any: tuple[str, ...] = ()  # at least one must appear
    dates_all: tuple[date, ...] = ()  # every date must appear, in any common format
    cannot_say: bool = False  # the right answer is that the data is missing
    notes: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


# ---- Helpers --------------------------------------------------------------------------------


def ist_date(moment: datetime) -> date:
    return moment.astimezone(IST).date()


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def month_start(day: date) -> date:
    return day.replace(day=1)


def previous_month_start(day: date) -> date:
    return (month_start(day) - timedelta(days=1)).replace(day=1)


def quarter_bounds_before(day: date) -> tuple[date, date]:
    """The calendar quarter before the one `day` is in: (first day, last day)."""
    this_quarter_start = date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)
    last_day = this_quarter_start - timedelta(days=1)
    return date(last_day.year, 3 * ((last_day.month - 1) // 3) + 1, 1), last_day


def full_name(customer: Customer) -> str:
    return f"{customer.first_name} {customer.last_name}".strip()


def money(amount: int) -> str:
    return f"Rs {amount:,}"


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def _hhmm(text: str) -> int:
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


# ---- Business -------------------------------------------------------------------------------


def q01_active_by_plan(db: Session) -> Expected:
    rows = db.execute(
        select(Plan.name, Subscription.id).select_from(Subscription)
        .outerjoin(Plan, Subscription.plan_id == Plan.id)
        .where(Subscription.status == "Active")).all()
    by_plan: dict[str, int] = defaultdict(int)
    for name, _ in rows:
        by_plan[name or UNKNOWN_PLAN] += 1
    total = len(rows)
    detail = ", ".join(f"{name}: {count}" for name, count in sorted(by_plan.items()))
    return Expected(
        "q01", f"{total} active subscriptions ({detail}).", dict(by_plan),
        numbers=(Num("total", total), *(Num(n, c) for n, c in by_plan.items())),
        names_all=tuple(n for n in by_plan if n != UNKNOWN_PLAN))


def _active_per_society(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Society.name).select_from(Subscription)
        .join(Vehicle, Subscription.vehicle_id == Vehicle.id)
        .join(Society, Vehicle.society_id == Society.id)
        .where(Subscription.status == "Active")).all()
    counts: dict[str, int] = defaultdict(int)
    for (name,) in rows:
        counts[name] += 1
    return dict(counts)


def q02_societies_by_subscribers(db: Session) -> Expected:
    counts = _active_per_society(db)
    all_societies = [name for (name,) in db.execute(select(Society.name))]
    most = max(counts.values())
    top = sorted(n for n, c in counts.items() if c == most)
    least = min(counts.values())
    bottom = sorted(n for n, c in counts.items() if c == least)
    with_none = [n for n in all_societies if n not in counts]
    return Expected(
        "q02",
        f"Most active subscriptions: {', '.join(top)} ({most}). Fewest among societies with any: "
        f"{len(bottom)} societies with {least}. {len(with_none)} societies have none.",
        {"top": top, "bottom": bottom, "none": len(with_none)},
        numbers=(Num("most", most),), names_any=tuple(top),
        notes="A subscriber is an active subscription (one per vehicle). Ties are expected.",
        extras={"top_count": most, "bottom_count": least})


def q03_inactive_last_30_days(db: Session, today: date) -> Expected:
    since = today - timedelta(days=30)
    events = [e for e in db.scalars(select(SubscriptionEvent).where(
        SubscriptionEvent.to_status == "Inactive")) if ist_date(e.at) >= since]
    inactive_now = len(list(db.scalars(select(Subscription).where(
        Subscription.status == "Inactive"))))
    return Expected(
        "q03",
        f"{len(events)} recorded status changes to Inactive in the last 30 days. "
        f"{inactive_now} subscriptions are Inactive now, but the seed data records no event, so "
        "when and why cannot be said (each has an Over due payment).",
        {"events": len(events), "inactive_now": inactive_now},
        numbers=(Num("events", len(events)),),
        notes="The seed creates no subscription events, so the reasons are not recorded.",
        extras={"inactive_now": inactive_now})


def _people_with_changes(db: Session, first: date, last: date) -> int:
    rows = db.scalars(select(ScheduleChange).where(
        ScheduleChange.kind.in_(("pause", "skip")), ScheduleChange.status != "Cancelled",
        ScheduleChange.start_date >= first, ScheduleChange.start_date <= last))
    return len({row.customer_id for row in rows})


def q04_pause_skip_months(db: Session, today: date) -> Expected:
    last_start = previous_month_start(today)
    last_end = month_start(today) - timedelta(days=1)
    before_start = previous_month_start(last_start)
    before_end = last_start - timedelta(days=1)
    last = _people_with_changes(db, last_start, last_end)
    before = _people_with_changes(db, before_start, before_end)
    this = _people_with_changes(db, month_start(today), today + timedelta(days=366))
    return Expected(
        "q04",
        f"{last} customers paused or skipped last month ({last_start:%B}), {before} the month "
        f"before ({before_start:%B}). (This month and later: {this}.)",
        {"last": last, "before": before, "this_month_on": this},
        numbers=(Num("last month", last), Num("month before", before)),
        notes="Counts customers by the start date of a skip or pause that was not cancelled.")


def q05_complaints_this_month(db: Session, today: date) -> Expected:
    rows = [c for c in db.scalars(select(Complaint))
            if ist_date(c.created_at) >= month_start(today)]
    by_cat: dict[str, int] = defaultdict(int)
    for row in rows:
        by_cat[row.category] += 1
    unresolved = sum(1 for r in rows if r.status != "Resolved")
    detail = ", ".join(f"{k}: {v}" for k, v in sorted(by_cat.items(), key=lambda i: -i[1]))
    return Expected(
        "q05", f"{len(rows)} complaints this month ({detail}); {unresolved} unresolved.",
        {"by_category": dict(by_cat), "total": len(rows), "unresolved": unresolved},
        numbers=(Num("total", len(rows)), Num("unresolved", unresolved)),
        names_all=tuple(by_cat))


def q06_ratings(db: Session) -> Expected:
    visit_society = {str(v.id): name for v, name in db.execute(
        select(Visit, Society.name).join(Vehicle, Visit.vehicle_id == Vehicle.id)
        .join(Society, Vehicle.society_id == Society.id))}
    ratings = list(db.scalars(select(VisitRating)))
    if not ratings:
        return Expected("q06", "There are no visit ratings.", cannot_say=True)
    by_society: dict[str, list[int]] = defaultdict(list)
    for item in ratings:
        by_society[visit_society[item.visit_id]].append(item.rating)
    average = round(sum(r.rating for r in ratings) / len(ratings), 1)
    means = {n: round(sum(v) / len(v), 1) for n, v in by_society.items()}
    lowest_value = min(means.values())
    lowest = sorted(n for n, m in means.items() if m == lowest_value)
    return Expected(
        "q06",
        f"{len(ratings)} visit ratings, average {average}. Lowest society average "
        f"{lowest_value}: {', '.join(lowest)}.",
        {"count": len(ratings), "average": average, "by_society": means, "lowest": lowest},
        numbers=(Num("average", average, 0.05), Num("count", len(ratings))),
        names_any=tuple(lowest), extras={"lowest": lowest})


# ---- Operations -----------------------------------------------------------------------------


def _jobs_on(db: Session, day: date) -> list[tuple[Job, Visit]]:
    return [(job, visit) for job, visit in db.execute(
        select(Job, Visit).join(Visit, Job.visit_id == Visit.id).where(Visit.date == day))]


def q15_jobs_today(db: Session, today: date) -> Expected:
    jobs = [job for job, _ in _jobs_on(db, today)]
    count = lambda status: sum(1 for j in jobs if j.status == status)  # noqa: E731
    done, skipped, missed = count("Completed"), count("Skipped"), count("Could not complete")
    value = {"total": len(jobs), "completed": done, "skipped": skipped, "missed": missed,
             "in_progress": count("In progress"), "scheduled": count("Scheduled")}
    return Expected(
        "q15",
        f"{len(jobs)} jobs today: {done} completed, {skipped} skipped, {missed} missed "
        f"(could not complete), {value['in_progress']} in progress, {value['scheduled']} scheduled.",
        value,
        numbers=(Num("total", len(jobs)), Num("completed", done), Num("skipped", skipped),
                 Num("missed", missed)),
        notes="Missed means the crew marked the job Could not complete.")


def q16_absent_crew(db: Session, today: date) -> Expected:
    rows = db.execute(
        select(SchedulingCrewException, Login.display_name)
        .join(SchedulingCrew, SchedulingCrewException.crew_id == SchedulingCrew.id)
        .join(Login, SchedulingCrew.login_id == Login.id)
        .where(SchedulingCrewException.on_date == today)).all()
    absent = [(e, name) for e, name in rows if e.kind in ("Sick", "Leave")]
    late = [(e, name) for e, name in rows if e.kind == "Late start"]
    absent_ids = {e.crew_id for e, _ in absent}
    affected = [job for job, _ in _jobs_on(db, today) if job.crew_id in absent_ids]
    names = tuple(name for _, name in absent)
    return Expected(
        "q16",
        f"{len(absent)} crew absent today ({', '.join(f'{n} {e.kind}' for e, n in absent)}); "
        f"{len(late)} start late. Jobs affected: {len(affected)}.",
        {"absent": [n for _, n in absent], "late": [n for _, n in late],
         "jobs_affected": len(affected)},
        numbers=(Num("absent", len(absent)), Num("jobs affected", len(affected))),
        names_all=names)


def q17_at_risk(db: Session, today: date, now: datetime) -> Expected:
    now_min = now.astimezone(IST).hour * 60 + now.astimezone(IST).minute
    timings = {t.job_id: t for t in db.scalars(select(JobTiming))}
    societies = {s.id: s.name for s in db.scalars(select(Society))}
    visit_society = {v.id: societies[vehicle.society_id] for v, vehicle in db.execute(
        select(Visit, Vehicle).join(Vehicle, Visit.vehicle_id == Vehicle.id))}
    at_risk: dict[str, int] = defaultdict(int)
    for job, visit in _jobs_on(db, today):
        if job.status not in ("Scheduled", "In progress") or job.finish_by_minute is None:
            continue
        if job.crew_id is None:
            risky = True
        elif job.status == "In progress":
            started = timings.get(job.id)
            start_min = (started.started_at.astimezone(IST).hour * 60
                         + started.started_at.astimezone(IST).minute) if started else now_min
            risky = max(now_min, start_min + job.duration_minutes) > job.finish_by_minute
        else:
            risky = max(now_min, job.start_minute or now_min) + job.duration_minutes \
                > job.finish_by_minute
        if risky:
            at_risk[visit_society[visit.id]] += 1
    total = sum(at_risk.values())
    return Expected(
        "q17",
        f"{total} jobs at risk today in {len(at_risk)} societies: "
        f"{', '.join(f'{n} ({c})' for n, c in sorted(at_risk.items()))}.",
        dict(at_risk), numbers=(Num("jobs at risk", total),), names_all=tuple(sorted(at_risk)),
        notes="At risk: not completed and projected to finish after its expected completion time.")


def q18_pending_deep_spa(db: Session) -> Expected:
    rows = list(db.scalars(select(AddonBooking).where(
        AddonBooking.service == "Deep Spa", AddonBooking.status.in_(("Requested", "Scheduled")))))
    dates = sorted({r.proposed_date for r in rows})
    return Expected(
        "q18",
        f"{len(rows)} Deep Spa add-ons pending (Requested or Scheduled), on "
        f"{', '.join(d.strftime('%d-%b-%y') for d in dates)}.",
        {"count": len(rows), "dates": [d.isoformat() for d in dates]},
        numbers=(Num("pending", len(rows)),), dates_all=tuple(dates))


def _local_minutes(moment: datetime) -> int:
    local = moment.astimezone(IST)
    return local.hour * 60 + local.minute


def q19_on_time_rate(db: Session, today: date, now: datetime) -> Expected:
    first = week_start(today)
    timings = {t.job_id: t for t in db.scalars(select(JobTiming))}
    cutoff_of = {}
    for sub, vehicle in db.execute(select(Subscription, Vehicle).join(
            Vehicle, Subscription.vehicle_id == Vehicle.id)):
        cutoff_of[vehicle.id] = sub.cutoff_time
    bookings = {b.id: b for b in db.scalars(select(AddonBooking))}
    on_time = due = 0
    for job, visit in db.execute(select(Job, Visit).join(Visit, Job.visit_id == Visit.id).where(
            Visit.date >= first, Visit.date <= today)):
        if job.status == "Skipped":
            continue  # a skip is not a late job
        due += 1
        if job.addon_booking_id:
            cutoff = bookings[job.addon_booking_id].finish_by
        else:
            cutoff = cutoff_of.get(visit.vehicle_id)
        finished = timings.get(job.id)
        if job.status == "Completed" and finished and finished.finished_at and cutoff \
                and _local_minutes(finished.finished_at) <= cutoff.hour * 60 + cutoff.minute:
            on_time += 1
    rate = _pct(on_time, due)
    return Expected(
        "q19",
        f"On-time rate this week ({first:%d-%b-%y} to {today:%d-%b-%y}): {rate}% "
        f"({on_time} of {due} jobs, skipped jobs left out).",
        {"on_time": on_time, "due": due, "rate": rate},
        numbers=(Num("rate", rate, 0.6),), notes=(
            "On time: completed before the customer's cut-off. Jobs not completed by then count "
            "as late."), extras={"on_time": on_time, "due": due})


def _minutes_for_day(crew: SchedulingCrew, day: date, exceptions: dict) -> int:
    if crew.role == "Trainee" or not crew.active:
        return 0
    hours = next((h for h in (crew.working_hours or []) if h["day"] == WEEKDAYS[day.weekday()]),
                 None)
    if not hours or not hours.get("working"):
        return 0
    start, end = _hhmm(hours["start"]), _hhmm(hours["end"])
    exception = exceptions.get((crew.id, day))
    if exception is not None:
        if exception.kind in ("Sick", "Leave"):
            return 0
        if exception.kind == "Late start" and exception.from_minute is not None:
            start = max(start, exception.from_minute)
    return max(end - start, 0)


def capacity_table(db: Session, today: date) -> list[dict]:
    """Demand and capacity in minutes for each society and day of the next 7 days."""
    societies = {s.id: s.name for s in db.scalars(select(Society))}
    crew = list(db.scalars(select(SchedulingCrew)))
    exceptions = {(e.crew_id, e.on_date): e for e in db.scalars(select(SchedulingCrewException))}
    changes = list(db.scalars(select(ScheduleChange).where(
        ScheduleChange.kind.in_(("pause", "skip")), ScheduleChange.status == "Active")))
    bookings = list(db.scalars(select(AddonBooking).where(
        AddonBooking.service == "Deep Spa", AddonBooking.status.in_(("Requested", "Scheduled")))))
    vehicle_society = {v.id: v.society_id for v in db.scalars(select(Vehicle))}
    subs = [(s, v, p) for s, v, p in db.execute(
        select(Subscription, Vehicle, Plan).join(Vehicle, Subscription.vehicle_id == Vehicle.id)
        .outerjoin(Plan, Subscription.plan_id == Plan.id))]
    table = []
    for offset in range(1, 8):
        day = today + timedelta(days=offset)
        demand: dict[Any, int] = defaultdict(int)
        capacity: dict[Any, int] = defaultdict(int)
        for member in crew:
            capacity[member.society_id] += _minutes_for_day(member, day, exceptions)
        for sub, vehicle, plan in subs:
            if sub.status != "Active" or not vehicle.active or sub.first_service_date > day:
                continue
            if any(c.vehicle_id == vehicle.id and c.start_date <= day <= c.end_date
                   for c in changes):
                continue
            demand[vehicle.society_id] += MINUTES["Cleaning-External"]
            if plan is not None and plan.includes_interior \
                    and sub.interior_day == WEEKDAYS[day.weekday()]:
                demand[vehicle.society_id] += MINUTES["Cleaning-Internal"]
        for booking in bookings:
            if booking.proposed_date == day and booking.vehicle_id in vehicle_society:
                demand[vehicle_society[booking.vehicle_id]] += MINUTES["Deep Spa"]
        for society_id, need in demand.items():
            have = capacity.get(society_id, 0)
            use = need / have if have else float("inf")
            state = "over" if use > 1 else "tight" if use >= TIGHT_FROM else "ok"
            table.append({"society": societies[society_id], "date": day, "demand": need,
                          "capacity": have, "use": use, "state": state})
    return table


def q20_capacity(db: Session, today: date) -> Expected:
    table = capacity_table(db, today)
    tight = [r for r in table if r["state"] == "tight"]
    over = [r for r in table if r["state"] == "over"]
    flagged = sorted({r["society"] for r in tight + over})
    by_society: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"tight": [], "over": []})
    for row in tight + over:
        by_society[row["society"]][row["state"]].append(f"{row['date']:%d-%b}")
    parts = [f"{name}: tight on {', '.join(days['tight']) or 'no days'}, over capacity on "
             f"{', '.join(days['over']) or 'no days'}" for name, days in sorted(by_society.items())]
    return Expected(
        "q20",
        f"Next 7 days: {len(tight)} society-days tight (90-100% used), {len(over)} over capacity. "
        + "; ".join(parts) + ".",
        {"tight": [(r["society"], r["date"].isoformat()) for r in tight],
         "over": [(r["society"], r["date"].isoformat()) for r in over]},
        numbers=(Num("tight society-days", len(tight)), Num("over society-days", len(over))),
        names_all=tuple(flagged),
        notes="Demand: one external per active vehicle (less skips and pauses), internal on its "
              "care day, Deep Spa on its date. Capacity: counted crew hours less exceptions.")


# ---- Finance --------------------------------------------------------------------------------


def q21_cycle_money(db: Session, today: date) -> Expected:
    window_start = today - timedelta(days=29)
    live = [p for p in db.scalars(select(Payment)) if p.voided_at is None]
    in_window = [p for p in live if window_start <= p.due_date <= today]

    def total(rows, status):
        return sum(p.amount_rupees for p in rows if p.status == status)

    due, received = total(in_window, "Due"), total(in_window, "Received")
    over = total(live, "Over due")
    initiated = total(in_window, "Initiated")
    return Expected(
        "q21",
        f"This cycle ({window_start:%d-%b-%y} to {today:%d-%b-%y}): Due {money(due)}, "
        f"Received {money(received)}, Initiated {money(initiated)}. Over due, all outstanding: "
        f"{money(over)}.",
        {"due": due, "over_due": over, "received": received, "initiated": initiated},
        numbers=(Num("due", due), Num("over due", over), Num("received", received)),
        notes="Cycle: payments due in the 30 days to today. Over due is every unpaid overdue "
              "payment, whatever its cycle. Voided payments left out.")


def q22_overdue_over_7_days(db: Session, today: date) -> Expected:
    rows = db.execute(
        select(Customer, Payment).join(Payment, Payment.customer_id == Customer.id)
        .where(Payment.status == "Over due", Payment.voided_at.is_(None))).all()
    names: dict[str, int] = {}
    for customer, payment in rows:
        days = (today - (payment.overdue_since or payment.due_date)).days
        if days > 7:
            names[full_name(customer)] = max(names.get(full_name(customer), 0), days)
    return Expected(
        "q22",
        f"{len(names)} customers Over due by more than 7 days: "
        f"{', '.join(f'{n} ({d} days)' for n, d in sorted(names.items()))}.",
        names, numbers=(Num("customers", len(names)),), names_all=tuple(sorted(names)),
        notes="Names are allowed. No address, mobile or email.")


def _received_between(db: Session, first: date, last: date, kind: str | None = None) -> int:
    return sum(p.amount_rupees for p in db.scalars(select(Payment)) if p.status == "Received"
               and p.voided_at is None and p.received_at is not None
               and first <= ist_date(p.received_at) <= last and (kind is None or p.kind == kind))


def q23_collections(db: Session, today: date) -> Expected:
    this_monday = week_start(today)
    last = _received_between(db, this_monday - timedelta(days=7), this_monday - timedelta(days=1))
    before = _received_between(
        db, this_monday - timedelta(days=14), this_monday - timedelta(days=8))
    this_week = _received_between(db, this_monday, today)
    return Expected(
        "q23",
        f"Collected last week ({this_monday - timedelta(days=7):%d-%b-%y} to "
        f"{this_monday - timedelta(days=1):%d-%b-%y}): {money(last)}; the week before: "
        f"{money(before)}. (This week so far: {money(this_week)}.)",
        {"last_week": last, "week_before": before, "this_week": this_week},
        numbers=(Num("last week", last), Num("week before", before)),
        notes="Weeks run Monday to Sunday (IST). Collected means Received, by received date.")


def q24_addon_revenue(db: Session, today: date) -> Expected:
    revenue = _received_between(db, month_start(today), today, "Add-on")
    return Expected(
        "q24", f"Add-on revenue received this month ({month_start(today):%B %Y}): {money(revenue)}.",
        {"revenue": revenue}, numbers=(Num("revenue", revenue),),
        notes="Received add-on payments by received date; prices include GST.")


def q35_last_quarter_revenue(db: Session, today: date) -> Expected:
    first, last = quarter_bounds_before(today)
    revenue = _received_between(db, first, last)
    return Expected(
        "q35",
        f"Last quarter ({first:%d-%b-%y} to {last:%d-%b-%y}): {money(revenue)} received. "
        + ("The seed data has no payments in that period, so the data is missing."
           if revenue == 0 else ""),
        {"revenue": revenue, "from": first.isoformat(), "to": last.isoformat()},
        numbers=(Num("revenue", revenue),) if revenue else (), cannot_say=revenue == 0)


# ---- HR -------------------------------------------------------------------------------------


def q26_crew_counts(db: Session) -> Expected:
    rows = db.execute(select(SchedulingCrew, Login).join(
        Login, SchedulingCrew.login_id == Login.id)).all()
    active = [c for c, login in rows if c.active and login.active]
    by_role: dict[str, int] = defaultdict(int)
    for member in active:
        by_role[member.role] += 1
    paired = sum(1 for m in active if m.role == "Trainee" and m.paired_member_id is not None)
    detail = ", ".join(f"{k}: {v}" for k, v in sorted(by_role.items()))
    return Expected(
        "q26", f"{len(active)} active crew ({detail}); {paired} trainees are paired.",
        {"active": len(active), "by_role": dict(by_role), "paired_trainees": paired},
        numbers=(Num("active", len(active)), *(Num(k, v) for k, v in by_role.items()),
                 Num("paired trainees", paired)),
        names_all=tuple(by_role))


def q27_missed_skipped_by_crew(db: Session, today: date) -> Expected:
    counts: dict[str, int] = defaultdict(int)
    for _job, visit, name in db.execute(
            select(Job, Visit, Login.display_name).join(Visit, Job.visit_id == Visit.id)
            .join(SchedulingCrew, Job.crew_id == SchedulingCrew.id)
            .join(Login, SchedulingCrew.login_id == Login.id)
            .where(Job.status.in_(("Skipped", "Could not complete")))):
        if visit.date >= month_start(today):
            counts[name] += 1
    if not counts:
        return Expected("q27", "No crew has missed or skipped jobs this month.", {},
                        numbers=(Num("count", 0),))
    most = max(counts.values())
    top = sorted(n for n, c in counts.items() if c == most)
    return Expected(
        "q27", f"Most missed or skipped jobs this month: {', '.join(top)} ({most} each).",
        dict(counts), numbers=(Num("most", most),), names_any=tuple(top))


def q28_blocked_crew(db: Session, now: datetime) -> Expected:
    blocked = sorted(
        login.display_name for login in db.scalars(select(Login).where(Login.role == "crew"))
        if login.locked or (login.blocked_until is not None and login.blocked_until > now))
    return Expected(
        "q28", f"Blocked or locked crew accounts: {len(blocked)} ({', '.join(blocked) or 'none'}).",
        blocked, numbers=(Num("blocked", len(blocked)),), names_all=tuple(blocked),
        notes="Locked (legacy admin lock) or blocked until a future time after wrong passwords.")


# ---- Hindi, mixed and owner-decision questions ----------------------------------------------


def q37_overdue_customers(db: Session) -> Expected:
    customers = {p.customer_id for p in db.scalars(select(Payment).where(
        Payment.status == "Over due", Payment.voided_at.is_(None)))}
    return Expected(
        "q37", f"{len(customers)} customers have an Over due payment.", len(customers),
        numbers=(Num("customers", len(customers)),),
        notes="Over due is a current state, so this counts customers Over due now.")


def q38_green_meadows(db: Session) -> Expected:
    found = list(db.scalars(select(Society).where(Society.name.like("%Green Meadows%"))))
    if found:
        raise AssertionError("The dataset now has a Green Meadows society; give Q38 numbers.")
    return Expected(
        "q38", "There is no society called Green Meadows in the seed data, so the answer is that "
        "it cannot be found.", None, cannot_say=True,
        notes="Proposed seed addition: a Green Meadows society with complaints.")


def q42_jobs_on_1_jan(db: Session) -> Expected:
    count = len(_jobs_on(db, date(2026, 1, 1)))
    return Expected(
        "q42", f"{count} jobs on 01-Jan-26: the seed data has none, so the data is missing.",
        count, cannot_say=count == 0, numbers=() if count == 0 else (Num("jobs", count),))


def q49_lowest_rated_customers(db: Session) -> Expected:
    rating = q06_ratings(db)
    lowest = set(rating.value["lowest"])
    names: set[str] = set()
    visit_society = {str(v.id): (name, c) for v, name, c in db.execute(
        select(Visit, Society.name, Customer).join(Vehicle, Visit.vehicle_id == Vehicle.id)
        .join(Society, Vehicle.society_id == Society.id)
        .join(Customer, Vehicle.customer_id == Customer.id))}
    for item in db.scalars(select(VisitRating)):
        society, customer = visit_society[item.visit_id]
        if society in lowest:
            names.add(full_name(customer))
    return Expected(
        "q49",
        f"Lowest-rated: {', '.join(sorted(lowest))}. Customer names: {', '.join(sorted(names))}. "
        "The phone number is declined.", {"societies": sorted(lowest), "customers": sorted(names)},
        names_any=tuple(sorted(names)), extras={"customers": sorted(names)})


def q50_deep_spa_over_due_on_completion(db: Session) -> Expected:
    rows = db.execute(
        select(AddonBooking, Payment).join(Payment, AddonBooking.payment_id == Payment.id)
        .where(AddonBooking.service == "Deep Spa", AddonBooking.status == "Completed")).all()
    over = [b for b, p in rows if p.status == "Over due"]
    unpaid = [b for b, p in rows if p.status != "Received"]
    return Expected(
        "q50",
        f"{len(over)} completed Deep Spa add-ons are Over due ({len(rows)} completed, "
        f"{len(unpaid)} unpaid). The rule: an add-on payment becomes Over due the moment its "
        "service completes.",
        {"over_due": len(over), "completed": len(rows), "unpaid": len(unpaid)},
        numbers=(Num("over due", len(over)),),
        notes="In the seed every completed add-on is already Received, so none is Over due.")


# ---- All ------------------------------------------------------------------------------------


def compute_all(db: Session, now: datetime) -> dict[str, Expected]:
    """Every live question's expected answer, keyed by `q01` and so on."""
    today = ist_date(now)
    q15 = q15_jobs_today(db, today)
    results = [
        q01_active_by_plan(db), q02_societies_by_subscribers(db),
        q03_inactive_last_30_days(db, today), q04_pause_skip_months(db, today),
        q05_complaints_this_month(db, today), q06_ratings(db), q15,
        q16_absent_crew(db, today), q17_at_risk(db, today, now), q18_pending_deep_spa(db),
        q19_on_time_rate(db, today, now), q20_capacity(db, today),
        q21_cycle_money(db, today), q22_overdue_over_7_days(db, today),
        q23_collections(db, today), q24_addon_revenue(db, today),
        q35_last_quarter_revenue(db, today), q26_crew_counts(db),
        q27_missed_skipped_by_crew(db, today), q28_blocked_crew(db, now),
        q37_overdue_customers(db), q38_green_meadows(db), q42_jobs_on_1_jan(db),
        q49_lowest_rated_customers(db), q50_deep_spa_over_due_on_completion(db),
    ]
    out = {r.key: r for r in results}
    # Question 36 is question 15 asked in Hindi: the same figures.
    missed = q15.value["missed"]
    out["q36"] = Expected("q36", f"{missed} jobs missed today (the same count as question 15).",
                          missed, numbers=(Num("missed", missed),),
                          notes="Answered in Hindi, addressing the Founder with 'ji'.")
    return out
