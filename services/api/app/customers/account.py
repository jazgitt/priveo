"""The customer's own account: profile (ACC-01, ACC-06), email change
(ACC-08), password change, vehicle parking and photo (VEH-01, VEH-04), and
the uploads a customer makes (vehicle photo, complaint photos, RC document).
"""
import re
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.customers.models import Customer, EmailChange, Vehicle
from app.customers.service import _NAME
from app.directory.lookup import society_basements
from app.directory.models import Society
from app.identity import tokens
from app.identity.models import AuthSession, Login
from app.identity.service import (
    User,
    _password_matches,
    hash_password,
    normalise,
    password_problem,
)
from app.media import service as media
from app.media.models import STATUS_CONFIRMED, MediaUpload
from app.media.store import ObjectStore, get_object_store
from app.platform.config import Settings, get_settings
from app.platform.db import get_db, utcnow
from app.platform.deps import require_role
from app.platform.email import EmailSender, get_email_sender, new_code
from app.platform.errors import ApiError

router = APIRouter(tags=["customer"])
customer_only = require_role("customer")

CHANGE_CODE_LIFETIME = timedelta(minutes=10)  # same as AUTH-05
MAX_WRONG_CHANGE_CODES = 5
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class AccountProfileOut(BaseModel):
    first_name: str
    last_name: str
    email: str
    mobile: str
    society: str
    flat: str
    initials: str
    member_since: datetime | None
    # The new email waiting for its code, or None (ACC-08).
    pending_email: str | None = None


class AccountProfileEdit(BaseModel):
    first_name: str
    last_name: str
    mobile: str


class AccountEmailChange(BaseModel):
    email: str


class AccountEmailCode(BaseModel):
    code: str


class AccountEmailCodeSent(BaseModel):
    email: str
    expires_in_seconds: int


class AccountPasswordChange(BaseModel):
    current_password: str
    new_password: str


class AccountVehicleEdit(BaseModel):
    parking_basement: str | None = None
    parking_number: str | None = None


class AccountVehicleOut(BaseModel):
    id: str
    parking_basement: str
    parking_number: str
    photo_url: str | None
    rc_status: str


class AccountUploadRequest(BaseModel):
    # "vehicle" (VEH-01), "complaint" (ISS-04) or "rc" (ONB-12).
    purpose: str
    vehicle_id: str | None = None
    content_type: str
    size_bytes: int


class AccountUploadTicket(BaseModel):
    id: str
    upload_url: str
    method: str
    headers: dict[str, str]


class AccountUploadState(BaseModel):
    id: str
    status: str
    purpose: str
    url: str | None = None


def rc_status(db: Session, vehicle_id: uuid.UUID) -> str:
    """Derived: the admin has no RC verification step yet (VEH-03)."""
    return "Uploaded" if media.has_confirmed(db, f"rc/{vehicle_id}") else "Not uploaded"


