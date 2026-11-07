"""Customer onboarding and administration shared by the portal and Add vehicle."""

import re
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session

from app.billing.config import get_money_settings
from app.billing.models import Payment, PaymentEvent
from app.billing.service import BillingService
from app.billing.status import display_status
from app.changes.cycle import renewal_date
from app.customers import plan_changes
from app.customers.logins import ensure_login, give_default_mpin, mobile_in_use, mobile_taken
from app.customers.models import (
    INTERIOR_DAY_CUSTOM,
    INTERIOR_DAYS,
    AddonRequest,
    Customer,
    EmailChange,
    Subscription,
    Vehicle,
)
from app.customers.parking_rules import basement_ok, clean_number
from app.customers.service import _NAME, read_cutoff, show_registration
from app.customers.welcome import send_welcome
from app.directory.models import DirectoryAudit, Plan, Society, VehicleCatalogueEntry, Zone
from app.identity.models import AuthSession, EmailCode, Login
from app.identity.service import User, normalise
from app.media import service as media
from app.media.models import STATUS_CONFIRMED, MediaUpload
from app.media.store import ObjectStore, get_object_store
from app.notifications.push import get_default_sender
from app.notifications.router import NotificationPreferencesIn
from app.notifications.service import NotificationService
from app.platform.clock import today_ist
from app.platform.db import get_db, utcnow
from app.platform.deps import require_feature, require_role
from app.platform.errors import ApiError
from app.scheduling.models import Job, SchedulingCrew, Visit

admin = APIRouter(prefix="/v1/admin", tags=["customer-administration"])
customer = APIRouter(prefix="/v1/customer", tags=["customer-administration"])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _drop_retired_fields(cls, data):
        # Old clients still send the first payment status. It is no longer chosen:
        # the status always comes from the cycle dates (PAY-14). Ignored, not stored.
        if isinstance(data, dict) and "first_payment_status" in data:
            data = {k: v for k, v in data.items() if k != "first_payment_status"}
        return data


class VehicleCreate(Input):
    society_id: uuid.UUID
    catalogue_id: uuid.UUID
    registration: str
    parking_basement: str
    parking_number: str
    # The zone of the society (site setup). Optional.
    zone_id: uuid.UUID | None = None
    plan_id: uuid.UUID | None = None
    cutoff_time: str | None = None
    interior_day: str | None = None
    # With "Custom": whose car's turn it is.
    interior_day_notes: str | None = None
    # The admin may add a vehicle without a photo; the customer route still needs one.
    photo_upload_id: uuid.UUID | None = None
    rc_upload_id: uuid.UUID | None = None


class CustomerCreate(Input):
    first_name: str
    last_name: str = ""
    # Optional: a contact, not a login. The customer signs in with the mobile
    # number and the MPIN, which starts as its last 6 digits.
    email: str | None = None
    mobile: str
    flat: str = Field(default="", max_length=40)
    vehicle: VehicleCreate


class CustomerEdit(Input):
    first_name: str
    last_name: str = ""
    mobile: str
    flat: str = Field(default="", max_length=40)
    address_line1: str = Field(default="", max_length=120)
    address_line2: str = Field(default="", max_length=120)
    society_id: uuid.UUID | None = None
    # Other names the customer is known by. Empty clears; not sent leaves it as it is.
    alternate_names: str | None = Field(default=None, max_length=500)


class SubscriptionSetup(Input):
    plan_id: uuid.UUID
    cutoff_time: str
    interior_day: str | None = None
    interior_day_notes: str | None = None
    # Empty: today.
    first_service_date: date | None = None


class EmailCorrection(Input):
    email: str


class VehicleEdit(Input):
    registration: str | None = None
    catalogue_id: uuid.UUID | None = None
    parking_basement: str | None = None
    parking_number: str | None = None
    zone_id: uuid.UUID | None = None
    # Send true to remove the zone.
    clear_zone: bool = False
    photo_upload_id: uuid.UUID | None = None
    rc_upload_id: uuid.UUID | None = None
    rc_verified: bool | None = None
    active: bool | None = None


class SubscriptionEdit(Input):
    plan_id: uuid.UUID | None = None
    # With a plan: the day the new plan starts. Empty: the next renewal date.
    effective_from: date | None = None
    # With a date before the renewal: what to charge for the days in between.
    charge: Literal["none", "prorated", "custom"] = "none"
    charge_rupees: int | None = None
    cutoff_time: str | None = None
    interior_day: str | None = None
    interior_day_notes: str | None = None


class UploadIn(Input):
    purpose: str
    content_type: str
    size_bytes: int


class SessionDevice(Input):
    device_name: str = Field(max_length=120)
    platform: str = Field(max_length=20)
    app_version: str = Field(max_length=40)


def audit(db, by, entity, target, action, detail):
    db.add(
        DirectoryAudit(
            admin_login_id=by, entity=entity, entity_id=str(target), action=action, detail=detail
        )
    )


