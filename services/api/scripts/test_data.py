"""Synthetic manual/E2E fixtures. Only opens an explicit, marked local SQLite file.

Never reads DATABASE_URL. See docs/testing/test-data-plan.md for commands and limits.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import uuid
import warnings
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, delete, event, inspect, select, text, tuple_
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.addons.models import AddonBooking
from app.billing.models import Invoice, Payment, PaymentEvent
from app.billing.tax import included_gst
from app.changes.models import PlanExtension, ScheduleChange
from app.crew.models import CrewMember
from app.customers.models import AddonRequest, Customer, Subscription, Vehicle
from app.directory import settings_registry
from app.directory.defaults import CHECKLISTS, WEEKDAYS
from app.directory.models import Plan, Society, WorkingSlot
from app.directory.seed import seed_defaults
from app.identity.models import Login
from app.identity.service import hash_password
from app.notifications.models import Notification, NotificationPreference
from app.platform.clock import IST, today_ist
from app.platform.db import Base
from app.scheduling.models import (
    Job,
    Schedule,
    SchedulingCrew,
    SchedulingCrewException,
    Visit,
)
from app.support.models import (
    AdminAlert,
    CheckIn,
    Complaint,
    ComplaintUpdate,
    Feedback,
    VisitRating,
)
from app.visits.models import JobChecklistProgress, JobOutcome, JobTiming

ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = ROOT / "tools/test-data/scenarios.json"
NAMESPACE = uuid.UUID("79897a5b-9f3a-472c-9a7e-a1bccb235d87")
MARKER = "priveo-synthetic-test-data-v1"


def identity(scenario: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{scenario}:{key}")


def catalogue() -> list[dict]:
    return json.loads(CATALOGUE.read_text(encoding="utf-8"))["scenarios"]


def open_database(path: Path):
    """Use SQLite only; enforce FKs, including during partial resets."""
    path = path.resolve()
    if path.suffix not in {".sqlite", ".sqlite3"}:
        raise ValueError("Use a dedicated .sqlite or .sqlite3 file.")
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path.as_posix()}")

    @event.listens_for(engine, "connect")
    def enable_fks(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    return engine


def verify_database(engine) -> None:
    if engine.dialect.name != "sqlite":
        raise ValueError("This seed tool supports dedicated local SQLite only.")
    if "test_data_control" not in inspect(engine).get_table_names():
        raise ValueError("Database is not marked for test data. Initialize an EMPTY file first.")
    with engine.connect() as connection:
        marker = connection.scalar(text("SELECT value FROM test_data_control WHERE key='marker'"))
    if marker != MARKER:
        raise ValueError("Database marker does not match this fixture tool.")


def initialize(engine, password: str, admin_password: str) -> None:
    """Never adopt an existing application DB, even if its filename looks safe."""
    if not password or not admin_password:
        raise ValueError(
            "Set TEST_DATA_PASSWORD and TEST_DATA_ADMIN_PASSWORD before initialization."
        )
    if engine.dialect.name != "sqlite":
        raise ValueError("Initialization supports dedicated local SQLite only.")
    tables = inspect(engine).get_table_names()
    if tables:
        verify_database(engine)
        return
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE test_data_control (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        )
        connection.execute(
            text("INSERT INTO test_data_control VALUES ('marker', :value)"), {"value": MARKER}
        )
    with Session(engine) as db:
        db.add(
            Login(
                id=identity("shared", "admin"),
                role="admin",
                login_id="priveopapa",
                display_name="Manual test Admin",
                password_hash=hash_password(admin_password),
                alert_email_enabled=False,
            )
        )
        db.add_all(
            [
                Society(
                    id=identity("shared", "secondary-society"),
                    name="TEST Secondary Society",
                    city="Synthetic City",
                    sector="Cross-society fixtures",
                ),
                Plan(
                    id=identity("shared", "internal-plan"),
                    name="TEST External + Internal",
                    monthly_price_rupees=999,
                    includes_interior=True,
                    inclusions=["Daily external cleaning", "Weekly internal cleaning"],
                ),
                Plan(
                    id=identity("shared", "external-plan"),
                    name="TEST External Only",
                    monthly_price_rupees=699,
                    includes_interior=False,
                    inclusions=["Daily external cleaning"],
                ),
            ]
        )
        db.commit()
        # The normal seed reads .env-backed payment/supplier/contact defaults.
        # Fixture initialization deliberately uses registry placeholders instead.
        with patch(
            "app.directory.settings_registry.default_for",
            side_effect=lambda key: str(settings_registry.BY_KEY[key].default),
        ):
            seed_defaults(db)


def _remove_scenario(db: Session, scenario: str) -> None:
    """Find descendants by FK, including records added while manually testing.

    Plain-string alert references are also followed. Deferred FKs handle the
    vehicle/media and retry-job cycles without disabling referential integrity.
    Admin and global catalogue/settings never enter the descendant set.
    """
    tables = Base.metadata.tables
    selected: dict[str, set] = {name: set() for name in tables}
    selected["societies"].add(identity(scenario, "society"))
    selected["logins"].add(identity(scenario, "customer-login"))
    for index in range(6):
        selected["logins"].add(identity(scenario, f"crew-login-{index}"))
    selected["admin_alerts"].update(identity(scenario, f"alert-{index}") for index in range(6))

    def keys_condition(table):
        columns = list(table.primary_key.columns)
        return (
            columns[0].in_(selected[table.name])
            if len(columns) == 1
            else tuple_(*columns).in_(selected[table.name])
        )

    changed = True
    while changed:
        changed = False
        for name, table in tables.items():
            primary = list(table.primary_key.columns)
            for foreign in table.foreign_keys:
                parent_table = foreign.column.table
                if not selected[parent_table.name]:
                    continue
                parents = list(
                    db.scalars(select(foreign.column).where(keys_condition(parent_table)))
                )
                rows = db.execute(select(*primary).where(foreign.parent.in_(parents))).all()
                children = {row[0] if len(primary) == 1 else tuple(row) for row in rows}
                extra = children - selected[name]
                if extra:
                    selected[name].update(extra)
                    changed = True
        refs = {str(key) for keys in selected.values() for key in keys}
        alerts = set(db.scalars(select(AdminAlert.id).where(AdminAlert.ref_id.in_(refs))))
        extra = alerts - selected["admin_alerts"]
        if extra:
            selected["admin_alerts"].update(extra)
            changed = True
    db.execute(text("PRAGMA defer_foreign_keys=ON"))
    # SQLite checks all remaining references at COMMIT, so cycles are safe.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # SQLAlchemy's known cyclic metadata ordering warning.
        ordered = list(reversed(Base.metadata.sorted_tables))
    for table in ordered:
        if selected[table.name]:
            db.execute(delete(table).where(keys_condition(table)))


def _seed_scenario(db: Session, config: dict, day: date, password_hash: str) -> dict:
    scenario = config["id"]
    number = next(index for index, item in enumerate(catalogue(), 1) if item["id"] == scenario)
    now = datetime.combine(day, time(10), IST).astimezone(UTC)
    admin = db.scalar(select(Login).where(Login.role == "admin"))
    society = Society(
        id=identity(scenario, "society"),
        name=f"TEST {scenario} {config['name']}",
        city="Synthetic City",
        sector="Test fixtures",
    )
    login = Login(
        id=identity(scenario, "customer-login"),
        role="customer",
        login_id=f"test.{scenario.lower()}@priveo.test",
        display_name=f"Test {scenario}",
        # C30 has no password yet: its first sign-in is by the emailed code.
        password_hash=None if config.get("no_password") else password_hash,
        password_changed_at=None if config.get("no_password") else now,
    )
    db.add_all([society, login])
    db.flush()
    onboarding = config.get("onboarding", True)
    customer = Customer(
        id=identity(scenario, "customer"),
        login_id=login.id,
        first_name="Test",
        last_name=scenario,
        email=login.login_id,
        mobile=f"99000{number:05d}",
        society_id=society.id,
        flat="TEST-101",
        source="migration" if config.get("legacy") else "admin",
        terms_accepted_at=now if onboarding else None,
        onboarding_confirmed_at=now if onboarding else None,
        email_verified_at=now if onboarding else None,
    )
    db.add(customer)
    hours = [
        {
            "day": name,
            "working": True,
            "start": "05:00",
            "end": "05:10" if config.get("short_hours") else "14:00",
        }
        for name in WEEKDAYS
    ]
    crews = []
    crew_logins = []
    roles = ["Manager", "Member", "Trainee"]
    if config.get("attendance") or config.get("crew_accounts"):
        roles += ["Member", "Member", "Member"]
    for index, role in enumerate(roles):
        mobile = f"980{number:04d}{index:03d}"
        crew_login = Login(
            id=identity(scenario, f"crew-login-{index}"),
            role="crew",
            login_id=mobile,
            display_name=f"TEST {scenario} {role} {index}",
            password_hash=password_hash,
            password_changed_at=now,
            active=not (config.get("crew_accounts") and index == 4),
            locked=bool(config.get("crew_accounts") and index == 5),
        )
        db.add(crew_login)
        db.flush()
        crew = SchedulingCrew(
            id=identity(scenario, f"crew-{index}"),
            login_id=crew_login.id,
            society_id=society.id,
            role=role,
            working_hours=hours,
            start_minute=300,
            end_minute=310 if config.get("short_hours") else 840,
            active=crew_login.active,
            paired_member_id=crews[1].id if role == "Trainee" else None,
        )
        db.add_all(
            [
                crew,
                CrewMember(
                    id=identity(scenario, f"crew-member-{index}"),
                    login_id=crew_login.id,
                    name=crew_login.display_name,
                    mobile=mobile,
                    society_id=society.id,
                    role=role,
                    working_hours=hours,
                ),
            ]
        )
        db.flush()
        crews.append(crew)
        crew_logins.append(crew_login)
    for service, start, end in [
        ("Cleaning-External", 300, 660),
        ("Cleaning-Internal", 300, 660),
        ("Deep Spa", 0, 1440),
    ]:
        db.add(
            WorkingSlot(
                id=identity(scenario, f"slot-{service}"),
                society_id=society.id,
                service=service,
                start_minute=start,
                end_minute=end,
                days=list(range(7)),
            )
        )
    if config.get("attendance"):
        for index, kind in zip([3, 4, 5], ["Sick", "Leave", "Late start"], strict=True):
            db.add(
                SchedulingCrewException(
                    id=identity(scenario, f"attendance-{index}"),
                    crew_id=crews[index].id,
                    on_date=day,
                    kind=kind,
                    from_minute=480 if kind == "Late start" else None,
                )
            )
    db.flush()
    vehicle_ids, payment_ids, visit_ids, schedule_ids, booking_ids = [], [], [], [], []
    states = config.get("payment_states", ["Received"])
    cycle_age = config.get("cycle_age", 26 if config.get("checkin") else 0)
    subscriptions = []

    def payment(vehicle, index, status, *, addon=False, offset=0, void=False):
        cycle = (
            day - timedelta(days=35 if vehicle.active is False else 3)
            if status == "Over due"
            else day - timedelta(days=cycle_age)
        )
        if not addon and subscriptions[index].status == "Activating":
            cycle = subscriptions[index].first_service_date
        payment_day = day + timedelta(days=offset) if addon else cycle
        item = Payment(
            id=identity(scenario, f"payment-{'addon' if addon else 'plan'}-{index}"),
            customer_id=customer.id,
            vehicle_id=vehicle.id,
            subscription_id=None if addon else subscriptions[index].id,
            kind="Add-on" if addon else "Plan",
            description="Deep Spa" if addon else "TEST plan cycle",
            amount_rupees=1500 if addon else subscriptions[index].monthly_price_rupees,
            status=status,
            due_date=payment_day,
            cycle_start=None if addon else cycle,
            cycle_end=None if addon else cycle + timedelta(days=29),
            overdue_since=payment_day if status == "Over due" else None,
            initiated_at=now if status == "Initiated" else None,
            received_at=now if status == "Received" else None,
            confirmed_by=admin.id if status == "Received" else None,
            voided_at=now if void else None,
        )
        db.add(item)
        db.flush()
        db.add(
            PaymentEvent(
                id=identity(scenario, f"event-{item.id}"),
                payment_id=item.id,
                to_status=status,
                by_login_id=admin.id if status == "Received" else None,
                at=now,
                note="Synthetic baseline",
            )
        )
        payment_ids.append(str(item.id))
        if status == "Received":
            tax = included_gst(item.amount_rupees, 18, "CGST_SGST")
            tax["mock_configuration"] = True
            db.add(
                Invoice(
                    id=identity(scenario, f"invoice-{item.id}"),
                    payment_id=item.id,
                    number=f"TEST-{scenario}-{'A' if addon else 'P'}-{index}",
                    issued_by=admin.id,
                    amount_rupees=item.amount_rupees,
                    customer_name=login.display_name,
                    vehicle_label=vehicle.registration or vehicle.model,
                    description=item.description,
                    seller_details={
                        "seller_name": "Placeholder TEST Priveo",
                        "seller_address": "Placeholder test address",
                        "seller_gstin": "Placeholder TEST GSTIN",
                    },
                    tax_details=None if config.get("legacy") else tax,
                    issued_at=now,
                )
            )
            if config.get("legacy"):
                db.flush()
                db.get(Invoice, identity(scenario, f"invoice-{item.id}")).seller_details = None
        return item

    def visit(
        vehicle, key, offset, status, *, booking=None, draft=False, unassigned=False, internal=False
    ):
        on_date = day + timedelta(days=offset)
        schedule_id = identity(scenario, f"schedule-{on_date}")
        if not db.get(Schedule, schedule_id):
            db.add(
                Schedule(
                    id=schedule_id,
                    society_id=society.id,
                    start_date=on_date,
                    end_date=on_date,
                    status="Draft" if draft else "Frozen",
                    frozen_at=None if draft else now - timedelta(days=2),
                    frozen_by=None if draft else admin.id,
                )
            )
            db.flush()
        schedule_ids.append(str(schedule_id))
        item = Visit(
            id=identity(scenario, f"visit-{key}"),
            schedule_id=schedule_id,
            vehicle_id=vehicle.id,
            date=on_date,
            status=status,
            addon_key=str(booking.id) if booking else "",
        )
        db.add(item)
        db.flush()
        service = (
            "Deep Spa" if booking else ("Cleaning-Internal" if internal else "Cleaning-External")
        )
        job_start = 360 + (int(key.rsplit("-", 1)[1]) * 25 if key.startswith("crew-day-") else 0)
        job = Job(
            id=identity(scenario, f"job-{key}"),
            visit_id=item.id,
            service=service,
            status=status,
            duration_minutes=120 if booking else 20,
            crew_id=None if unassigned else crews[1].id,
            start_minute=None if unassigned else job_start,
            finish_by_minute=840 if booking else 660,
            addon_booking_id=booking.id if booking else None,
            note="No available capacity" if unassigned else "",
            checklist_snapshot={
                "legacy": False,
                "items": [{"key": k, "label": label} for k, label in CHECKLISTS[service]],
            },
        )
        db.add(job)
        db.flush()
        if status in {"Completed", "In progress"}:
            started = datetime.combine(on_date, time(job_start // 60, job_start % 60), IST)
            db.add(
                JobTiming(
                    job_id=job.id,
                    started_at=started,
                    finished_at=started + timedelta(minutes=job.duration_minutes)
                    if status == "Completed"
                    else None,
                )
            )
            for key_name, _label in CHECKLISTS[service][: 5 if status == "Completed" else 2]:
                db.add(
                    JobChecklistProgress(
                        id=identity(scenario, f"check-{job.id}-{key_name}"),
                        job_id=job.id,
                        item_key=key_name,
                        checked_at=started,
                        checked_by=crew_logins[1].id,
                    )
                )
        if status in {"Skipped", "Could not complete"}:
            db.add(
                JobOutcome(
                    id=identity(scenario, f"outcome-{job.id}"),
                    job_id=job.id,
                    kind="skipped" if status == "Skipped" else "could_not_complete",
                    reason_key="car_not_in_spot" if status != "Skipped" else None,
                    note="Synthetic operational outcome",
                    by_login_id=crew_logins[0].id,
                    at=now,
                )
            )
            if status == "Skipped" and service == "Cleaning-External":
                db.add(
                    PlanExtension(
                        id=identity(scenario, f"extension-{job.id}"),
                        vehicle_id=vehicle.id,
                        job_id=job.id,
                        on_date=on_date,
                        by_login_id=crew_logins[0].id,
                    )
                )
        visit_ids.append(str(item.id))
        return item

    for index in range(config.get("vehicles", 1)):
        vehicle = Vehicle(
            id=identity(scenario, f"vehicle-{index}"),
            customer_id=customer.id,
            society_id=identity("shared", "secondary-society")
            if config.get("multi_society") and index % 2
            else society.id,
            registration=None if config.get("legacy") else f"TS{number:02d}TT{index + 1:04d}",
            make="Hyundai",
            model="Creta",
            variant="Base",
            category="SUV",
            parking_basement="B1",
            parking_number=str(index + 1),
            active=not config.get("vehicle_inactive", False),
            source_ref=f"test:{scenario}:{index}",
        )
        db.add(vehicle)
        db.flush()
        vehicle_ids.append(str(vehicle.id))
        if config.get("subscribed", True):
            inactive = index >= config.get("inactive_from", 999)
            status = "Inactive" if inactive else config.get("subscription_status", "Active")
            state = "Over due" if inactive or status == "Inactive" else states[index % len(states)]
            interior = config.get("interior", True)
            plan = db.get(
                Plan, identity("shared", "internal-plan" if interior else "external-plan")
            )
            sub = Subscription(
                id=identity(scenario, f"subscription-{index}"),
                vehicle_id=vehicle.id,
                plan_id=None if config.get("legacy") else plan.id,
                monthly_price_rupees=plan.monthly_price_rupees,
                first_service_date=(
                    day + timedelta(days=1)
                    if status == "Activating"
                    else day - timedelta(days=95 if status == "Inactive" else 93)
                    if state == "Over due"
                    else day - timedelta(days=90 + cycle_age)
                ),
                status=status,
                cutoff_time=time(11),
                interior_day=WEEKDAYS[day.weekday()] if interior else None,
                pending_plan_id=identity("shared", "external-plan")
                if config.get("pending_plan")
                else None,
                pending_from=day + timedelta(days=30) if config.get("pending_plan") else None,
            )
            db.add(sub)
            db.flush()
            subscriptions.append(sub)
            pay = payment(vehicle, index, state)
            if status == "Inactive":
                pay.cycle_start = day - timedelta(days=35)
                pay.cycle_end = day - timedelta(days=6)
                pay.due_date = pay.cycle_start
                pay.overdue_since = pay.cycle_start
        changes = config.get("changes")
        if changes:
            kind = "pause" if changes == "pause" or (changes == "mixed" and index % 2) else "skip"
            for count, active in enumerate([True, False]):
                start = day + timedelta(days=1 + index * 2 + count * 10)
                if kind == "pause" and index == 0 and active:
                    start = day - timedelta(days=1)
                db.add(
                    ScheduleChange(
                        id=identity(scenario, f"change-{index}-{count}"),
                        customer_id=customer.id,
                        vehicle_id=vehicle.id,
                        kind=kind,
                        start_date=start,
                        end_date=start + timedelta(days=2 if kind == "pause" else 0),
                        status="Active" if active else "Cancelled",
                        actor="customer",
                        actor_login_id=login.id,
                        ended_at=None if active else now,
                    )
                )
        addon_states = config.get("addons", []) if index == 0 else []
        if config.get("standalone"):
            addon_states = ["Missed" if states[index] == "Over due" else "Requested"]
        for addon_index, addon_status in enumerate(addon_states):
            item_index = index * 10 + addon_index
            offset = (
                -(addon_index + 1) if addon_status in {"Completed", "Missed"} else addon_index + 3
            )
            pay_state = (
                states[index]
                if config.get("standalone")
                else ("Received" if addon_status in {"Completed", "Scheduled"} else "Due")
            )
            pay = payment(
                vehicle,
                item_index,
                pay_state,
                addon=True,
                offset=offset,
                void=addon_status == "Cancelled",
            )
            booking = AddonBooking(
                id=identity(scenario, f"addon-{item_index}"),
                customer_id=customer.id,
                vehicle_id=vehicle.id,
                service="Deep Spa",
                standalone=bool(config.get("standalone")),
                proposed_date=day + timedelta(days=offset),
                finish_by=time(14),
                status=addon_status,
                price_rupees=1500,
                payment_id=pay.id,
                contact_mobile=customer.mobile if config.get("standalone") else "",
                cancelled_at=now if addon_status == "Cancelled" else None,
            )
            db.add(booking)
            db.flush()
            booking_ids.append(str(booking.id))
            if addon_status in {"Scheduled", "Completed", "Missed"}:
                visit(
                    vehicle,
                    f"addon-{item_index}",
                    offset,
                    "Could not complete" if addon_status == "Missed" else addon_status,
                    booking=booking,
                )
        if config.get("history") and index == 0:
            for count in range(3):
                item = visit(vehicle, f"history-{count}", -1 - count * 30, "Completed")
                if config.get("ratings"):
                    db.add(
                        VisitRating(
                            id=identity(scenario, f"rating-{count}"),
                            customer_id=customer.id,
                            visit_id=str(item.id),
                            rating=5 - count,
                            tags=[],
                            comment="Synthetic visit rating",
                        )
                    )
        if config.get("crew_day"):
            job_status = ["Scheduled", "In progress", "Completed", "Skipped", "Could not complete"][
                index
            ]
            visit(vehicle, f"crew-day-{index}", 0, job_status, internal=index == 1)
        if config.get("unassigned") and index == 0:
            visit(vehicle, "unassigned", 1, "Scheduled", draft=True, unassigned=True)
        if config.get("draft"):
            visit(vehicle, "draft", 1, "Scheduled", draft=True)
    if config.get("checkin") and subscriptions:
        db.add(
            CheckIn(
                id=identity(scenario, "checkin"),
                customer_id=customer.id,
                subscription_id=subscriptions[0].id,
                cycle_start=day - timedelta(days=cycle_age),
                answers=[{"category": "Value for money", "rating": 4}],
                comment="Synthetic check-in",
            )
        )
        db.add(
            Feedback(
                id=identity(scenario, "feedback"),
                customer_id=customer.id,
                category="Service quality",
                rating=4,
                comment="Synthetic feedback",
            )
        )
    if config.get("legacy"):
        db.add(
            AddonRequest(
                id=identity(scenario, "legacy-addon"),
                customer_id=customer.id,
                vehicle_id=None,
                service="Deep Spa",
                price_rupees=None,
                service_date=None,
                payment_status=None,
                notes="Unknown imported history",
                source_ref=f"test:{scenario}:legacy",
            )
        )
    if config.get("inbox"):
        for index, visit_id in enumerate(visit_ids[:2]):
            db.add(
                Notification(
                    id=identity(scenario, f"notification-{index}"),
                    login_id=login.id,
                    event="service_completed",
                    title=f"TEST {'Unread' if index == 0 else 'Read'} service message",
                    body="Synthetic service completion",
                    visit_id=visit_id,
                    ref_type="visit",
                    ref_id=visit_id,
                    created_at=now,
                    read_at=now if index else None,
                )
            )
        db.add(NotificationPreference(login_id=login.id, event="renewal_reminder", enabled=False))
    if config.get("complaints"):
        for index, status in enumerate(["Raised", "In progress", "Resolved", "Raised"]):
            complaint = Complaint(
                id=identity(scenario, f"complaint-{index}"),
                number=number * 100 + index,
                customer_id=customer.id,
                category="Cleaning quality",
                description=f"Synthetic {status} complaint",
                photo_keys=[],
                status=status,
                # The overdue one must be over 4 hours old by the real clock, even
                # when the fixture day's 10:00 IST anchor is still in the future.
                created_at=(
                    min(now, datetime.now(UTC)) - timedelta(hours=5)
                    if index == 3
                    else now - timedelta(hours=1)
                ),
                updated_at=now,
            )
            db.add(complaint)
            db.flush()
            db.add(
                ComplaintUpdate(
                    id=identity(scenario, f"complaint-update-{index}"),
                    complaint_id=complaint.id,
                    author_role="admin",
                    author_login_id=admin.id,
                    status=status,
                    note="Synthetic thread entry",
                    created_at=now,
                )
            )
    if config.get("alerts") or config.get("complaints") or config.get("unassigned"):
        for index in range(2):
            db.add(
                AdminAlert(
                    id=identity(scenario, f"alert-{index}"),
                    kind="test_data",
                    title=f"TEST {scenario} {'Unread' if index == 0 else 'Read'} alert",
                    body=config["name"],
                    created_at=now,
                    read_at=now if index else None,
                )
            )
    db.flush()
    payments = list(db.scalars(select(Payment).where(Payment.customer_id == customer.id)))
    return {
        "id": scenario,
        "name": config["name"],
        "as_of": day.isoformat(),
        "society_id": str(society.id),
        "customer_login": login.login_id,
        "first_sign_in": bool(config.get("no_password")),
        "customer_id": str(customer.id),
        "vehicle_ids": vehicle_ids,
        "active_vehicle_ids": [] if config.get("vehicle_inactive") else vehicle_ids,
        "crew_logins": [item.login_id for item in crew_logins],
        "crew_ids": [str(item.id) for item in crews],
        "payment_ids": payment_ids,
        "visit_ids": visit_ids,
        "schedule_ids": sorted(set(schedule_ids)),
        "booking_ids": booking_ids,
        "voided_payment_ids": [str(item.id) for item in payments if item.voided_at is not None],
    }


def refresh(engine, scenarios: list[str], day: date, password: str) -> dict:
    verify_database(engine)
    if not password:
        raise ValueError("Set TEST_DATA_PASSWORD before refreshing scenarios.")
    configs = {item["id"]: item for item in catalogue()}
    unknown = set(scenarios) - configs.keys()
    if unknown:
        raise ValueError(f"Unknown scenarios: {', '.join(sorted(unknown))}")
    password_hash = hash_password(password)
    with Session(engine) as db, db.begin():
        admins = list(db.scalars(select(Login).where(Login.role == "admin")))
        if len(admins) != 1 or admins[0].login_id != "priveopapa":
            raise ValueError("Expected exactly one Admin login: priveopapa.")
        for scenario in dict.fromkeys(scenarios):
            _remove_scenario(db, scenario)
            snapshot = _seed_scenario(db, configs[scenario], day, password_hash)
            db.execute(
                text(
                    "INSERT INTO test_data_control(key,value) VALUES (:key,:value) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
                ),
                {"key": f"scenario:{scenario}", "value": json.dumps(snapshot)},
            )
        errors = db.execute(text("PRAGMA foreign_key_check")).all()
        if errors:
            raise ValueError(f"Fixture foreign-key check failed: {errors}")
    return manifest(engine)


def manifest(engine) -> dict:
    verify_database(engine)
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text("SELECT value FROM test_data_control WHERE key LIKE 'scenario:%' ORDER BY key")
            )
            .scalars()
            .all()
        )
    return {
        "version": 1,
        "admin_login": "priveopapa",
        "scenarios": [json.loads(row) for row in rows],
        "limitations": [
            "Seeded historical jobs have checklist/timing/outcome records but no media files. "
            "Upload actual proof through the app for photo/video E2E cases.",
            "Offline queues and OTP/cutoff cases need device setup or controlled action tests.",
            "Global Admin settings/catalogue edits survive scenario refresh; --fresh resets them.",
        ],
    }


def fresh_start(path: Path, day: date, password: str) -> dict:
    """Build a complete replacement before atomically replacing the marked file.

    Keep the ONE Admin's login ID/password; clear test sessions, settings and
    every other manually added record. An unmarked database cannot be replaced.
    Stop the API first so Windows can replace the SQLite file.
    """
    engine = open_database(path)
    try:
        verify_database(engine)
        with Session(engine) as db:
            admins = list(db.scalars(select(Login).where(Login.role == "admin")))
            if len(admins) != 1 or admins[0].login_id != "priveopapa":
                raise ValueError("Expected exactly one Admin login: priveopapa.")
            admin_id, admin_hash, admin_name = (
                admins[0].id,
                admins[0].password_hash,
                admins[0].display_name,
            )
    finally:
        engine.dispose()
    replacement_path = path.resolve().with_name(f"{path.stem}.refresh-{uuid.uuid4().hex}.sqlite3")
    replacement = open_database(replacement_path)
    try:
        initialize(replacement, password, secrets.token_urlsafe(24))
        with Session(replacement) as db:
            admin = db.get(Login, identity("shared", "admin"))
            admin.id, admin.password_hash, admin.display_name = admin_id, admin_hash, admin_name
            db.commit()
        result = refresh(replacement, [item["id"] for item in catalogue()], day, password)
        replacement.dispose()
        os.replace(replacement_path, path.resolve())
        return result
    finally:
        replacement.dispose()
        if replacement_path.exists():
            replacement_path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--init", action="store_true")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Reset the entire MARKED test file; preserve Admin credentials",
    )
    parser.add_argument("--refresh", help="all or comma-separated IDs, e.g. C07,R01")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--database-file", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=today_ist())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    configs = catalogue()
    selected = (
        [item["id"] for item in configs]
        if args.refresh == "all"
        else ([item.strip().upper() for item in args.refresh.split(",")] if args.refresh else [])
    )
    unknown = set(selected) - {item["id"] for item in configs}
    if unknown:
        parser.error(f"Unknown scenarios: {', '.join(sorted(unknown))}")
    if args.list or args.dry_run:
        print(
            json.dumps(
                {
                    "as_of": args.as_of.isoformat(),
                    "scope": "fresh" if args.fresh else "scenario-refresh",
                    "scenarios": [
                        item for item in configs if not selected or item["id"] in selected
                    ],
                },
                indent=2,
            )
        )
        return
    if os.environ.get("ENVIRONMENT", "dev").lower() not in ("dev", "test"):
        parser.error("Fixture writes are allowed only with ENVIRONMENT=dev or test.")
    if not args.database_file:
        parser.error("Specify --database-file explicitly. DATABASE_URL is never used.")
    if args.output and (
        args.output.suffix.lower() != ".json"
        or args.output.resolve() == args.database_file.resolve()
    ):
        parser.error("Manifest output must be a separate .json file.")
    if args.fresh and (args.init or args.refresh):
        parser.error("Use --fresh separately from --init/--refresh.")
    if args.fresh:
        result = fresh_start(
            args.database_file, args.as_of, os.environ.get("TEST_DATA_PASSWORD", "")
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return
    engine = open_database(args.database_file)
    try:
        if args.init:
            initialize(
                engine,
                os.environ.get("TEST_DATA_PASSWORD", ""),
                os.environ.get("TEST_DATA_ADMIN_PASSWORD", ""),
            )
        result = (
            refresh(engine, selected, args.as_of, os.environ.get("TEST_DATA_PASSWORD", ""))
            if selected
            else manifest(engine)
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