class AccountService:
    def __init__(self, db: Session, settings: Settings, store: ObjectStore,
                 email: EmailSender):
        self.db, self.s, self.store, self.email = db, settings, store, email

    def customer(self, login_id: uuid.UUID) -> Customer:
        c = self.db.scalar(select(Customer).where(Customer.login_id == login_id))
        if c is None:
            raise ApiError("no_customer_record",
                           "Your details are not set up yet. Contact Priveo.", 404)
        return c

    def _pending(self, c: Customer) -> EmailChange | None:
        row = self.db.scalar(select(EmailChange).where(
            EmailChange.customer_id == c.id, EmailChange.ended_at.is_(None))
            .order_by(EmailChange.created_at.desc()))
        if row is not None and row.expires_at <= utcnow():
            return None
        return row

    def profile(self, login_id: uuid.UUID) -> AccountProfileOut:
        c = self.customer(login_id)
        pending = self._pending(c)
        initials = ((c.first_name[:1] + c.last_name[:1]) or c.email[:1]).upper()
        return AccountProfileOut(
            first_name=c.first_name, last_name=c.last_name, email=c.email, mobile=c.mobile,
            society=self.db.get(Society, c.society_id).name, flat=c.flat, initials=initials,
            member_since=c.created_at, pending_email=pending.new_email if pending else None)

    def edit_profile(self, login_id: uuid.UUID, body: AccountProfileEdit) -> AccountProfileOut:
        c = self.customer(login_id)
        first, last = " ".join(body.first_name.split()), " ".join(body.last_name.split())
        mobile = body.mobile.strip()
        errors: dict[str, str] = {}
        if not _NAME.fullmatch(first):
            errors["first_name"] = "Enter your first name, using letters only."
        if not _NAME.fullmatch(last):
            errors["last_name"] = "Enter your last name, using letters only."
        if mobile != c.mobile and not re.fullmatch(r"\d{10}", mobile):
            errors["mobile"] = "Enter a 10-digit mobile number."
        if errors:
            raise ApiError("validation_failed", "Please check the details.", 422, errors)
        c.first_name, c.last_name, c.mobile = first, last, mobile
        self.db.get(Login, c.login_id).display_name = f"{first} {last}"
        self.db.commit()
        return self.profile(login_id)

    # --- Email change (ACC-08) ---

    def start_email_change(self, login_id: uuid.UUID, email: str) -> AccountEmailCodeSent:
        c = self.customer(login_id)
        new = normalise(email)
        if not _EMAIL.fullmatch(new) or len(new) > 254:
            raise ApiError("validation_failed", "Enter a valid email.", 422,
                           {"email": "Enter a valid email."})
        taken = self.db.scalar(select(Login.id).where(Login.login_id == new)) is not None
        taken = taken or self.db.scalar(
            select(Customer.id).where(Customer.email == new, Customer.id != c.id)) is not None
        if new == c.email or taken:
            raise ApiError("email_in_use", "This email is already in use.", 409,
                           {"email": "This email is already in use."})
        now = utcnow()
        self.db.execute(update(EmailChange).where(
            EmailChange.customer_id == c.id, EmailChange.ended_at.is_(None)
        ).values(ended_at=now))
        code = new_code(self.s)
        row = EmailChange(id=uuid.uuid4(), customer_id=c.id, new_email=new, code_hash="",
                          created_at=now, expires_at=now + CHANGE_CODE_LIFETIME)
        row.code_hash = tokens.keyed_hash(self.s, f"{row.id}:{code}")
        self.db.add(row)
        self.db.commit()
        self.email.send_code(new, code, "email_change_code")
        return AccountEmailCodeSent(
            email=new, expires_in_seconds=int(CHANGE_CODE_LIFETIME.total_seconds()))

    def verify_email_change(self, login_id: uuid.UUID, code: str) -> AccountProfileOut:
        c = self.customer(login_id)
        row = self._pending(c)
        if row is None:
            raise ApiError("code_ended", "Request a new code.", 400)
        if not tokens.same(row.code_hash, tokens.keyed_hash(self.s, f"{row.id}:{code.strip()}")):
            row.wrong_attempts += 1
            error = ApiError("invalid_code", "The code is not correct.", 400)
            if row.wrong_attempts >= MAX_WRONG_CHANGE_CODES:
                row.ended_at = utcnow()
                error = ApiError("code_ended", "Too many wrong attempts. Request a new code.", 400)
            self.db.commit()
            raise error
        # Someone may have taken the email since the code was sent.
        if self.db.scalar(select(Login.id).where(Login.login_id == row.new_email)) is not None:
            row.ended_at = utcnow()
            self.db.commit()
            raise ApiError("email_in_use", "This email is already in use.", 409)
        row.ended_at = utcnow()
        c.email = row.new_email
        self.db.get(Login, c.login_id).login_id = row.new_email
        self.db.commit()
        return self.profile(login_id)

    # --- Password ---

    def change_password(self, user: User, body: AccountPasswordChange) -> None:
        login = self.db.get(Login, user.id)
        if not _password_matches(login.password_hash, body.current_password):
            raise ApiError("invalid_credentials", "The current password is not correct.", 422,
                           {"current_password": "The current password is not correct."})
        problem = password_problem(body.new_password)
        if problem:
            raise ApiError("weak_password", problem, 422, {"new_password": problem})
        now = utcnow()
        login.password_hash = hash_password(body.new_password)
        login.password_changed_at = now
        # Other devices sign out. This one stays signed in.
        self.db.execute(update(AuthSession).where(
            AuthSession.login_id == login.id, AuthSession.ended_at.is_(None),
            AuthSession.id != user.session_id).values(
                ended_at=now, ended_reason="password_changed"))
        self.db.commit()

    # --- Vehicles ---

    def _vehicle(self, c: Customer, vehicle_id: str) -> Vehicle:
        try:
            v = self.db.get(Vehicle, uuid.UUID(vehicle_id))
        except ValueError:
            v = None
        if v is None or v.customer_id != c.id or not v.active:
            raise ApiError("vehicle_not_found", "This vehicle was not found.", 404)
        return v

    def _vehicle_out(self, v: Vehicle) -> AccountVehicleOut:
        photo = media.vehicle_photo_urls(self.db, self.store, [v.id]).get(v.id)
        return AccountVehicleOut(
            id=str(v.id), parking_basement=v.parking_basement, parking_number=v.parking_number,
            photo_url=photo, rc_status=rc_status(self.db, v.id))

    def edit_vehicle(self, login_id: uuid.UUID, vehicle_id: str,
                     body: AccountVehicleEdit) -> AccountVehicleOut:
        """VEH-04: parking only. Car details change through support."""
        c = self.customer(login_id)
        v = self._vehicle(c, vehicle_id)
        errors: dict[str, str] = {}
        basement = number = None
        if body.parking_basement is not None:
            basement = body.parking_basement.strip().upper()
            if basement not in society_basements(self.db, c.society_id):
                errors["parking_basement"] = "Select the basement."
        if body.parking_number is not None:
            number = body.parking_number.strip()
            if not re.fullmatch(r"\d{1,5}", number):
                errors["parking_number"] = "Enter the parking number, in digits."
        if errors:
            raise ApiError("validation_failed", "Please check the details.", 422, errors)
        if basement is not None:
            v.parking_basement = basement
        if number is not None:
            v.parking_number = number
        self.db.commit()
        return self._vehicle_out(v)

    def vehicle_state(self, login_id: uuid.UUID, vehicle_id: str) -> AccountVehicleOut:
        return self._vehicle_out(self._vehicle(self.customer(login_id), vehicle_id))

    # --- Uploads ---

    def request_upload(self, login_id: uuid.UUID,
                       body: AccountUploadRequest) -> AccountUploadTicket:
        c = self.customer(login_id)
        subject = None
        if body.purpose in ("vehicle", "rc"):
            if body.vehicle_id is None:
                raise ApiError("validation_failed", "Please check the file.", 422,
                               {"vehicle_id": "Choose the vehicle."})
            subject = self._vehicle(c, body.vehicle_id).id
        upload, signed = media.request_customer_upload(
            self.db, self.store, owner_id=login_id, purpose=body.purpose, subject_id=subject,
            content_type=body.content_type, size_bytes=body.size_bytes)
        return AccountUploadTicket(id=str(upload.id), upload_url=signed.url,
                                   method=signed.method, headers=signed.headers)

    def _own_upload(self, login_id: uuid.UUID, upload_id: str) -> MediaUpload:
        try:
            upload = self.db.get(MediaUpload, uuid.UUID(upload_id))
        except ValueError:
            upload = None
        if (upload is None or upload.owner_login_id != login_id
                or upload.purpose not in media.CUSTOMER_PURPOSES):
            raise ApiError("not_found", "This upload was not found.", 404)
        return upload

    def _state(self, upload: MediaUpload) -> AccountUploadState:
        url = (media.download_url(self.store, upload)
               if upload.status == STATUS_CONFIRMED else None)
        return AccountUploadState(id=str(upload.id), status=upload.status,
                                  purpose=upload.purpose, url=url)

    def confirm_upload(self, login_id: uuid.UUID, upload_id: str) -> AccountUploadState:
        upload = self._own_upload(login_id, upload_id)
        # Confirming a vehicle photo makes it the vehicle's photo (newest wins).
        return self._state(media.confirm_upload(self.db, self.store, upload))

    def upload_state(self, login_id: uuid.UUID, upload_id: str) -> AccountUploadState:
        return self._state(self._own_upload(login_id, upload_id))