def get_customer(db, customer_id):
    c = db.get(Customer, customer_id)
    if c is None:
        raise ApiError("not_found", "Customer not found.", 404)
    return c


def valid_person(first, last, mobile):
    first, last, mobile = " ".join(first.split()), " ".join(last.split()), mobile.strip()
    errors = {}
    if not _NAME.fullmatch(first):
        errors["first_name"] = "Enter a first name using letters."
    if last and not _NAME.fullmatch(last):
        errors["last_name"] = "Enter a last name using letters."
    if not re.fullmatch(r"\d{10}", mobile):
        errors["mobile"] = "Enter a 10-digit mobile number."
    if errors:
        raise ApiError("validation_failed", "Check the customer details.", 422, errors)
    return first, last, mobile


def valid_email(email):
    value = normalise(email)
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) or len(value) > 254:
        raise ApiError("validation_failed", "Enter a valid email.", 422, {"email": "Invalid."})
    return value


def registration(db, raw, vehicle_id=None):
    value = re.sub(r"\s", "", raw).upper()
    if not re.fullmatch(r"(?:[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{4}|\d{2}BH\d{4}[A-Z]{1,2})", value):
        raise ApiError(
            "validation_failed",
            "Enter a registration such as HR26EC4321.",
            422,
            {"registration": "Invalid registration."},
        )
    found = db.scalar(select(Vehicle.id).where(Vehicle.registration == value))
    if found is not None and found != vehicle_id:
        raise ApiError("registration_in_use", "This vehicle is already registered.", 409)
    return value


def asset(db, raw, owner, purpose, vehicle_id=None):
    row = db.get(MediaUpload, raw)
    claimed = db.scalar(
        select(Vehicle.id).where(or_(Vehicle.photo_upload_id == raw, Vehicle.rc_upload_id == raw))
    )
    if (
        row is None
        or row.status != STATUS_CONFIRMED
        or row.purpose != purpose
        or row.owner_login_id != owner
        or (claimed is not None and claimed != vehicle_id)
    ):
        raise ApiError(
            "validation_failed",
            "Upload and confirm your own file first.",
            422,
            {f"{purpose}_upload_id": "Confirmed file required."},
        )
    return row.id


def zone_for(db, zone_id, society_id):
    """The zone to set on a vehicle: an active zone of the vehicle's society."""
    zone = db.get(Zone, zone_id)
    if zone is None or not zone.active or zone.society_id != society_id:
        raise ApiError("validation_failed", "Choose an active zone of this society.", 422,
                       {"zone_id": "Invalid."})
    return zone


def start_subscription(db, c, v, plan, *, cutoff, interior_day, interior_day_notes,
                       by, first_service_date=None):
    """A new subscription (Activating) for a vehicle, with its first plan payment."""
    first = first_service_date or today_ist()
    sub = Subscription(
        vehicle_id=v.id,
        plan_id=plan.id,
        monthly_price_rupees=plan.monthly_price_rupees,
        status="Activating",
        first_service_date=first,
        cutoff_time=cutoff,
        interior_day=interior_day if plan.includes_interior else None,
        interior_day_notes=(interior_day_notes or "").strip() or None
        if plan.includes_interior and interior_day == INTERIOR_DAY_CUSTOM else None,
    )
    db.add(sub)
    db.flush()
    # The status is never chosen: the payment is stored Open and its displayed
    # status comes from the cycle dates and today (PAY-14). The cycle starts on
    # the first service date, so a future start shows Not Due.
    payment = BillingService(db, utcnow, get_money_settings()).ensure_cycle_payment(sub, v, first)
    payment.description = f"First month of {plan.name}"
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            from_status=None,
            to_status=display_status(payment, today_ist()).status,
            by_login_id=by,
            note="First payment at onboarding",
        )
    )
    return sub, payment


