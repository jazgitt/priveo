"""Customer onboarding and administration shared by the portal and Add vehicle."""

import re
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.billing.models import Payment, PaymentEvent
from app.changes.cycle import renewal_date
from app.customers.models import WEEKDAYS, Customer, EmailChange, Subscription, Vehicle
from app.customers.service import _NAME, read_cutoff, show_registration
from app.customers.welcome import send_welcome
from app.directory import lookup
from app.directory.models import DirectoryAudit, Plan, Society, VehicleCatalogueEntry
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
from app.platform.deps import require_role
from app.platform.errors import ApiError

admin = APIRouter(prefix="/v1/admin", tags=["customer-administration"])
customer = APIRouter(prefix="/v1/customer", tags=["customer-administration"])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VehicleCreate(Input):
    society_id: uuid.UUID
    catalogue_id: uuid.UUID
    registration: str
    parking_basement: str
    parking_number: str
    plan_id: uuid.UUID | None = None
    cutoff_time: str | None = None
    interior_day: str | None = None
    photo_upload_id: uuid.UUID
    rc_upload_id: uuid.UUID | None = None
    first_payment_status: str = "Due"


class CustomerCreate(Input):
    first_name: str
    last_name: str
    email: str
    mobile: str
    flat: str = Field(default="", max_length=40)
    vehicle: VehicleCreate


class CustomerEdit(Input):
    first_name: str
    last_name: str
    mobile: str
    flat: str = Field(default="", max_length=40)


class EmailCorrection(Input):
    email: str


class VehicleEdit(Input):
    registration: str | None = None
    catalogue_id: uuid.UUID | None = None
    parking_basement: str | None = None
    parking_number: str | None = None
    photo_upload_id: uuid.UUID | None = None
    rc_upload_id: uuid.UUID | None = None
    rc_verified: bool | None = None


class SubscriptionEdit(Input):
    plan_id: uuid.UUID | None = None
    cutoff_time: str | None = None
    interior_day: str | None = None


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
    if not _NAME.fullmatch(last):
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
    basement, number = body.parking_basement.upper(), body.parking_number.strip()
    if plan and (cutoff is None or (plan.includes_interior and body.interior_day not in WEEKDAYS)):
        raise ApiError("validation_failed", "Choose a cutoff and interior care day.", 422)
    if basement not in lookup.society_basements(db, society.id) or not re.fullmatch(
        r"\d{1,5}", number
    ):
        raise ApiError("validation_failed", "Check the parking location.", 422)
    reg = registration(db, body.registration)
    photo = asset(db, body.photo_upload_id, owner, "vehicle")
    rc = asset(db, body.rc_upload_id, owner, "rc") if body.rc_upload_id else None
    if body.first_payment_status not in ("Due", "Over due", "Initiated", "Received"):
        raise ApiError("validation_failed", "Choose a payment status.", 422)
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
    sub = Subscription(
        vehicle_id=v.id,
        plan_id=plan.id,
        monthly_price_rupees=plan.monthly_price_rupees,
        status="Activating",
        first_service_date=today_ist(),
        cutoff_time=cutoff,
        interior_day=body.interior_day if plan.includes_interior else None,
    )
    db.add(sub)
    db.flush()
    payment = Payment(
        customer_id=c.id,
        vehicle_id=v.id,
        subscription_id=sub.id,
        kind="Plan",
        description=f"First month of {plan.name}",
        amount_rupees=sub.monthly_price_rupees,
        status=body.first_payment_status,
        due_date=today_ist(),
        cycle_start=today_ist(),
        cycle_end=today_ist() + timedelta(days=lookup.setting(db, "billing.cycle_days")),
        received_at=utcnow() if body.first_payment_status == "Received" else None,
        confirmed_by=by if body.first_payment_status == "Received" else None,
        overdue_since=today_ist() if body.first_payment_status == "Over due" else None,
        initiated_at=utcnow() if body.first_payment_status == "Initiated" else None,
    )
    db.add(payment)
    db.flush()
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            from_status=None,
            to_status=payment.status,
            by_login_id=by,
            note="First payment at onboarding",
        )
    )
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
        "society_id": str(society.id),
        "society": society.name,
        "registration": show_registration(v.registration),
        "make": v.make,
        "model": v.model,
        "variant": v.variant,
        "category": v.category,
        "parking_basement": v.parking_basement,
        "parking_number": v.parking_number,
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
            "first_service_date": sub.first_service_date,
            "pending_plan_id": str(sub.pending_plan_id) if sub.pending_plan_id else None,
            "pending_from": sub.pending_from,
        }
        if sub
        else None,
        "payments": [
            {
                "id": str(p.id),
                "status": p.status,
                "amount_rupees": p.amount_rupees,
                "due_date": p.due_date,
            }
            for p in payments
        ],
    }


