"""The two-society seed tool: its guards, and a full add / remove round trip on the test database
(in-memory SQLite by default, PostgreSQL in CI)."""
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.addons.models import AddonBooking
from app.customers.models import Customer, Subscription, Vehicle
from app.directory.models import AddonCatalogueItem, Plan, Society
from app.directory.seed import seed_defaults
from app.identity.seed import seed_logins
from app.scheduling import service as scheduling
from app.scheduling.models import Job, SchedulingCrew
from app.support.models import Complaint
from scripts import seed_two_societies as seed

AS_OF = date(2026, 11, 2)  # a Monday


@pytest.fixture(autouse=True)
def clean_tool_tables(engine):
    # These tables sit outside the ORM metadata, so the engine fixture does not drop them.
    drop = ("two_society_seed_before", "two_society_seed_manifest", "two_society_seed_control",
            "alembic_version")
    with engine.begin() as connection:
        for name in drop:
            connection.execute(text(f"DROP TABLE IF EXISTS {name}"))
    yield
    with engine.begin() as connection:
        for name in drop:
            connection.execute(text(f"DROP TABLE IF EXISTS {name}"))


@pytest.fixture(autouse=True)
def quick_solver(monkeypatch):
    """The solver's real limit is 10 seconds a day; a fraction of a second is enough here."""
    original = scheduling.solve_day
    monkeypatch.setattr(scheduling, "solve_day",
                        lambda crew, jobs, max_seconds=0.3: original(crew, jobs, max_seconds))


@pytest.fixture
def prepared(engine, settings):
    """A migrated-looking database with the Admin and the directory defaults, then marked."""
    with Session(engine) as db:
        seed_logins(db, settings)
        seed_defaults(db)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('0042')"))
    seed.init_marker(engine, confirmed=True)
    return engine


# ---- guards -------------------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://me@localhost/priveo_mani",
    "postgresql+psycopg://me@127.0.0.1:5432/priveo_mani",
    "postgresql+psycopg://me@/priveo_mani?host=/tmp",
])
def test_local_postgres_urls_pass(url):
    seed.check_target(url, "dev")


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://u:p@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
    "postgresql+psycopg://u:p@db.example.com/priveo",
    "postgresql+psycopg://u:p@10.0.0.5/priveo",
    "sqlite:///local.db",
    "mysql://me@localhost/x",
    "",
])
def test_non_local_or_non_postgres_targets_are_refused(url):
    with pytest.raises(seed.SeedError):
        seed.check_target(url, "dev")


@pytest.mark.parametrize("environment", ["test", "prod", "production", " Test "])
def test_hosted_environments_are_refused(environment):
    with pytest.raises(seed.SeedError, match="local development"):
        seed.check_target("postgresql+psycopg://me@localhost/priveo_mani", environment)