def add_vehicle(db, c, body, owner, by=None):
    society = db.get(Society, body.society_id)
    entry = db.get(VehicleCatalogueEntry, body.catalogue_id)
    plan = db.get(Plan, body.plan_id) if body.plan_id else None
    if (
        society is None
        or not society.active
        or entry is None
        or not entry.active
        or (body.plan_id is not None and (plan is None or not plan.active))
    ):
        raise ApiError("validation_failed", "Choose an active society, vehicle and plan.", 422)
    cutoff = read_cutoff(body.cutoff_time)
    basement, number = body.parking_basement.strip().upper(), clean_number(body.parking_number)
    # The interior care day is optional at onboarding; a car without one is on Needs Attention.
    if plan and (cutoff is None or (body.interior_day is not None and body.interior_day not in INTERIOR_DAYS)):
        raise ApiError("validation_failed", "Choose a cutoff, and an interior care day from the list.", 422)
    if number is None or not basement_ok(db, society.id, basement,
                                         has_zone=body.zone_id is not None):
        raise ApiError("validation_failed", "Check the parking location.", 422)
    reg = registration(db, body.registration)
    photo = asset(db, body.photo_upload_id, owner, "vehicle") if body.photo_upload_id else None
    rc = asset(db, body.rc_upload_id, owner, "rc") if body.rc_upload_id else None
    v = Vehicle(
        customer_id=c.id,
        society_id=society.id,
        registration=reg,
        make=entry.make,
        model=entry.model,
        variant=entry.variant,
        category=entry.category,
        parking_basement=basement,
        parking_number=number,
        zone_id=zone_for(db, body.zone_id, society.id).id if body.zone_id else None,
        photo_upload_id=photo,
        rc_upload_id=rc,
    )
    db.add(v)
    db.flush()
    if plan is None:
        if by:
            audit(db, by, "vehicle", v.id, "create", {"customer_id": str(c.id),
                                                       "registration": reg, "subscription": False})
        return v, None, None
    sub, payment = start_subscription(
        db, c, v, plan, cutoff=cutoff, interior_day=body.interior_day,
        interior_day_notes=body.interior_day_notes,
        by=by)
    if by:
        audit(db, by, "vehicle", v.id, "create", {"customer_id": str(c.id), "registration": reg})
    return v, sub, payment


def vehicle_out(db, v, store):
    c = db.get(Customer, v.customer_id)
    society = db.get(Society, v.society_id or c.society_id)
    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == v.id))
    plan = db.get(Plan, sub.plan_id) if sub and sub.plan_id else None
    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.vehicle_id == v.id, Payment.voided_at.is_(None))
            .order_by(Payment.created_at.desc())
        )
    )
    photo = media.vehicle_photo_urls(db, store, [v.id]).get(v.id)
    return {
        "id": str(v.id),
        "active": v.active,
        "society_id": str(society.id),
        "society": society.name,
        "registration": show_registration(v.registration),
        "make": v.make,
        "model": v.model,
        "variant": v.variant,
        "category": v.category,
        "parking_basement": v.parking_basement,
        "parking_number": v.parking_number,
        "zone_id": str(v.zone_id) if v.zone_id else None,
        "zone": db.get(Zone, v.zone_id).name if v.zone_id else None,
        "photo_url": photo,
        "rc_verified": v.rc_verified,
        "rc_url": media.upload_urls(db, store, [str(v.rc_upload_id)])[0]
        if v.rc_upload_id
        else None,
        "subscription": {
            "id": str(sub.id),
            "status": sub.status,
            "plan_id": str(sub.plan_id),
            "plan_name": plan.name if plan else "",
            "price_rupees": sub.monthly_price_rupees,
            "cutoff_time": sub.cutoff_time.strftime("%H:%M") if sub.cutoff_time else "",
            "interior_day": sub.interior_day,
            "interior_day_notes": sub.interior_day_notes,
            "first_service_date": sub.first_service_date,
            "pending_plan_id": str(sub.pending_plan_id) if sub.pending_plan_id else None,
            "pending_from": sub.pending_from,
        }
        if sub
        else None,
        "payments": [
            {
                "id": str(p.id),
                "status": display_status(p, today_ist()).status,
                "amount_rupees": p.amount_rupees,
                "due_date": p.due_date,
            }
            for p in payments
        ],
    }


def detail(db, c, store):
    from app.customers.history import imported_history
    login = db.get(Login, c.login_id) if c.login_id else None
    return {
        "id": str(c.id),
        "first_name": c.first_name,
        "last_name": c.last_name,
        "email": c.email,
        "mobile": c.mobile,
        "flat": c.flat,
        "alternate_names": c.alternate_names,
        "address_line1": c.address_line1,
        "address_line2": c.address_line2,
        "society_id": str(c.society_id),
        "email_verified": c.email_verified_at is not None,
        "mpin_changed": login is not None and not login.must_change_mpin,
        "has_login": login is not None,
        "onboarding_confirmed": c.onboarding_confirmed_at is not None,
        "imported_history": imported_history(db, c.id),
        "vehicles": [
            vehicle_out(db, v, store)
            for v in db.scalars(
                select(Vehicle)
                .where(Vehicle.customer_id == c.id)
                .order_by(Vehicle.active.desc(), Vehicle.created_at)
            )
        ],
    }


# What a customer's subscriptions add up to: the best one wins (Active, then
# Activating, then Inactive). A customer with none has "No subscription".
CUSTOMER_STATUSES = ("Active", "Activating", "Inactive", "No subscription")
_RANK = {"Active": 3, "Activating": 2, "Inactive": 1}
_RANK_NAME = {v: k for k, v in _RANK.items()}


def _status_rank():
    """One row per customer that has a subscription on an active vehicle."""
    rank = case(
        *[(Subscription.status == name, n) for name, n in _RANK.items()], else_=0
    )
    return (
        select(Vehicle.customer_id.label("customer_id"), func.max(rank).label("rank"))
        .join(Subscription, Subscription.vehicle_id == Vehicle.id)
        .where(Vehicle.active.is_(True))
        .group_by(Vehicle.customer_id)
        .subquery()
    )