def detail(db, c, store):
    from app.customers.history import imported_history
    login = db.get(Login, c.login_id)
    return {
        "id": str(c.id),
        "first_name": c.first_name,
        "last_name": c.last_name,
        "email": c.email,
        "mobile": c.mobile,
        "flat": c.flat,
        "email_verified": c.email_verified_at is not None,
        "password_set": login.password_hash is not None,
        "onboarding_confirmed": c.onboarding_confirmed_at is not None,
        "imported_history": imported_history(db, c.id),
        "vehicles": [
            vehicle_out(db, v, store)
            for v in db.scalars(
                select(Vehicle)
                .where(Vehicle.customer_id == c.id, Vehicle.active.is_(True))
                .order_by(Vehicle.created_at)
            )
        ],
    }


@admin.get("/customers")
def list_customers(
    q: str = "",
    society_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = (
        select(Customer)
        .outerjoin(Vehicle, Vehicle.customer_id == Customer.id)
        .outerjoin(Society, Society.id == func.coalesce(Vehicle.society_id, Customer.society_id))
    )
    if q:
        text = f"%{q.strip()}%"
        query = query.where(
            or_(
                (Customer.first_name + " " + Customer.last_name).ilike(text),
                Customer.last_name.ilike(text),
                Customer.email.ilike(text),
                Customer.mobile.ilike(text),
                Vehicle.registration.ilike(text.replace(" ", "")),
                Society.name.ilike(text),
            )
        )
    if society_id:
        query = query.where(Society.id == society_id)
    found = list(db.scalars(query.distinct().order_by(
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
    password_set = dict(db.execute(
        select(Login.id, Login.password_hash.is_not(None))
        .where(Login.id.in_([c.login_id for c in found]))
    ).all()) if ids else {}
    return [
        {
            "id": str(c.id),
            "name": f"{c.first_name} {c.last_name}",
            "email": c.email,
            "mobile": c.mobile,
            "flat": c.flat,
            "email_verified": c.email_verified_at is not None,
            "password_set": bool(password_set.get(c.login_id)),
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
    email = valid_email(body.email)
    existing = db.scalar(select(Customer).where(Customer.email == email))
    if existing:
        return {**detail(db, existing, store), "existing": True}
    if db.scalar(select(Login.id).where(Login.login_id == email)):
        raise ApiError("email_in_use", "This email is already in use.", 409)
    first, last, mobile = valid_person(body.first_name, body.last_name, body.mobile)
    login = Login(role="customer", login_id=email, display_name=f"{first} {last}")
    db.add(login)
    db.flush()
    c = Customer(
        login_id=login.id,
        first_name=first,
        last_name=last,
        email=email,
        mobile=mobile,
        society_id=body.vehicle.society_id,
        flat=body.flat,
    )
    db.add(c)
    db.flush()
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
    c.first_name, c.last_name, c.mobile = valid_person(body.first_name, body.last_name, body.mobile)
    c.flat = body.flat
    db.get(Login, c.login_id).display_name = f"{c.first_name} {c.last_name}"
    audit(db, user.id, "customer", c.id, "update", body.model_dump())
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


@customer.post("/vehicles", status_code=201)
def customer_add_vehicle(
    body: VehicleCreate,
    user: User = Depends(require_role("customer")),
    db: Session = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
):
    if body.first_payment_status != "Due":
        raise ApiError("validation_failed", "The first payment starts Due.", 422)
    c = db.scalar(select(Customer).where(Customer.login_id == user.id))
    if c is None:
        raise ApiError("not_found", "Customer not found.", 404)
    if body.plan_id is None:
        raise ApiError("validation_failed", "Choose a plan; standalone vehicles are created by admin.", 422)
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


def reset_login(db, c, by, reason):
    login = db.get(Login, c.login_id)
    login.password_hash = None
    login.password_changed_at = utcnow()
    login.failed_attempts, login.blocked_until = 0, None
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
    db.execute(
        update(EmailChange)
        .where(EmailChange.customer_id == c.id, EmailChange.ended_at.is_(None))
        .values(ended_at=utcnow())
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
    if db.scalar(select(Login.id).where(Login.login_id == email)):
        raise ApiError("email_in_use", "This email is already in use.", 409)
    old = c.email
    reset_login(db, c, user.id, "email_corrected")
    c.email = email
    c.email_verified_at = None
    db.get(Login, c.login_id).login_id = email
    audit(db, user.id, "customer", c.id, "email", {"email": [old, email]})
    db.commit()
    return {"welcome_sent": send_welcome(db, c)}


@admin.post("/customers/{customer_id}/reset-password")
def reset_password(
    customer_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    reset_login(db, get_customer(db, customer_id), user.id, "password_reset")
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
    if body.plan_id:
        plan = db.get(Plan, body.plan_id)
        if plan is None or not plan.active:
            raise ApiError("validation_failed", "Choose an active plan.", 422)
        sub.pending_plan_id = plan.id
        sub.pending_from = renewal_date(db, sub.vehicle_id, sub.first_service_date, today_ist())
    if body.cutoff_time is not None:
        cutoff = read_cutoff(body.cutoff_time)
        if cutoff is None:
            raise ApiError("validation_failed", "Choose a cutoff in 30-minute steps.", 422)
        sub.cutoff_time = cutoff
    if body.interior_day is not None:
        chosen_plan = sub.pending_plan_id or sub.plan_id
        plan = db.get(Plan, chosen_plan) if chosen_plan else None
        if body.interior_day not in WEEKDAYS or (plan and not plan.includes_interior):
            raise ApiError("validation_failed", "Choose an interior care day for this plan.", 422)
        sub.interior_day = body.interior_day
    audit(db, user.id, "subscription", sub.id, "update", body.model_dump(mode="json"))
    db.commit()
    from app.scheduling.service import reconcile_vehicle

    reconcile_vehicle(db, sub.vehicle_id)
    # ADM-CUS-14/15: admin plan and default preferences edits are silent.
    # Explicit skip/operations actions keep their separate notification rules.
    return {"updated": True, "pending_from": sub.pending_from}


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
    if body.parking_basement is not None:
        if body.parking_basement.upper() not in lookup.society_basements(
            db, v.society_id or c.society_id
        ):
            raise ApiError("validation_failed", "Choose a basement.", 422)
        v.parking_basement = body.parking_basement.upper()
    if body.parking_number is not None:
        if not re.fullmatch(r"\d{1,5}", body.parking_number):
            raise ApiError("validation_failed", "Enter a numeric parking number.", 422)
        v.parking_number = body.parking_number
    if body.photo_upload_id:
        v.photo_upload_id = asset(db, body.photo_upload_id, user.id, "vehicle", v.id)
    if body.rc_upload_id:
        v.rc_upload_id = asset(db, body.rc_upload_id, user.id, "rc", v.id)
        v.rc_verified = False
    if body.rc_verified is not None:
        if not v.rc_upload_id:
            raise ApiError("validation_failed", "An RC document is required.", 422)
        v.rc_verified = body.rc_verified
    audit(db, user.id, "vehicle", v.id, "update", body.model_dump(mode="json"))
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
    return NotificationService(db, get_default_sender()).preferences(c.login_id)


@admin.put("/customers/{customer_id}/notification-preferences")
def set_notification_preferences(
    customer_id: uuid.UUID,
    body: NotificationPreferencesIn,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    c = get_customer(db, customer_id)
    audit(db, user.id, "customer", c.id, "notifications", body.model_dump())
    return NotificationService(db, get_default_sender()).set_preferences(
        c.login_id, {i.event: i.enabled for i in body.items}
    )