def test_environment_variable_is_read_when_not_given(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    with pytest.raises(seed.SeedError):
        seed.check_target("postgresql+psycopg://me@localhost/priveo_mani")


def test_an_unmarked_database_is_refused(engine, settings):
    with Session(engine) as db:
        seed_logins(db, settings)
    for call in (lambda: seed.add(engine, AS_OF, "pw", schedule=False),
                 lambda: seed.remove(engine), lambda: seed.status(engine)):
        with pytest.raises(seed.SeedError, match="not marked"):
            call()


def test_marking_needs_confirmation_a_migrated_database_and_one_admin(engine, settings):
    with Session(engine) as db:
        seed_logins(db, settings)
    with pytest.raises(seed.SeedError, match="--confirm"):
        seed.init_marker(engine, confirmed=False)
    with pytest.raises(seed.SeedError, match="not migrated"):
        seed.init_marker(engine, confirmed=True)


def test_a_wrong_marker_value_is_refused(prepared):
    with prepared.begin() as connection:
        connection.execute(text("UPDATE two_society_seed_control SET value='something-else'"))
    with pytest.raises(seed.SeedError, match="does not match"):
        seed.status(prepared)


# ---- add and remove -----------------------------------------------------------------------------


def _count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_add_builds_the_spec_and_remove_restores_every_table(prepared):
    before = seed.counts(prepared)
    with Session(prepared) as db:
        customers_before = _count(db, Customer)
        deep_spa = db.scalar(select(AddonCatalogueItem).where(AddonCatalogueItem.name == "Deep Spa"))
        old = (deep_spa.price_rupees, deep_spa.duration_minutes)
    summary = seed.add(prepared, AS_OF, "Local-pw-1", customers=(6, 10))
    assert summary["vehicles"] == 17 + 29  # the vehicle counts follow the customer index
    with Session(prepared) as db:
        names = [s.name for s in db.scalars(select(Society).order_by(Society.name))
                 if s.name.startswith("TEST S")]
        assert names == ["TEST S1", "TEST S2"]
        assert _count(db, Customer) - customers_before == 16
        assert [(p.name, p.monthly_price_rupees) for p in db.scalars(
            select(Plan).where(Plan.name.in_(["Basic", "Premium", "Luxe"])).order_by(
                Plan.sort_order))] == [("Basic", 999), ("Premium", 1299), ("Luxe", 1999)]
        prices = {i.name: i.price_rupees for i in db.scalars(select(AddonCatalogueItem))}
        assert prices["Deep Spa"] == 5999 and prices["Chauffeur on demand"] == 1999
        assert prices["KB Overhaul"] == 9999 and prices["Paintjob"] == 7999
        roles: dict[tuple[str, str], int] = {}
        for crew, society in db.execute(select(SchedulingCrew, Society).join(
                Society, Society.id == SchedulingCrew.society_id)):
            roles[(society.name, crew.role)] = roles.get((society.name, crew.role), 0) + 1
        assert roles == {("TEST S1", "Manager"): 1, ("TEST S1", "Member"): 4,
                         ("TEST S1", "Trainee"): 2, ("TEST S2", "Manager"): 2,
                         ("TEST S2", "Member"): 11, ("TEST S2", "Trainee"): 5}
        evening = [c for c in db.scalars(select(SchedulingCrew))
                   if "17:00" in str(c.working_hours)]
        assert len(evening) == 6 and {c.role for c in evening} == {"Member"}
        assert _count(db, Job) > 0
        sunday = [h for c in db.scalars(select(SchedulingCrew).limit(1)) for h in c.working_hours
                  if h["day"] == "Sunday"]
        assert sunday and sunday[0]["working"] is False
    assert seed.status(prepared)["customers"] == 16
    with pytest.raises(seed.SeedError, match="already added"):
        seed.add(prepared, AS_OF, "Local-pw-1", customers=(6, 10))

    with Session(prepared) as db:  # something done by hand on a seeded customer
        customer = db.scalars(select(Customer).where(Customer.email.like("s1.%"))).first()
        db.add(Complaint(number=9001, customer_id=customer.id, category="Service quality",
                         description="made by hand", status="Raised"))
        db.commit()
    removed = seed.remove(prepared)
    assert removed["customers"] == 16 and removed["complaints"] >= 1
    assert seed.counts(prepared) == before
    assert seed.remove(prepared) == {}  # a second remove changes nothing
    with Session(prepared) as db:
        deep_spa = db.scalar(select(AddonCatalogueItem).where(AddonCatalogueItem.name == "Deep Spa"))
        assert (deep_spa.price_rupees, deep_spa.duration_minutes) == old


def test_remove_leaves_other_societies_and_their_customers_alone(prepared):
    with Session(prepared) as db:
        other = Society(name="Real Society", city="Pune")
        db.add(other)
        db.commit()
    before = seed.counts(prepared)
    seed.add(prepared, AS_OF, "Local-pw-1", customers=(4, 4), schedule=False)
    seed.remove(prepared)
    assert seed.counts(prepared) == before
    with Session(prepared) as db:
        assert db.scalar(select(Society).where(Society.name == "Real Society")) is not None


def test_force_reload_replaces_the_data_and_refuses_a_name_clash(prepared):
    seed.add(prepared, AS_OF, "Local-pw-1", customers=(4, 4), schedule=False)
    summary = seed.add(prepared, AS_OF, "Local-pw-1", customers=(4, 4), schedule=False,
                       force_reload=True)
    assert summary["vehicles"] > 0
    with Session(prepared) as db:
        assert _count(db, Society) == 3 and _count(db, Plan) >= 3  # the demo society stays
    seed.remove(prepared)
    with Session(prepared) as db:  # a plan with the same name that the tool did not make
        db.add(Plan(name="Luxe", monthly_price_rupees=5, includes_interior=False))
        db.commit()
    before = seed.counts(prepared)
    with pytest.raises(seed.SeedError, match="already exists"):
        seed.add(prepared, AS_OF, "Local-pw-1", customers=(4, 4), schedule=False)
    assert seed.counts(prepared) == before  # the failed add cleaned up after itself


def test_overdue_and_inactive_rules_hold(prepared):
    seed.add(prepared, AS_OF, "Local-pw-1", customers=(40, 100), schedule=False)
    with Session(prepared) as db:
        from app.billing.models import Payment

        inactive = db.scalars(select(Subscription).where(Subscription.status == "Inactive")).all()
        assert len(inactive) == 7
        inactive_ids = {s.id for s in inactive}
        late = db.scalars(select(Payment).where(
            Payment.status == "Open", Payment.kind == "Plan", Payment.due_date < AS_OF)).all()
        assert late
        for payment in late:
            age = (AS_OF - payment.due_date).days
            if payment.subscription_id in inactive_ids:
                assert age > 7
            else:
                assert 1 <= age <= 6
        owners = {db.get(Vehicle, s.vehicle_id).customer_id for s in inactive}
        assert 1 < len(owners) < 7  # seven vehicles spread over a few customers
        counts_by_customer = dict(db.execute(
            select(Vehicle.customer_id, func.count()).group_by(Vehicle.customer_id)).all())
        many = sum(1 for n in counts_by_customer.values() if n > 3)
        assert many == 70  # half of the 40 and half of the 100 customers
        assert _count(db, AddonBooking) > 0


def test_seed_shows_all_six_payment_statuses(prepared):
    from app.billing.models import Payment
    from app.billing.status import DISPLAY_STATUSES, STORED_STATUSES, display_status

    seed.add(prepared, AS_OF, "Local-pw-1", customers=(40, 100), schedule=False)
    with Session(prepared) as db:
        payments = db.scalars(select(Payment)).all()
        assert {p.status for p in payments} <= set(STORED_STATUSES)
        shown = {display_status(p, AS_OF).status for p in payments if p.kind == "Plan"}
        assert shown == set(DISPLAY_STATUSES)
        current = {}  # the latest cycle of each subscription
        for p in sorted((p for p in payments if p.kind == "Plan"), key=lambda p: p.cycle_start):
            current[p.subscription_id] = p
        seeded = db.scalars(select(Subscription.id).join(Vehicle, Vehicle.id == Subscription.vehicle_id)
                            .where(Vehicle.source_ref.like("seed2:%"))).all()
        assert seeded and set(seeded) <= set(current)  # one current-cycle payment each
        # Earlier cycles are all Paid.
        for p in payments:
            if p.kind == "Plan" and p.cycle_start < current[p.subscription_id].cycle_start:
                assert p.status == "Paid"