def _matching(q: str, society_id: uuid.UUID | None):
    """The customers that match a search and a society, as a query of IDs."""
    query = (
        select(Customer.id)
        .outerjoin(Vehicle, Vehicle.customer_id == Customer.id)
        .outerjoin(Zone, Zone.id == Vehicle.zone_id)
        .outerjoin(Society, Society.id == func.coalesce(Vehicle.society_id, Customer.society_id))
    )
    if q:
        text = f"%{q.strip()}%"
        query = query.where(
            or_(
                func.trim(Customer.first_name + " " + Customer.last_name).ilike(text),
                Customer.last_name.ilike(text),
                Customer.email.ilike(text),
                Customer.mobile.ilike(text),
                Vehicle.registration.ilike(text.replace(" ", "")),
                Society.name.ilike(text),
                Customer.alternate_names.ilike(text),
                Vehicle.parking_number.ilike(text),
                Zone.name.ilike(text),
            )
        )
    if society_id:
        query = query.where(Society.id == society_id)
    return query.distinct()


@admin.get("/customers/summary")
def customers_summary(
    q: str = "",
    society_id: uuid.UUID | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """The numbers above the customer list, for the same search and society."""
    ranks = _status_rank()
    addons = select(AddonRequest.customer_id.label("customer_id")).distinct().subquery()
    has_addon = addons.c.customer_id.is_not(None)
    ids = _matching(q, society_id).subquery()
    rows = db.execute(
        select(ranks.c.rank, has_addon, func.count())
        .select_from(Customer)
        .join(ids, ids.c.id == Customer.id)
        .outerjoin(ranks, ranks.c.customer_id == Customer.id)
        .outerjoin(addons, addons.c.customer_id == Customer.id)
        .group_by(ranks.c.rank, has_addon)
    ).all()
    by_status = dict.fromkeys(CUSTOMER_STATUSES, 0)
    addons_only = 0
    for rank, addon, n in rows:
        by_status[_RANK_NAME.get(rank, "No subscription")] += n
        if not rank and addon:
            addons_only += n
    total = sum(by_status.values())
    return {
        "total": total,
        "with_subscription": total - by_status["No subscription"],
        "addons_only": addons_only,
        "by_status": by_status,
    }


@admin.get("/customers")
def list_customers(
    q: str = "",
    society_id: uuid.UUID | None = None,
    status: str | None = Query(
        default=None, description="Active, Activating, Inactive or No subscription"
    ),
    scope: str | None = Query(
        default=None, description="with_subscription or addons_only"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if status is not None and status not in CUSTOMER_STATUSES:
        raise ApiError("validation_failed", "Choose a status from the list.", 422)
    if scope is not None and scope not in ("with_subscription", "addons_only"):
        raise ApiError("validation_failed", "Choose with_subscription or addons_only.", 422)
    ranks = _status_rank()
    ids_query = _matching(q, society_id).subquery()
    query = (
        select(Customer)
        .join(ids_query, ids_query.c.id == Customer.id)
        .outerjoin(ranks, ranks.c.customer_id == Customer.id)
    )
    if scope == "with_subscription":
        query = query.where(ranks.c.rank.is_not(None))
    elif scope == "addons_only":
        addons = select(AddonRequest.customer_id).distinct().scalar_subquery()
        query = query.where(ranks.c.rank.is_(None), Customer.id.in_(addons))
    if status == "No subscription":
        query = query.where(ranks.c.rank.is_(None))
    elif status:
        query = query.where(ranks.c.rank == _RANK[status])
    found = list(db.scalars(query.order_by(
        Customer.first_name, Customer.last_name, Customer.id).limit(limit).offset(offset)))
    # Each row also carries its vehicles and onboarding state, so the portal list
    # shows them without opening every customer (one query each, not per row).
    ids = [c.id for c in found]
    vehicles: dict[uuid.UUID, list[dict]] = {i: [] for i in ids}
    for v, status in db.execute(
        select(Vehicle, Subscription.status)
        .outerjoin(Subscription, Subscription.vehicle_id == Vehicle.id)
        .where(Vehicle.customer_id.in_(ids), Vehicle.active.is_(True))
        .order_by(Vehicle.created_at)
    ) if ids else []:
        vehicles[v.customer_id].append(
            {"id": str(v.id), "registration": show_registration(v.registration), "status": status}
        )
    mpin_changed = dict(db.execute(
        select(Login.id, Login.must_change_mpin.is_(False))
        .where(Login.id.in_([c.login_id for c in found if c.login_id]))
    ).all()) if ids else {}
    return [
        {
            "id": str(c.id),
            "name": f"{c.first_name} {c.last_name}".strip(),
            "email": c.email,
            "mobile": c.mobile,
            "flat": c.flat,
            "email_verified": c.email_verified_at is not None,
            "mpin_changed": bool(mpin_changed.get(c.login_id)),
            "onboarding_confirmed": c.onboarding_confirmed_at is not None,
            "vehicles": vehicles[c.id],
        }
        for c in found
    ]




@admin.get("/customers/{customer_id}")
def customer_detail(
    customer_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    return detail(db, get_customer(db, customer_id), store)


@admin.post("/customers", status_code=201)
def create_customer(
    body: CustomerCreate,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    first, last, mobile = valid_person(body.first_name, body.last_name, body.mobile)
    email = valid_email(body.email) if body.email and body.email.strip() else None
    if email is not None:
        existing = db.scalar(select(Customer).where(Customer.email == email))
        if existing:
            return {**detail(db, existing, store), "existing": True}
    if mobile_taken(db, mobile):
        raise mobile_in_use(mobile)
    c = Customer(
        first_name=first,
        last_name=last,
        email=email,
        mobile=mobile,
        society_id=body.vehicle.society_id,
        flat=body.flat,
    )
    db.add(c)
    db.flush()
    # The sign-in is the mobile number and the MPIN (the last 6 digits of the number).
    ensure_login(db, c)
    add_vehicle(db, c, body.vehicle, user.id, user.id)
    audit(db, user.id, "customer", c.id, "create", {"email": email})
    db.commit()
    return {**detail(db, c, store), "welcome_sent": send_welcome(db, c)}


@admin.patch("/customers/{customer_id}")
def edit_customer(
    customer_id: uuid.UUID,
    body: CustomerEdit,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    c = get_customer(db, customer_id)
    first, last, mobile = valid_person(body.first_name, body.last_name, body.mobile)
    if mobile != c.mobile:
        if mobile_taken(db, mobile, except_id=c.id):
            raise mobile_in_use(mobile)
        change_mobile(db, c, mobile)
    c.first_name, c.last_name = first, last
    c.flat = body.flat
    c.address_line1 = body.address_line1.strip()
    c.address_line2 = body.address_line2.strip()
    if body.alternate_names is not None:
        c.alternate_names = " ".join(body.alternate_names.split()) or None
    if body.society_id is not None and body.society_id != c.society_id:
        society = db.get(Society, body.society_id)
        if society is None or not society.active:
            raise ApiError("validation_failed", "Choose an active society.", 422)
        c.society_id = society.id
    if c.login_id:
        db.get(Login, c.login_id).display_name = f"{c.first_name} {c.last_name}".strip()
    # Alternate names are not written to the audit log (owner, 3 Nov 2026).
    audit(db, user.id, "customer", c.id, "update",
          body.model_dump(mode="json", exclude={"alternate_names"}))
    db.commit()
    return detail(db, c, store)


@admin.post("/customers/{customer_id}/vehicles", status_code=201)
def admin_add_vehicle(
    customer_id: uuid.UUID,
    body: VehicleCreate,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    v, _, payment = add_vehicle(db, get_customer(db, customer_id), body, user.id, user.id)
    db.commit()
    return {**vehicle_out(db, v, store), "payment_id": str(payment.id) if payment else None}


@admin.post("/vehicles/{vehicle_id}/subscription", status_code=201)
def set_up_subscription(
    vehicle_id: uuid.UUID,
    body: SubscriptionSetup,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    """Starts the subscription of a vehicle that has none, for example one loaded
    from a sheet without plan details. It starts Activating, like a new vehicle's."""
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise ApiError("not_found", "Vehicle not found.", 404)
    if not v.active:
        raise ApiError("validation_failed", "This vehicle is not active.", 422)
    if db.scalar(select(Subscription.id).where(Subscription.vehicle_id == v.id)) is not None:
        raise ApiError("subscription_exists", "This vehicle already has a subscription.", 409)
    plan = db.get(Plan, body.plan_id)
    if plan is None or not plan.active:
        raise ApiError("validation_failed", "Choose an active plan.", 422,
                       {"plan_id": "Invalid."})
    cutoff = read_cutoff(body.cutoff_time)
    if cutoff is None:
        raise ApiError("validation_failed", "Choose a cutoff in 30-minute steps.", 422,
                       {"cutoff_time": "Invalid."})
    # The interior care day is optional at onboarding; a car without one is on Needs Attention.
    if body.interior_day is not None and body.interior_day not in INTERIOR_DAYS:
        raise ApiError("validation_failed", "Choose an interior care day from the list.", 422,
                       {"interior_day": "Invalid."})
    c = db.get(Customer, v.customer_id)
    sub, payment = start_subscription(
        db, c, v, plan, cutoff=cutoff, interior_day=body.interior_day,
        interior_day_notes=body.interior_day_notes,
        by=user.id,
        first_service_date=body.first_service_date)
    audit(db, user.id, "subscription", sub.id, "create",
          {"vehicle_id": str(v.id), "plan_id": str(plan.id)})
    db.commit()
    return {**vehicle_out(db, v, store), "payment_id": str(payment.id)}


@customer.post("/vehicles", status_code=201,
               dependencies=[Depends(require_feature("customer.add_vehicle"))])
def customer_add_vehicle(
    body: VehicleCreate,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    c = db.scalar(select(Customer).where(Customer.login_id == user.id))
    if c is None:
        raise ApiError("not_found", "Customer not found.", 404)
    if body.plan_id is None:
        raise ApiError(
            "validation_failed", "Choose a plan; standalone vehicles are created by admin.", 422
        )
    if body.photo_upload_id is None:
        raise ApiError("validation_failed", "Add a photo of the vehicle.", 422,
                       {"photo_upload_id": "A photo is required."})
    v, _, payment = add_vehicle(db, c, body, user.id)
    db.commit()
    return {**vehicle_out(db, v, store), "payment_id": str(payment.id)}


@customer.get("/onboarding-summary")
def onboarding_summary(
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    c = db.scalar(select(Customer).where(Customer.login_id == user.id))
    if c is None:
        raise ApiError("not_found", "Customer not found.", 404)
    rows = []
    for v in db.scalars(
        select(Vehicle).where(Vehicle.customer_id == c.id, Vehicle.active.is_(True))
    ):
        sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == v.id))
        plan = db.get(Plan, sub.plan_id) if sub and sub.plan_id else None
        rows.append(
            {
                **vehicle_out(db, v, store),
                "plan": {
                    "list_price_rupees": plan.list_price_rupees,
                    "inclusions": plan.inclusions,
                    "badge": plan.badge,
                }
                if plan
                else None,
            }
        )
    return {"vehicles": rows}


@customer.put("/session-device", status_code=204)
def session_device(
    body: SessionDevice,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
):
    session = db.get(AuthSession, user.session_id)
    session.device_name, session.platform, session.app_version = (
        body.device_name,
        body.platform,
        body.app_version,
    )
    db.commit()


def change_mobile(db, c, mobile):
    """The mobile number is the sign-in ID, so a new one signs the customer out
    everywhere. While the customer still has the MPIN the admin gave, that MPIN
    follows the new number."""
    c.mobile = mobile
    if c.login_id is None:
        return
    login = db.get(Login, c.login_id)
    login.login_id = mobile
    if login.must_change_mpin:
        give_default_mpin(login, mobile)
    db.execute(
        update(AuthSession)
        .where(AuthSession.login_id == c.login_id, AuthSession.ended_at.is_(None))
        .values(ended_at=utcnow(), ended_reason="mobile_changed")
    )


def reset_mpin(db, c, by, reason):
    """Back to the first MPIN (the last 6 digits of the mobile number): the
    customer is signed out everywhere and must choose a new MPIN at the next
    sign-in. A customer without a sign-in gets one."""
    login = ensure_login(db, c)
    give_default_mpin(login, c.mobile)
    db.execute(
        update(AuthSession)
        .where(AuthSession.login_id == c.login_id, AuthSession.ended_at.is_(None))
        .values(ended_at=utcnow(), ended_reason=reason)
    )
    db.execute(
        update(EmailCode)
        .where(EmailCode.login_id == c.login_id, EmailCode.ended_at.is_(None))
        .values(ended_at=utcnow(), ended_reason=reason)
    )
    audit(db, by, "customer", c.id, reason, {})


@admin.patch("/customers/{customer_id}/email")
def correct_email(
    customer_id: uuid.UUID,
    body: EmailCorrection,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    c = get_customer(db, customer_id)
    email = valid_email(body.email)
    if email == c.email:
        return {"welcome_sent": False}
    if db.scalar(select(Customer.id).where(Customer.email == email, Customer.id != c.id)):
        raise ApiError("email_in_use", "This email is already in use.", 409)
    old = c.email
    # The email is a contact, not the sign-in, so the customer stays signed in.
    c.email = email
    c.email_verified_at = None
    db.execute(
        update(EmailChange)
        .where(EmailChange.customer_id == c.id, EmailChange.ended_at.is_(None))
        .values(ended_at=utcnow())
    )
    audit(db, user.id, "customer", c.id, "email", {"email": [old, email]})
    db.commit()
    return {"welcome_sent": send_welcome(db, c)}


@admin.post("/customers/{customer_id}/reset-mpin")
def reset_mpin_route(
    customer_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Gives the customer the first MPIN again (the last 6 digits of the mobile
    number). They must choose a new one at the next sign-in."""
    reset_mpin(db, get_customer(db, customer_id), user.id, "mpin_reset")
    db.commit()
    return {"reset": True}


@admin.get("/customers/{customer_id}/sessions")
def sessions(
    customer_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    c = get_customer(db, customer_id)
    return [
        {
            "id": str(s.id),
            "device_name": s.device_name,
            "platform": s.platform,
            "app_version": s.app_version,
            "channel": s.channel,
            "last_active": s.last_used_at,
        }
        for s in db.scalars(
            select(AuthSession)
            .where(AuthSession.login_id == c.login_id, AuthSession.ended_at.is_(None))
            .order_by(AuthSession.last_used_at.desc())
        )
    ]


@admin.post("/customers/{customer_id}/sessions/{session_id}/logout")
def end_session(
    customer_id: uuid.UUID,
    session_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    c = get_customer(db, customer_id)
    s = db.get(AuthSession, session_id)
    if s is None or s.login_id != c.login_id:
        raise ApiError("not_found", "Session not found.", 404)
    s.ended_at, s.ended_reason = utcnow(), "admin_logout"
    audit(db, user.id, "customer", c.id, "session_logout", {"session_id": str(s.id)})
    db.commit()
    return {"ended": True}


@admin.patch("/subscriptions/{subscription_id}")
def edit_subscription(
    subscription_id: uuid.UUID,
    body: SubscriptionEdit,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise ApiError("not_found", "Subscription not found.", 404)
    watched = ("pending_plan_id", "pending_from", "cutoff_time", "interior_day",
               "interior_day_notes")
    before = {k: getattr(sub, k) for k in watched}
    if body.plan_id:
        plan = db.get(Plan, body.plan_id)
        if plan is None or not plan.active:
            raise ApiError("validation_failed", "Choose an active plan.", 422)
        if body.effective_from is not None:
            plan_changes.validate_start(body.effective_from)
        starts = body.effective_from or renewal_date(
            db, sub.vehicle_id, sub.first_service_date, today_ist())
        change = plan_changes.schedule(
            db, sub, plan, starts, body.effective_from is not None, user.id)
        if body.charge != "none" and body.effective_from is None:
            raise ApiError("validation_failed", "Choose a date to charge for the days before it.", 422)
        db.flush()
        plan_changes.charge(db, sub, plan, change, starts, body.charge, body.charge_rupees)
    elif body.effective_from is not None:
        raise ApiError("validation_failed", "Choose a plan for that date.", 422)
    if body.cutoff_time is not None:
        cutoff = read_cutoff(body.cutoff_time)
        if cutoff is None:
            raise ApiError("validation_failed", "Choose a cutoff in 30-minute steps.", 422)
        sub.cutoff_time = cutoff
    if body.interior_day is not None:
        chosen_plan = sub.pending_plan_id or sub.plan_id
        plan = db.get(Plan, chosen_plan) if chosen_plan else None
        if body.interior_day not in INTERIOR_DAYS or (plan and not plan.includes_interior):
            raise ApiError("validation_failed", "Choose an interior care day for this plan.", 422)
        sub.interior_day = body.interior_day
        if body.interior_day != INTERIOR_DAY_CUSTOM:
            sub.interior_day_notes = None
    if body.interior_day_notes is not None and sub.interior_day == INTERIOR_DAY_CUSTOM:
        sub.interior_day_notes = body.interior_day_notes.strip() or None
    # A-04: {field: [old, new]} of what changed.
    diff = {k: [str(before[k]) if before[k] is not None else None,
                str(getattr(sub, k)) if getattr(sub, k) is not None else None]
            for k in watched if getattr(sub, k) != before[k]}
    audit(db, user.id, "subscription", sub.id, "update", diff or body.model_dump(mode="json"))
    db.commit()
    from app.scheduling.service import reconcile_vehicle

    reconcile_vehicle(db, sub.vehicle_id)
    # ADM-CUS-14/15: admin plan and default preferences edits are silent.
    # Explicit skip/operations actions keep their separate notification rules.
    return {"updated": True, "pending_from": sub.pending_from}


@admin.get("/vehicles/{vehicle_id}/crew")
def vehicle_crew(
    vehicle_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """ADM-CUS-28: the crew who serve a vehicle, read from its scheduled jobs from
    today (IST) on. Read only. Skipped jobs and unassigned jobs do not count."""
    if db.get(Vehicle, vehicle_id) is None:
        raise ApiError("not_found", "Vehicle not found.", 404)
    rows = db.execute(
        select(SchedulingCrew, Login.display_name, Job.service, Visit.date)
        .join(Job, Job.crew_id == SchedulingCrew.id)
        .join(Visit, Visit.id == Job.visit_id)
        .join(Login, Login.id == SchedulingCrew.login_id)
        .where(Visit.vehicle_id == vehicle_id, Visit.date >= today_ist(),
               Job.status != "Skipped")
        .order_by(Visit.date, Job.start_minute)
    ).all()
    crew: dict[uuid.UUID, dict] = {}
    for member, name, service, day in rows:
        entry = crew.setdefault(member.id, {
            "id": str(member.id), "name": name, "role": member.role,
            "services": [], "next_date": day.isoformat(), "jobs": 0,
        })
        entry["jobs"] += 1
        if service not in entry["services"]:
            entry["services"].append(service)
    return sorted(crew.values(), key=lambda c: (c["next_date"], c["name"]))


@admin.patch("/vehicles/{vehicle_id}")
def edit_vehicle(
    vehicle_id: uuid.UUID,
    body: VehicleEdit,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise ApiError("not_found", "Vehicle not found.", 404)
    if body.registration is not None:
        v.registration = registration(db, body.registration, v.id)
    if body.catalogue_id:
        entry = db.get(VehicleCatalogueEntry, body.catalogue_id)
        if entry is None or not entry.active:
            raise ApiError("validation_failed", "Choose an active vehicle.", 422)
        v.make, v.model, v.variant, v.category = (
            entry.make,
            entry.model,
            entry.variant,
            entry.category,
        )
    c = db.get(Customer, v.customer_id)
    old_zone = v.zone_id
    if body.zone_id is not None:
        v.zone_id = zone_for(db, body.zone_id, v.society_id or c.society_id).id
    elif body.clear_zone:
        v.zone_id = None
    if body.parking_basement is not None:
        basement = body.parking_basement.strip().upper()
        if not basement_ok(db, v.society_id or c.society_id, basement,
                           has_zone=v.zone_id is not None):
            raise ApiError("validation_failed", "Choose a basement, or give the vehicle a zone.", 422)
        v.parking_basement = basement
    elif body.clear_zone and not v.parking_basement:
        # Removing the zone of a vehicle that has no basement would leave it without a place.
        raise ApiError("validation_failed", "Choose a basement, or keep the vehicle's zone.", 422)
    if body.parking_number is not None:
        number = clean_number(body.parking_number)
        if number is None:
            raise ApiError("validation_failed", "Enter the parking number (up to 60 characters).", 422)
        v.parking_number = number
    if body.photo_upload_id:
        v.photo_upload_id = asset(db, body.photo_upload_id, user.id, "vehicle", v.id)
    if body.rc_upload_id:
        v.rc_upload_id = asset(db, body.rc_upload_id, user.id, "rc", v.id)
        v.rc_verified = False
    if body.rc_verified is not None:
        if not v.rc_upload_id:
            raise ApiError("validation_failed", "An RC document is required.", 422)
        v.rc_verified = body.rc_verified
    if body.active is not None and body.active != v.active:
        sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == v.id))
        if not body.active and sub is not None and sub.status in ("Active", "Activating"):
            raise ApiError(
                "validation_failed",
                "Make the subscription inactive before deactivating this vehicle.",
                422,
            )
        v.active = body.active
    detail = body.model_dump(mode="json")
    if v.zone_id != old_zone:
        # The zone change is recorded by name, from and to (owner, 3 Nov 2026).
        names = {z.id: z.name for z in db.scalars(select(Zone).where(
            Zone.id.in_([i for i in (old_zone, v.zone_id) if i])))}
        detail["zone"] = [names.get(old_zone), names.get(v.zone_id)]
    audit(db, user.id, "vehicle", v.id, "update", detail)
    db.commit()
    return vehicle_out(db, v, store)


@admin.post("/customer-uploads", status_code=201)
def admin_upload(
    body: UploadIn,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    if body.purpose not in ("vehicle", "rc"):
        raise ApiError("validation_failed", "Use vehicle or rc.", 422)
    row, signed = media.request_customer_upload(
        db,
        store,
        owner_id=user.id,
        subject_id=None,
        purpose=body.purpose,
        content_type=body.content_type,
        size_bytes=body.size_bytes,
    )
    return {
        "id": str(row.id),
        "upload_url": signed.url,
        "method": signed.method,
        "headers": signed.headers,
    }


@admin.post("/customer-uploads/{upload_id}/confirm")
def admin_confirm_upload(
    upload_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    row = db.get(MediaUpload, upload_id)
    if row is None or row.owner_login_id != user.id or row.purpose not in ("vehicle", "rc"):
        raise ApiError("not_found", "Upload not found.", 404)
    media.confirm_upload(db, store, row)
    return {"id": str(row.id), "url": media.download_url(store, row)}


@admin.get("/customers/{customer_id}/notification-preferences")
def notification_preferences(
    customer_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    c = get_customer(db, customer_id)
    if c.login_id is None:
        raise ApiError("no_sign_in", "This customer has no sign-in yet.", 409)
    return NotificationService(db, get_default_sender()).preferences(c.login_id)


@admin.put("/customers/{customer_id}/notification-preferences")
def set_notification_preferences(
    customer_id: uuid.UUID,
    body: NotificationPreferencesIn,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    c = get_customer(db, customer_id)
    if c.login_id is None:
        raise ApiError("no_sign_in", "This customer has no sign-in yet.", 409)
    audit(db, user.id, "customer", c.id, "notifications", body.model_dump())
    return NotificationService(db, get_default_sender()).set_preferences(
        c.login_id, {i.event: i.enabled for i in body.items}
    )