def get_account_service(db: Session = Depends(get_db),
                        settings: Settings = Depends(get_settings),
                        store: ObjectStore = Depends(get_object_store)) -> AccountService:
    return AccountService(db, settings, store, get_email_sender(settings))


@router.get("/profile", response_model=AccountProfileOut)
def get_profile(user: User = Depends(customer_only),
                svc: AccountService = Depends(get_account_service)):
    return svc.profile(user.id)


@router.patch("/profile", response_model=AccountProfileOut)
def patch_profile(body: AccountProfileEdit, user: User = Depends(customer_only),
                  svc: AccountService = Depends(get_account_service)):
    return svc.edit_profile(user.id, body)


@router.post("/profile/email", response_model=AccountEmailCodeSent)
def start_email_change(body: AccountEmailChange, user: User = Depends(customer_only),
                       svc: AccountService = Depends(get_account_service)):
    """Sends a code to the new email. The old email stays until it is verified."""
    return svc.start_email_change(user.id, body.email)


@router.post("/profile/email/verify", response_model=AccountProfileOut)
def verify_email_change(body: AccountEmailCode, user: User = Depends(customer_only),
                        svc: AccountService = Depends(get_account_service)):
    return svc.verify_email_change(user.id, body.code)


@router.post("/password", status_code=204)
def change_password(body: AccountPasswordChange, user: User = Depends(customer_only),
                    svc: AccountService = Depends(get_account_service)):
    svc.change_password(user, body)


