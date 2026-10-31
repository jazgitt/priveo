"""The local seed dataset the evaluation runs against.

It is built by the existing synthetic test-data tool (`scripts/test_data.py`: every
catalogue scenario, anchored on a fixed day), so the eval uses the same realistic data
the rest of the repo tests with. Nothing here copies seed code. The database is a
throwaway SQLite file, never a real database."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.billing.models import Payment
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import Society
from app.identity.models import Login
from app.platform.clock import IST
from app.platform.db import Base
from app.scheduling.models import Job, SchedulingCrew
from app.support.models import Complaint, VisitRating
from scripts.test_data import catalogue, initialize, open_database, refresh

# Synthetic values for the throwaway database only. They are not real credentials.
FIXTURE_PASSWORD = "EvalFixturePassword123!"
FIXTURE_ADMIN_PASSWORD = "EvalAdminPassword123!"

# Friday 30-Oct-26, 11:30 IST. The seed tool anchors its data on this IST date.
FIXED_NOW = datetime(2026, 10, 30, 11, 30, tzinfo=IST).astimezone(UTC)


@dataclass(frozen=True)
class DatasetReport:
    """What `build_dataset` created, counted from the database."""

    today: str
    scenarios: int
    counts: dict[str, int]
    # Values that must never appear in an answer. A customer name is allowed (D14).
    customer_mobiles: tuple[str, ...] = field(default_factory=tuple)
    customer_emails: tuple[str, ...] = field(default_factory=tuple)
    customer_flats: tuple[str, ...] = field(default_factory=tuple)

    def describe(self) -> str:
        lines = [f"Dataset for {self.today}: {self.scenarios} scenarios"]
        lines += [f"  {name}: {count}" for name, count in self.counts.items()]
        return "\n".join(lines)


def make_engine_at(path: Path) -> Engine:
    """A dedicated SQLite file with foreign keys on (the seed tool refuses anything else)."""
    return open_database(path)


def build_dataset(session: Session, now: datetime = FIXED_NOW) -> DatasetReport:
    """Create the dataset in the (empty) SQLite database behind `session`.

    `now` fixes "today": the IST date of `now` is the seed's anchor day. Running it twice
    on one database refreshes the same rows, so the result is the same."""
    engine = session.get_bind()
    if engine.dialect.name != "sqlite":
        raise ValueError("The eval dataset is built in a throwaway SQLite database only.")
    if now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware.")
    session.commit()  # the seed tool opens its own sessions
    initialize(engine, FIXTURE_PASSWORD, FIXTURE_ADMIN_PASSWORD)
    day = now.astimezone(IST).date()
    refresh(engine, [item["id"] for item in catalogue()], day, FIXTURE_PASSWORD)
    _clamp_created_at(session, now)
    session.expire_all()
    return describe_dataset(session, day.isoformat())


def _clamp_created_at(session: Session, now: datetime) -> None:
    """The seed stamps new rows with the real clock, which can be after the fixed `now`. A
    question about "so far" or "this week" would then miss them. Nothing is created in the
    future of the day the eval pretends it is."""
    for mapper in Base.registry.mappers:
        column = mapper.local_table.c.get("created_at")
        if column is not None:
            session.execute(update(mapper.local_table).where(column > now).values(created_at=now))
    session.commit()


def describe_dataset(session: Session, today: str) -> DatasetReport:
    def count(model) -> int:
        return session.scalar(select(func.count()).select_from(model)) or 0

    counts = {
        "societies": count(Society),
        "customers": count(Customer),
        "vehicles": count(Vehicle),
        "subscriptions": count(Subscription),
        "crew": count(SchedulingCrew),
        "jobs": count(Job),
        "payments": count(Payment),
        "addon bookings": count(AddonBooking),
        "complaints": count(Complaint),
        "visit ratings": count(VisitRating),
        "admin logins": session.scalar(
            select(func.count()).select_from(Login).where(Login.role == "admin")) or 0,
    }
    customers = list(session.scalars(select(Customer)))
    return DatasetReport(
        today=today, scenarios=len(catalogue()), counts=counts,
        customer_mobiles=tuple(sorted({c.mobile for c in customers})),
        customer_emails=tuple(sorted({c.email for c in customers})),
        customer_flats=tuple(sorted({c.flat for c in customers if c.flat})))
