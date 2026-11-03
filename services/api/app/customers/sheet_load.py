"""One-time load of the customers on the owner's "Monthly Customer" sheet (3 Nov 2026).

The sheet has one row for each vehicle and no email, so a customer is loaded
without an email and without a sign-in (the login logic for them is still to
be decided). It sets up the four plans, creates the zones the sheet names, and
links each subscription to the plan with the same price.

It can run again: a vehicle is matched by its serial number (`sheet:<no>`) and
what is already loaded is left as it is.

The report names rows by serial number only. It never contains a name, phone
number or car number.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.customers.importer import _compact, _rows, _text, date_of, mobile_of, parking_of, split_name, time_of
from app.customers.models import (
    INTERIOR_DAY_CUSTOM,
    WEEKDAYS,
    Customer,
    Subscription,
    Vehicle,
)
from app.directory.models import Plan, Society, Zone
from app.directory.service import next_code

SHEET = "Monthly Customer"
SOURCE = "migration"

# The plans the sheet's prices stand for. All include interior care.
PLANS = (
    ("Basic 5d", 699, 1),
    ("Premium", 999, 2),
    ("Luxe", 1299, 3),
    ("Special 1K", 1000, 4),
)
RENAMED_PLAN = ("Premium Care", "Premium")


@dataclass
class SheetReport:
    applied: bool = False
    society: str = ""
    plans_created: int = 0
    plans_renamed: int = 0
    zones_created: int = 0
    customers_created: int = 0
    customers_kept: int = 0
    vehicles_created: int = 0
    vehicles_kept: int = 0
    subscriptions_created: int = 0
    # Loaded, but something needs the admin's attention.
    warnings: list[str] = field(default_factory=list)
    # Not loaded.
    errors: list[str] = field(default_factory=list)


def ensure_plans(db: Session, report: SheetReport) -> None:
    old, new = RENAMED_PLAN
    renamed = db.scalar(select(Plan).where(func.lower(Plan.name) == old.lower()))
    if renamed is not None and db.scalar(
            select(Plan.id).where(func.lower(Plan.name) == new.lower())) is None:
        renamed.name = new
        report.plans_renamed += 1
    for name, price, order in PLANS:
        plan = db.scalar(select(Plan).where(func.lower(Plan.name) == name.lower()))
        if plan is None:
            db.add(Plan(code=next_code(db, Plan, "PLN"), name=name,
                        monthly_price_rupees=price, includes_interior=True,
                        sort_order=order, inclusions=[], badge=""))
            db.flush()
            report.plans_created += 1
        elif plan.sort_order != order and name == new:
            plan.sort_order = order
    db.flush()


class _Load:
    def __init__(self, db: Session, society: Society, report: SheetReport):
        self.db, self.society, self.report = db, society, report
        self.customers: dict[tuple[str, str], Customer] = {}
        self.zones: dict[str, Zone] = {}
        self.plan_by_price: dict[int, Plan] = {}
        for plan in db.scalars(select(Plan).where(Plan.active.is_(True))
                               .order_by(Plan.sort_order, Plan.code)):
            self.plan_by_price.setdefault(plan.monthly_price_rupees, plan)

    def warn(self, ref: str, message: str) -> None:
        self.report.warnings.append(f"row {ref}: {message}")

    def error(self, ref: str, message: str) -> None:
        self.report.errors.append(f"row {ref}: {message}")

    def zone(self, text: str) -> Zone | None:
        name = " ".join(text.split())
        if not name:
            return None
        key = name.lower()
        if key not in self.zones:
            zone = self.db.scalar(select(Zone).where(
                Zone.society_id == self.society.id, func.lower(Zone.name) == key))
            if zone is None:
                zone = Zone(society_id=self.society.id, name=name)
                self.db.add(zone)
                self.db.flush()
                self.report.zones_created += 1
            self.zones[key] = zone
        return self.zones[key]

    def customer(self, row: dict, ref: str, name: str, mobile: str) -> Customer:
        key = (name.lower(), mobile)
        alternate = " ".join(_text(row.get("alternate customer names")).split())
        flat = _text(row.get("flat no."))
        customer = self.customers.get(key)
        if customer is None:
            first, last = split_name(name)
            customer = self.db.scalar(select(Customer).where(
                Customer.source == SOURCE, Customer.email.is_(None),
                Customer.mobile == mobile, Customer.society_id == self.society.id,
                func.lower(Customer.first_name) == first.lower(),
                func.lower(Customer.last_name) == last.lower()))
            if customer is None:
                if not last:
                    self.warn(ref, "the name is one word, so the last name is empty")
                customer = Customer(
                    login_id=None, email=None, first_name=first, last_name=last,
                    mobile=mobile, society_id=self.society.id, flat=flat,
                    alternate_names=alternate or None, source=SOURCE)
                self.db.add(customer)
                self.db.flush()
                self.report.customers_created += 1
            else:
                self.report.customers_kept += 1
            self.customers[key] = customer
        elif flat and customer.flat and flat != customer.flat:
            self.warn(ref, "the flat differs from the customer's other rows, the first is kept")
        if alternate and alternate.lower() not in (customer.alternate_names or "").lower():
            customer.alternate_names = ", ".join(
                p for p in (customer.alternate_names, alternate) if p)
        if flat and not customer.flat:
            customer.flat = flat
        return customer

    def row(self, row: dict) -> None:
        ref = _text(row.get("sl. no.")) or "?"
        source_ref = f"sheet:{ref}"
        name = " ".join(_text(row.get("customer name")).split())
        mobile = mobile_of(row.get("phone number"))
        if not name or mobile is None:
            return self.error(ref, "the name or the 10-digit phone number is missing")

        existing = self.db.scalar(select(Vehicle).where(Vehicle.source_ref == source_ref))
        if existing is not None:
            self.report.vehicles_kept += 1
            return None
        customer = self.customer(row, ref, name, mobile)

        notes = []
        # Stored as given: no spaces, upper case, no format check.
        registration = _compact(row.get("car number")) or None
        if registration is None:
            self.warn(ref, "no car number")
        elif len(registration) > 20:
            self.warn(ref, "the car number is longer than 20 characters, kept as a note")
            notes.append(f"Car number as given: {_text(row.get('car number'))}")
            registration = None
        elif self.db.scalar(select(Vehicle.id).where(Vehicle.registration == registration)):
            self.warn(ref, "the car number is already on another vehicle, kept as a note")
            notes.append(f"Car number as given: {_text(row.get('car number'))}")
            registration = None

        parking_text = " ".join(_text(row.get("parking number")).split())
        basement, number, understood = parking_of(parking_text)
        if not parking_text:
            self.warn(ref, "no parking number")
        elif not understood:
            # Free text such as "Under D25" is kept whole.
            basement, number = "", parking_text
            if len(number) > 60:
                notes.append(f"Parking as given: {parking_text}")
                number = ""
                self.warn(ref, "the parking text is longer than 60 characters, kept as a note")

        model = _text(row.get("model"))
        if not model:
            self.warn(ref, "no model")
        zone = self.zone(_text(row.get("basement1/2/3")))
        vehicle = Vehicle(
            customer_id=customer.id, society_id=self.society.id, registration=registration,
            make=_text(row.get("make")), model=model, variant=_text(row.get("variant")),
            parking_basement=basement, parking_number=number,
            zone_id=zone.id if zone else None, notes="\n".join(notes), source_ref=source_ref)
        self.db.add(vehicle)
        self.db.flush()
        self.report.vehicles_created += 1
        self.subscription(row, ref, vehicle)
        return None

    def subscription(self, row: dict, ref: str, vehicle: Vehicle) -> None:
        start = date_of(row.get("start date"))
        price = row.get("package")
        if start is None or not isinstance(price, int | float):
            missing = " and ".join(n for n, v in (
                ("start date", start), ("package", price if isinstance(price, int | float) else None))
                if v is None)
            self.warn(ref, f"no {missing}, so the vehicle is loaded without a subscription "
                           "(inactive until the plan details are supplied)")
            return
        plan = self.plan_by_price.get(int(price))
        if plan is None:
            self.warn(ref, "no plan has this price, so the plan is left empty")

        cutoff = time_of(row.get("time before (customer wish)"))
        if cutoff is None:
            self.warn(ref, "no cutoff time")
        day_text = " ".join(_text(row.get("interior day")).split())
        day = day_text.capitalize() or None
        day_notes = _text(row.get("interior day notes")) or None
        if day is not None and day not in WEEKDAYS:
            if day_text.lower().startswith("alternate"):
                # The customer's cars take turns: the logic comes later.
                day, day_notes = INTERIOR_DAY_CUSTOM, day_notes or day_text
            else:
                self.warn(ref, "the interior day is not a weekday, left empty")
                day = None
        self.db.add(Subscription(
            vehicle_id=vehicle.id, plan_id=plan.id if plan else None,
            monthly_price_rupees=int(price), status="Active", first_service_date=start,
            cutoff_time=cutoff, interior_day=day, interior_day_notes=day_notes))
        self.report.subscriptions_created += 1


def _society(db: Session, name: str | None) -> Society:
    if name:
        found = db.scalar(select(Society).where(func.lower(Society.name) == name.lower()))
        if found is None:
            raise ValueError("There is no society with that name.")
        return found
    societies = list(db.scalars(select(Society)))
    if len(societies) != 1:
        raise ValueError(
            f"There are {len(societies)} societies. Name the one to load into.")
    return societies[0]


def load_monthly_customers(db: Session, path: Path | str, *, society_name: str | None = None,
                           apply: bool) -> SheetReport:
    """Loads the sheet. With apply=False nothing is saved: it is a trial run
    that reports what would happen."""
    report = SheetReport(applied=apply)
    workbook = load_workbook(path, data_only=True)
    if SHEET not in workbook.sheetnames:
        report.errors.append(f'There is no sheet named "{SHEET}".')
        return report
    try:
        society = _society(db, society_name)
        report.society = re.sub(r"\s+", " ", society.name)
        ensure_plans(db, report)
        run = _Load(db, society, report)
        for row in _rows(workbook[SHEET]):
            run.row(row)
        if apply:
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise
    return report