@router.patch("/vehicles/{vehicle_id}", response_model=AccountVehicleOut)
def patch_vehicle(vehicle_id: str, body: AccountVehicleEdit,
                  user: User = Depends(customer_only),
                  svc: AccountService = Depends(get_account_service)):
    """Parking basement and number (VEH-04)."""
    return svc.edit_vehicle(user.id, vehicle_id, body)


@router.get("/vehicles/{vehicle_id}/account", response_model=AccountVehicleOut)
def vehicle_account(vehicle_id: str, user: User = Depends(customer_only),
                    svc: AccountService = Depends(get_account_service)):
    return svc.vehicle_state(user.id, vehicle_id)


@router.post("/uploads", response_model=AccountUploadTicket, status_code=201)
def request_upload(body: AccountUploadRequest, user: User = Depends(customer_only),
                   svc: AccountService = Depends(get_account_service)):
    """A signed upload URL for a vehicle photo, complaint photo or RC document."""
    return svc.request_upload(user.id, body)


@router.post("/uploads/{upload_id}/confirm", response_model=AccountUploadState)
def confirm_upload(upload_id: str, user: User = Depends(customer_only),
                   svc: AccountService = Depends(get_account_service)):
    return svc.confirm_upload(user.id, upload_id)


@router.get("/uploads/{upload_id}", response_model=AccountUploadState)
def get_upload(upload_id: str, user: User = Depends(customer_only),
               svc: AccountService = Depends(get_account_service)):
    return svc.upload_state(user.id, upload_id)

