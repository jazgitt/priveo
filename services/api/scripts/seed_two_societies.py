"""Two synthetic societies (TEST S1 and TEST S2) that can be added to and removed from a
LOCAL development database on demand, for trying Mani Bond (Walk) against realistic data.

    LOCAL_SEED_PASSWORD=... python scripts/seed_two_societies.py \\
        --database-url postgresql+psycopg://me@localhost/priveo_mani  init-marker --confirm-local-dev-database
    ... add [--as-of 2026-11-02] [--force-reload] [--no-schedule]
    ... status
    ... counts          (row count of every table, for before/after checks)
    ... remove

Safety. The target is only ever the URL given with --database-url or LOCAL_SEED_DATABASE_URL
(never DATABASE_URL). It must be PostgreSQL on localhost, 127.0.0.1, ::1 or a unix socket, and
ENVIRONMENT must not be test or prod. The database must carry this tool's marker, which only
`init-marker` writes, on an already migrated database that has the single Admin. Nothing here
creates application tables; schema comes from the Alembic migrations.

Payment status. No status is chosen when a subscription is created: it comes from the cycle
dates and today's date (the as-of day). The tool only sets each subscription's first service date,
then runs the daily payments job logic: the current cycle's payment is made as
generate_due_payments makes it (due on the cycle's last day; seeded subscriptions only), Paid and
Initiated are recorded on it afterwards as the admin would, and mark_overdue_and_inactive marks
Over due payments and makes subscriptions Inactive after 7 days late. No past payments are
invented. Dates for a 30-day cycle (see CURRENT_CYCLE_MIX):
  first service date 9 or 19 days ago ........ cycle ends in 20 or 10 days: Not Due
  first service date 24 or 28 days ago ....... ends in 5 or 1 days: Due
  first service date 29 days ago ............. ends today: Due today
  first service date 31 to 36 days ago ....... first cycle ended 1 to 6 days ago, unpaid: Over due
  first service date 38 to 42 days ago ....... ended 9 to 13 days ago: Over due, then Inactive
  Initiated or Paid (recorded) ............... any of the above dates
All six display statuses appear. Add-on payments are Open (booking Requested) or Paid (Completed).
Note: mark_overdue_and_inactive works on every unpaid payment in the target database, not only
the seeded ones.

What remove deletes. Every row this tool created (listed in `two_society_seed_manifest`) plus
every row that references one of them through a foreign key, found by walking the metadata,
including rows made while testing by hand on the seeded customers, vehicles or crew. It never
touches the Admin, other societies, other customers, services, settings, or any plan or add-on
this tool did not create. The one add-on it edits (an existing "Deep Spa") is put back to the
values it had. Plans and add-ons it created are removed unless something else still uses them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
import warnings
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import (
    JSON,
    Column,
    MetaData,
    String,
    Table,
    delete,
    func,
    insert,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.addons.models import AddonBooking
from app.billing.models import Payment
from app.changes.models import ScheduleChange
from app.crew.models import CrewMember
from app.customers.models import Customer, SchedulePattern, Subscription, Vehicle
from app.directory.defaults import WEEKDAYS
from app.directory.models import (
    AddonCatalogueItem,
    DirectoryAudit,
    Plan,
    Society,
    WorkingSlot,
)
from app.identity.models import Login
from app.identity.service import hash_password
from app.platform.clock import today_ist
from app.platform.db import Base, make_engine
from app.platform.sync_guard import refuse_if_restored
from app.scheduling import service as scheduling
from app.scheduling.models import (
    Job,
    SchedulingCrew,
    SchedulingCrewException,
    Visit,
)
from app.support.models import AdminAlert, Complaint

NAMESPACE = uuid.UUID("5d0f6f55-6e0e-4a52-9d3c-2b1a8c7e4f10")
MARKER = "priveo-two-societies-seed-v1"
IST_OFFSET_HOURS = 5.5

_meta = MetaData()
CONTROL = Table("two_society_seed_control", _meta,
                Column("key", String(40), primary_key=True), Column("value", String(120)))
MANIFEST = Table("two_society_seed_manifest", _meta,
                 Column("table_name", String(80), primary_key=True),
                 Column("pk", String(80), primary_key=True))
BEFORE = Table("two_society_seed_before", _meta,
               Column("table_name", String(80), primary_key=True),
               Column("pk", String(80), primary_key=True),
               Column("old_values", JSON))

SOCIETIES = (("S1", "TEST S1", 40, 7, (1, 4, 2)), ("S2", "TEST S2", 100, 18, (2, 11, 5)))
PLANS = (
    ("Basic", 999, False, ["Daily external cleaning (Mon to Sat)"], 0),
    ("Premium", 1299, True,
     ["Daily external cleaning (Mon to Sat)", "One internal cleaning a week"], 1),
    ("Luxe", 1999, True,
     ["Daily external cleaning (Mon to Sat)", "Two internal cleanings a week"], 2),
)
# name, price, catalogue minutes. All four map to the fixed service "Deep Spa": the scheduler
# takes a job's length from the service (120 min), not from the catalogue row.
ADDONS = (
    ("Deep Spa", 5999, 120), ("Chauffeur on demand", 1999, 120),
    ("KB Overhaul", 9999, 240), ("Paintjob", 7999, 360),
)
MODELS = (("Hyundai", "Creta", "SUV"), ("Maruti Suzuki", "Swift", "Hatchback"),
          ("Honda", "City", "Sedan"), ("Tata", "Nexon", "Compact SUV"),
          ("Toyota", "Innova Crysta", "MUV"), ("Kia", "Seltos", "SUV"))
WORKING_DAYS = list(range(6))  # Monday to Saturday; Sunday is the weekly off


def ident(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


class SeedError(Exception):
    """A refusal or a problem the person running the tool should read."""


# ---- guards -----------------------------------------------------------------------------------


def check_target(url: str, environment: str | None = None) -> None:
    """Refuse anything that is not a local PostgreSQL database in a non-hosted environment."""
    environment = (os.environ.get("ENVIRONMENT", "dev") if environment is None else environment)
    if environment.strip().lower() in {"test", "prod", "production"}:
        raise SeedError(f"ENVIRONMENT is {environment!r}: this tool only runs for local development.")
    if not url:
        raise SeedError("Give --database-url or set LOCAL_SEED_DATABASE_URL.")
    parsed = make_url(url)
    if not parsed.drivername.startswith("postgresql"):
        raise SeedError("The target must be a local PostgreSQL database.")
    host = (parsed.host or "").strip().lower()
    socket_host = str(parsed.query.get("host", ""))
    if host and host not in {"localhost", "127.0.0.1", "::1"} and not host.startswith("/"):
        raise SeedError(f"{host!r} is not a local host. This tool never touches hosted databases.")
    if socket_host and not socket_host.startswith("/") and socket_host not in {"localhost", "127.0.0.1"}:
        raise SeedError(f"{socket_host!r} is not a local host.")
    own = urlparse(os.environ.get("DATABASE_URL", "")).hostname or ""
    if own and own not in {"localhost", "127.0.0.1", "::1"} and host and host == own:
        raise SeedError("That is the host of DATABASE_URL, which is not local.")


def check_marked(engine: Engine) -> None:
    if CONTROL.name not in inspect(engine).get_table_names():
        raise SeedError("This database is not marked for the seed tool. Run init-marker first, "
                        "on a local development database only.")
    with engine.connect() as connection:
        marker = connection.scalar(select(CONTROL.c.value).where(CONTROL.c.key == "marker"))
    if marker != MARKER:
        raise SeedError("The database marker does not match this tool.")


def init_marker(engine: Engine, *, confirmed: bool) -> str:
    if not confirmed:
        raise SeedError("Pass --confirm-local-dev-database to mark this database.")
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables or "logins" not in tables:
        raise SeedError("The database is not migrated. Apply the Alembic migrations first.")
    with Session(engine) as db:
        admins = db.scalars(select(Login).where(Login.role == "admin")).all()
    if len(admins) != 1:
        raise SeedError(f"Expected exactly one Admin login, found {len(admins)}.")
    _meta.create_all(engine)
    with engine.begin() as connection:
        existing = connection.scalar(select(CONTROL.c.value).where(CONTROL.c.key == "marker"))
        if existing is None:
            connection.execute(insert(CONTROL).values(key="marker", value=MARKER))
    return "marked"


# ---- manifest ---------------------------------------------------------------------------------


def _track(db: Session, objs) -> None:
    for obj in objs:
        table = obj.__table__
        pk = [getattr(obj, col.key) for col in table.primary_key.columns]
        db.execute(
            text("INSERT INTO two_society_seed_manifest (table_name, pk) VALUES (:t, :p) "
                 "ON CONFLICT (table_name, pk) DO NOTHING")
            if db.bind.dialect.name == "postgresql"
            else text("INSERT OR IGNORE INTO two_society_seed_manifest (table_name, pk) VALUES (:t, :p)"),
            {"t": table.name, "p": "|".join(str(v) for v in pk)},
        )


def _manifest(db: Session) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for table_name, pk in db.execute(select(MANIFEST.c.table_name, MANIFEST.c.pk)):
        out.setdefault(table_name, set()).add(pk)
    return out


def _add(db: Session, *objs) -> None:
    db.add_all(objs)
    db.flush()
    _track(db, objs)


# ---- add --------------------------------------------------------------------------------------


def _hours(evening: bool) -> list[dict]:
    rows = []
    for index, name in enumerate(WEEKDAYS):
        row = {"day": name, "working": index in WORKING_DAYS, "start": "05:00", "end": "11:00"}
        if evening and index in WORKING_DAYS:
            row["extra_slots"] = [{"start": "17:00", "end": "19:00"}]
        rows.append(row)
    return rows


def _setup_globals(db: Session) -> tuple[list[Plan], list[AddonCatalogueItem]]:
    plans = []
    for name, price, interior, inclusions, order in PLANS:
        if db.scalar(select(Plan).where(Plan.name == name)) is not None:
            raise SeedError(f"A plan named {name!r} already exists that this tool did not create.")
        plan = Plan(id=ident(f"plan:{name}"), name=name, monthly_price_rupees=price,
                    includes_interior=interior, inclusions=inclusions, sort_order=order)
        _add(db, plan)
        plans.append(plan)
    items = []
    for order, (name, price, minutes) in enumerate(ADDONS, start=1):
        existing = db.scalar(select(AddonCatalogueItem).where(AddonCatalogueItem.name == name))
        if existing is not None:
            if name != "Deep Spa":
                raise SeedError(f"An add-on named {name!r} already exists that this tool did not create.")
            db.execute(insert(BEFORE).values(
                table_name="addon_catalogue", pk=str(existing.id),
                old_values={"price_rupees": existing.price_rupees,
                            "list_price_rupees": existing.list_price_rupees,
                            "duration_minutes": existing.duration_minutes,
                            "active": existing.active}))
            existing.price_rupees = price
            existing.duration_minutes = minutes
            existing.active = True
            items.append(existing)
            continue
        item = AddonCatalogueItem(
            id=ident(f"addon:{name}"), name=name, service="Deep Spa", price_rupees=price,
            duration_minutes=minutes, active=True, sort_order=order,
            description=f"TEST {name} (synthetic add-on).")
        _add(db, item)
        items.append(item)
    db.flush()
    return plans, items


def _vehicle_count(i: int) -> int:
    return 4 + (i // 2) % 2 if i % 2 == 0 else 1 + (i // 2) % 2


# The current cycle of an ordinary Active vehicle: (what is recorded on it, days to the due date,
# which is the cycle's last day). Nothing is stored by hand: the first service date puts the
# cycle where the date rule needs it, the daily job logic makes the payment, and Paid or
# Initiated is recorded on it afterwards, as the admin or the customer would. Dates (30-day cycle,
# due on its last day, today = the as-of day): 20 or 10 days left is Not Due, 5 or 1 is Due, 0 is
# Due today, a first service date 31 days ago or more is Over due (the overdue vehicles below,
# 1 to 6 days late stay Active; 9 to 13 days late the job makes Inactive), Initiated and Paid are
# recorded. Ten rows, used in turn.
CURRENT_CYCLE_MIX = (
    ("Paid", 25), ("Paid", 12), ("Paid", 5), (None, 20), (None, 10),
    (None, 5), (None, 1), (None, 0), ("Initiated", 2), ("Paid", 15),
)


def _record_payments(db, admin, now, planned, late_start):
    """Makes the payments the way the daily job would have. A subscription that started a cycle
    ago and has not paid had its first payment made on its first service date (`late_start`);
    each subscription's current cycle payment is made as generate_due_payments does it (only for
    the seeded subscriptions). Then the Paid and Initiated ones are recorded, as the admin would,
    and the job marks the late ones Over due and makes the long-late subscriptions Inactive.
    No past payment is invented."""
    from app.billing.config import get_money_settings
    from app.billing.service import BillingService, mark_overdue_and_inactive
    from app.changes.cycle import cycle_window

    service = BillingService(db, lambda: now, get_money_settings())
    today = (now + timedelta(hours=IST_OFFSET_HOURS)).date()
    seeded = db.execute(
        select(Subscription, Vehicle).join(Vehicle, Vehicle.id == Subscription.vehicle_id)
        .where(Vehicle.source_ref.like("seed2:%"))).all()
    for sub, vehicle in seeded:
        if sub.id in late_start:
            service.ensure_cycle_payment(sub, vehicle, sub.first_service_date)
        start, _ = cycle_window(sub.first_service_date, 0, today, service._cycle_days)
        service.ensure_cycle_payment(sub, vehicle, start)
    db.commit()
    for sub_id, state in planned.items():
        payment = db.scalar(select(Payment).where(
            Payment.subscription_id == sub_id, Payment.status == "Open", Payment.kind == "Plan"))
        service._apply(payment, state, admin.id, "Synthetic baseline")
    db.commit()
    mark_overdue_and_inactive(now, db=db)
    db.commit()


def _seed_society(db, admin, plans, addons, tag, name, n_customers, n_crew, roles, day, now,
                  password_hash, sequence, counters, planned, late_start):
    s_no = int(tag[1:])
    society = Society(id=ident(f"{tag}:society"), name=name, city="Synthetic City",
                      sector="Seed data")
    _add(db, society)
    # Working days Monday to Saturday. The Deep Spa slot is open all day on those days.
    for service, start, end in (("Cleaning-External", 300, 660), ("Cleaning-Internal", 300, 660),
                                ("Deep Spa", 0, 1440)):
        _add(db, WorkingSlot(id=ident(f"{tag}:slot:{service}"), society_id=society.id,
                             service=service, start_minute=start, end_minute=end,
                             days=WORKING_DAYS))

    # ---- crew
    managers, members, trainees = roles
    kinds = ["Manager"] * managers + ["Member"] * members + ["Trainee"] * trainees
    crew, member_ids, evening_left = [], [], 3
    for index, role in enumerate(kinds):
        mobile = f"98{s_no}{index + 1:07d}"
        evening = role == "Member" and evening_left > 0
        if evening:
            evening_left -= 1
        login = Login(id=ident(f"{tag}:crew-login:{index}"), role="crew", login_id=mobile,
                      display_name=f"TEST {tag} {role} {index + 1}", password_hash=password_hash,
                      password_changed_at=now)
        _add(db, login)
        paired = member_ids[index % len(member_ids)] if role == "Trainee" and member_ids else None
        hours = _hours(evening)
        sched = SchedulingCrew(id=ident(f"{tag}:crew:{index}"), login_id=login.id,
                               society_id=society.id, role=role, working_hours=hours,
                               start_minute=300, end_minute=1140 if evening else 660,
                               paired_member_id=paired)
        _add(db, sched,
             CrewMember(id=ident(f"{tag}:crew-member:{index}"), login_id=login.id,
                        name=login.display_name, mobile=mobile, society_id=society.id,
                        role=role, working_hours=hours))
        crew.append(sched)
        if role == "Member":
            member_ids.append(sched.id)

    # ---- customers and vehicles
    big = [i for i in range(n_customers) if i % 2 == 0]
    # S2: seven Inactive vehicles over four customers (2 + 2 + 2 + 1), all in the big households.
    inactive_owners = ({big[5]: 2, big[15]: 2, big[25]: 2, big[35]: 1}
                       if tag == "S2" and len(big) > 35 else {})
    # About a tenth of the customers owe an overdue payment; the Inactive owners count in S2.
    n_overdue = max(1, n_customers // 10 - len(inactive_owners))
    overdue_small = set(range(1, 2 * n_overdue + 1, 2))
    vehicles_made = 0
    for i in range(n_customers):
        email = f"{tag.lower()}.c{i + 1:03d}@priveo.test"
        has_password = i < 5
        login = Login(id=ident(f"{tag}:cust-login:{i}"), role="customer", login_id=email,
                      display_name=f"TEST {tag} Customer {i + 1:03d}",
                      password_hash=password_hash if has_password else None,
                      password_changed_at=now if has_password else None)
        _add(db, login)
        customer = Customer(
            id=ident(f"{tag}:customer:{i}"), login_id=login.id, first_name="TEST",
            last_name=f"{tag} C{i + 1:03d}", email=email,
            mobile=f"900{s_no}{i + 1:06d}", society_id=society.id,
            flat=f"T{i // 10 + 1}-{i % 10 + 101}", source="admin", terms_accepted_at=now,
            onboarding_confirmed_at=now, email_verified_at=now)
        _add(db, customer)
        inactive_left = inactive_owners.get(i, 0)
        for v in range(_vehicle_count(i)):
            vehicles_made += 1
            n = vehicles_made
            make, model, category = MODELS[(i + v) % len(MODELS)]
            vehicle = Vehicle(
                id=ident(f"{tag}:vehicle:{i}:{v}"), customer_id=customer.id, society_id=society.id,
                registration=f"TS0{s_no}SD{n:05d}", make=make, model=model, variant="Base",
                category=category, parking_basement="B1", parking_number=str(n),
                source_ref=f"seed2:{tag}:{n}")
            _add(db, vehicle)
            plan = plans[(i + v) % 3]
            # The current cycle ends `days_left` days from today (negative: Over due).
            inactive = inactive_left > 0 and v < inactive_left
            overdue_days = None
            if inactive:
                overdue_days = 9 + (n % 5)  # more than 7 days: the job makes the plan Inactive
            elif i in overdue_small and v == 0:
                overdue_days = 1 + (i % 6)  # 6 days or fewer: the plan is still Active
            record = None
            if overdue_days is not None:
                days_left = -overdue_days
            else:
                record, days_left = CURRENT_CYCLE_MIX[(i + v) % len(CURRENT_CYCLE_MIX)]
            cycle_start = day + timedelta(days=days_left - 29)
            if days_left < 0:
                late_start.add(ident(f"{tag}:sub:{i}:{v}"))
            # The first service date is where the date rule needs the cycle. A late vehicle
            # started one cycle ago: its first payment is the overdue one.
            first = cycle_start
            sub = Subscription(
                id=ident(f"{tag}:sub:{i}:{v}"), vehicle_id=vehicle.id, plan_id=plan.id,
                monthly_price_rupees=plan.monthly_price_rupees, status="Active",
                first_service_date=first,
                cutoff_time=time(11), interior_day=None)
            _add(db, sub)
            if record:
                planned[sub.id] = record
            interior = []
            if plan.name == "Premium":
                interior = [WEEKDAYS[(i + v) % 6]]
            elif plan.name == "Luxe":
                interior = [WEEKDAYS[(i + v) % 6], WEEKDAYS[((i + v) + 3) % 6]]
            _add(db, SchedulePattern(
                id=ident(f"{tag}:pattern:{i}:{v}"), subscription_id=sub.id, kind="Weekly",
                exterior_weekdays=list(WEEKDAYS[:6]), interior_weekdays=interior))
            counters["vehicles"] += 1
            counters["overdue"] += days_left < 0
            status = "Inactive" if inactive else "Active"  # what the daily job will leave it as
            # A skip or a pause on some vehicles
            if status == "Active" and (i + v) % 13 == 0:
                kind = "pause" if (i + v) % 26 == 0 else "skip"
                start = day + timedelta(days=2 + v)
                _add(db, ScheduleChange(
                    id=ident(f"{tag}:change:{i}:{v}"), customer_id=customer.id,
                    vehicle_id=vehicle.id, kind=kind, start_date=start,
                    end_date=start + timedelta(days=2 if kind == "pause" else 0),
                    status="Active", actor="customer", actor_login_id=login.id))
                counters["changes"] += 1
            # An add-on booking on the first vehicle of about one customer in six
            if v == 0 and i % 6 == 0:
                item = addons[(i // 6) % 4]
                booking_state = ["Requested", "Completed", "Requested"][(i // 6) % 3]
                offset = 2 + (i % 4) if booking_state == "Requested" else -(2 + i % 5)
                pay_state = "Paid" if booking_state == "Completed" else "Open"
                due = day + timedelta(days=offset)
                pay = Payment(
                    id=ident(f"payment:{tag}:addon:{i}"), customer_id=customer.id,
                    vehicle_id=vehicle.id, kind="Add-on", description=item.name,
                    amount_rupees=item.price_rupees, status=pay_state, due_date=due,
                    received_at=now if pay_state == "Paid" else None,
                    confirmed_by=admin.id if pay_state == "Paid" else None)
                _add(db, pay)
                _add(db, AddonBooking(
                    id=ident(f"{tag}:booking:{i}"), customer_id=customer.id,
                    vehicle_id=vehicle.id, service="Deep Spa", addon_code=item.code,
                    addon_name=item.name, proposed_date=due, finish_by=time(18),
                    status=booking_state, price_rupees=item.price_rupees, payment_id=pay.id))
                counters["bookings"] += 1
        if i % 12 == 5:
            sequence[0] += 1
            _add(db, Complaint(
                id=ident(f"{tag}:complaint:{i}"), number=sequence[0], customer_id=customer.id,
                category="Service quality", description="TEST synthetic complaint",
                status=["Raised", "In progress", "Resolved"][(i // 12) % 3]))
            counters["complaints"] += 1
    return society, crew


def add(engine: Engine, as_of: date | None = None, password: str = "", *,
        customers: tuple[int, int] | None = None, schedule: bool = True,
        force_reload: bool = False) -> dict:
    check_marked(engine)
    if force_reload:
        remove(engine)
    with Session(engine, expire_on_commit=False) as db:
        if db.scalar(select(func.count()).select_from(MANIFEST)):
            raise SeedError("The two societies are already added. Use remove, or --force-reload.")
        admins = db.scalars(select(Login).where(Login.role == "admin")).all()
        if len(admins) != 1:
            raise SeedError("Expected exactly one Admin login.")
        admin = admins[0]
        day = as_of or today_ist()
        now = datetime.combine(day, time(10), tzinfo=UTC) - timedelta(hours=IST_OFFSET_HOURS)
        password_hash = hash_password(password) if password else None
        counters = {k: 0 for k in
                    ("vehicles", "overdue", "inactive", "active", "changes", "bookings",
                     "complaints")}
        try:
            plans, addons = _setup_globals(db)
            sequence = [db.scalar(select(func.coalesce(func.max(Complaint.number), 0)))]
            societies = {}
            planned: dict = {}
            late_start: set = set()
            for index, (tag, name, n_cust, n_crew, roles) in enumerate(SOCIETIES):
                size = customers[index] if customers else n_cust
                societies[tag] = _seed_society(db, admin, plans, addons, tag, name, size, n_crew,
                                               roles, day, now, password_hash, sequence, counters, planned, late_start)
            db.commit()
            _record_payments(db, admin, now, planned, late_start)
            counters["inactive"] = db.scalar(
                select(func.count()).select_from(Subscription).join(
                    Vehicle, Vehicle.id == Subscription.vehicle_id)
                .where(Vehicle.source_ref.like("seed2:%"), Subscription.status == "Inactive"))
            counters["active"] = counters["vehicles"] - counters["inactive"]
            summary: dict = {"as_of": day.isoformat(), **counters, "schedule": {}}
            if schedule:
                summary["schedule"] = _schedule_overlay(db, admin, societies, day)
            _record_closure(db)
            db.commit()
        except Exception:
            db.rollback()
            db.close()
            remove(engine)  # take out whatever the failed run left behind
            raise
    return summary


def _schedule_overlay(db: Session, admin: Login, societies: dict, day: date) -> dict:
    """Run tomorrow (frozen) and the six days after it (a Draft) through the real scheduler,
    then make one crew member absent tomorrow and one job unmovable (Completed)."""
    tomorrow = day + timedelta(days=1)
    out = {}
    for tag, (society, _crew) in societies.items():
        first = scheduling.get_or_create_schedule(db, society.id, tomorrow, 1)
        scheduling.run_schedule(db, first, admin.id)
        db.commit()
        rest = scheduling.get_or_create_schedule(db, society.id, tomorrow + timedelta(days=1), 6)
        scheduling.run_schedule(db, rest, admin.id)
        db.commit()
        scheduling.freeze(db, first, admin.id)
        jobs = db.execute(
            select(Job, Visit).join(Visit, Visit.id == Job.visit_id)
            .where(Visit.schedule_id.in_([first.id, rest.id]))).all()
        placed = [j for j, _ in jobs if j.crew_id is not None]
        unplaced = [j for j, _ in jobs if j.crew_id is None and j.status == "Scheduled"]
        # The most loaded Member tomorrow is the one who is away.
        load: dict[uuid.UUID, int] = {}
        for job, visit in jobs:
            if visit.schedule_id == first.id and job.crew_id is not None:
                load[job.crew_id] = load.get(job.crew_id, 0) + 1
        absent = max(load, key=load.get) if load else None
        if absent is not None:
            _add(db, SchedulingCrewException(
                id=ident(f"{tag}:absence"), crew_id=absent, on_date=tomorrow, kind="Sick"))
        done = next((j for j, v in jobs
                     if v.schedule_id == first.id and j.crew_id is not None), None)
        if done is not None:
            scheduling.set_job_status(db, done.id, "Completed")
        db.commit()
        out[tag] = {
            "jobs": len(jobs), "placed": len(placed), "unplaced": len(unplaced),
            "absent_crew_jobs": load.get(absent, 0) if absent else 0,
            "frozen_day": tomorrow.isoformat(), "completed_job": str(done.id) if done else None}
    return out


def _closure(db: Session) -> dict[str, set]:
    """Every row reachable from the seeded societies and logins through foreign keys."""
    manifest = _manifest(db)
    tables = Base.metadata.tables
    selected: dict[str, set] = {name: set() for name in tables}
    for name in ("societies", "logins"):
        for pk in manifest.get(name, ()):
            selected[name].add(uuid.UUID(pk))
    keep_roots = {"plans", "addon_catalogue"}

    def keys_in(table):
        cols = list(table.primary_key.columns)
        return cols[0].in_(list(selected[table.name]))

    changed = True
    while changed:
        changed = False
        for name, table in tables.items():
            if name in keep_roots:
                continue
            primary = list(table.primary_key.columns)
            if len(primary) != 1:
                continue
            for fk in table.foreign_keys:
                parent = fk.column.table
                if parent.name in keep_roots or not selected[parent.name]:
                    continue
                parents = list(selected[parent.name]) if fk.column.primary_key else [
                    v for (v,) in db.execute(select(fk.column).where(keys_in(parent)))]
                if not parents:
                    continue
                found = {row[0] for row in db.execute(
                    select(primary[0]).where(fk.parent.in_(parents)))}
                extra = found - selected[name]
                if extra:
                    selected[name] |= extra
                    changed = True
        refs = {str(k) for keys in selected.values() for k in keys}
        alerts = set(db.scalars(select(AdminAlert.id).where(AdminAlert.ref_id.in_(refs)))) \
            if refs else set()
        extra = alerts - selected["admin_alerts"]
        if extra:
            selected["admin_alerts"] |= extra
            changed = True
        # The scheduler and billing write audit rows that name a schedule or a payment by a
        # plain string, not a key.
        named = {str(k) for name in ("schedules", "payments") for k in selected[name]}
        audit = set()
        for start in range(0, len(named), 5000):
            audit |= set(db.scalars(select(DirectoryAudit.id).where(
                DirectoryAudit.entity.in_(("schedule", "payment")),
                DirectoryAudit.entity_id.in_(list(named)[start:start + 5000]))))
        extra = audit - selected["directory_audit"]
        if extra:
            selected["directory_audit"] |= extra
            changed = True
    return selected


def _record_closure(db: Session) -> None:
    closure = _closure(db)
    for name, keys in closure.items():
        for pk in keys:
            db.execute(
                text("INSERT INTO two_society_seed_manifest (table_name, pk) VALUES (:t, :p) "
                     "ON CONFLICT (table_name, pk) DO NOTHING")
                if db.bind.dialect.name == "postgresql"
                else text("INSERT OR IGNORE INTO two_society_seed_manifest (table_name, pk) "
                          "VALUES (:t, :p)"),
                {"t": name, "p": str(pk)})


# ---- remove / status / counts -------------------------------------------------------------------


def remove(engine: Engine) -> dict:
    check_marked(engine)
    removed: dict[str, int] = {}
    with Session(engine) as db:
        if not db.scalar(select(func.count()).select_from(MANIFEST)):
            return removed
        closure = _closure(db)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ordered = list(reversed(Base.metadata.sorted_tables))
        for table in ordered:
            keys = closure.get(table.name)
            if not keys or table.name in {"plans", "addon_catalogue"}:
                continue
            pk = list(table.primary_key.columns)
            if len(pk) != 1:
                continue
            keys = list(keys)
            for start in range(0, len(keys), 5000):
                result = db.execute(delete(table).where(pk[0].in_(keys[start:start + 5000])))
                removed[table.name] = removed.get(table.name, 0) + result.rowcount
        manifest = _manifest(db)
        before = {(r.table_name, r.pk): r.old_values for r in db.execute(select(BEFORE))}
        for (table_name, pk), old in before.items():  # an existing add-on this tool edited
            item = db.get(AddonCatalogueItem, uuid.UUID(pk)) if table_name == "addon_catalogue" else None
            if item is not None:
                for field, value in old.items():
                    setattr(item, field, value)
        for pk in manifest.get("addon_catalogue", ()):
            item = db.get(AddonCatalogueItem, uuid.UUID(pk))
            if item is not None:
                _delete_if_unused(db, AddonCatalogueItem, item, removed)
        for pk in manifest.get("plans", ()):
            plan = db.get(Plan, uuid.UUID(pk))
            if plan is not None:
                _delete_if_unused(db, Plan, plan, removed)
        db.execute(delete(MANIFEST))
        db.execute(delete(BEFORE))
        db.commit()
    return removed


def _delete_if_unused(db: Session, model, row, removed: dict) -> None:
    try:
        with db.begin_nested():
            db.delete(row)
            db.flush()
        removed[model.__tablename__] = removed.get(model.__tablename__, 0) + 1
    except Exception:  # still referenced by something this tool did not create: leave it
        removed[f"{model.__tablename__} kept (in use)"] = 1


def status(engine: Engine) -> dict:
    check_marked(engine)
    with Session(engine) as db:
        manifest = _manifest(db)
    return {name: len(keys) for name, keys in sorted(manifest.items()) if keys}


def counts(engine: Engine) -> dict[str, int]:
    out = {}
    with engine.connect() as connection:
        for table in sorted(Base.metadata.sorted_tables, key=lambda t: t.name):
            out[table.name] = connection.scalar(select(func.count()).select_from(table))
    return out


# ---- command line -------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", default=os.environ.get("LOCAL_SEED_DATABASE_URL", ""))
    sub = parser.add_subparsers(dest="command", required=True)
    mark = sub.add_parser("init-marker")
    mark.add_argument("--confirm-local-dev-database", action="store_true")
    adder = sub.add_parser("add")
    adder.add_argument("--as-of", type=date.fromisoformat)
    adder.add_argument("--force-reload", action="store_true")
    adder.add_argument("--no-schedule", action="store_true")
    adder.add_argument("--customers", type=int, nargs=2, metavar=("S1", "S2"))
    for name in ("remove", "status", "counts"):
        sub.add_parser(name)
    args = parser.parse_args(argv)
    try:
        check_target(args.database_url)
        engine = make_engine(args.database_url)
        refuse_if_restored(engine, "seed_two_societies")
        if args.command == "init-marker":
            result = init_marker(engine, confirmed=args.confirm_local_dev_database)
        elif args.command == "add":
            password = os.environ.get("LOCAL_SEED_PASSWORD", "")
            if not password:
                raise SeedError("Set LOCAL_SEED_PASSWORD (a local password for the seeded logins).")
            result = add(engine, args.as_of, password,
                         customers=tuple(args.customers) if args.customers else None,
                         schedule=not args.no_schedule, force_reload=args.force_reload)
        elif args.command == "remove":
            result = remove(engine)
        elif args.command == "status":
            result = status(engine)
        else:
            result = counts(engine)
    except SeedError as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
