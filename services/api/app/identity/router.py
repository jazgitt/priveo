import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.service import (
    AuthService,
    CodeSent,
    CodeVerified,
    LoginResult,
    StartResult,
    User,
)
from app.platform.db import get_db
from app.platform.deps import bearer_token, get_auth_service, require_role
from app.platform.errors import ApiError

router = APIRouter(prefix="/v1/auth", tags=["auth"])
admin = APIRouter(prefix="/v1/admin", tags=["admin"])


class LoginRequest(BaseModel):
    login_id: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class StartRequest(BaseModel):
    login_id: str


class CodeRequest(BaseModel):
    email: str


class VerifyCodeRequest(BaseModel):
    email: str
    code: str


class AuthSupportContact(BaseModel):
    helpline: str
    whatsapp: str
    hours: str


class CustomerSessionsEnded(BaseModel):
    ended: int


class SetPasswordRequest(BaseModel):
    password_token: str
    password: str


@router.get("/support-contact", response_model=AuthSupportContact)
def support_contact(db: Session = Depends(get_db)):
    """The helpline and WhatsApp numbers for the "not registered" screen, which
    a visitor sees before signing in (AUTH-15)."""
    from app.directory import lookup
    return AuthSupportContact(
        helpline=lookup.setting(db, "support.helpline"),
        whatsapp=lookup.setting(db, "support.whatsapp"), hours=lookup.setting(db, "support.hours")
    )


@router.get("/legal-links")
def legal_links():
    from app.platform.config import get_settings
    settings = get_settings()
    return {"terms": settings.terms_url, "privacy": settings.privacy_url}


@router.post("/start", response_model=StartResult)
def start(body: StartRequest, auth: AuthService = Depends(get_auth_service)):
    """Says what to ask for next: the password, or the code just emailed."""
    return auth.start(body.login_id)


@router.post("/code", response_model=CodeSent)
def send_code(body: CodeRequest, auth: AuthService = Depends(get_auth_service)):
    """Emails a customer a new code: "resend" and "forgot password"."""
    return auth.send_code(body.email)


@router.post("/code/verify", response_model=CodeVerified)
def verify_code(body: VerifyCodeRequest, auth: AuthService = Depends(get_auth_service)):
    return auth.verify_code(body.email, body.code)


@router.post("/password", response_model=LoginResult)
def set_password(body: SetPasswordRequest, auth: AuthService = Depends(get_auth_service)):
    """Sets the password after a correct code and signs the customer in."""
    return auth.set_password(body.password_token, body.password)


@router.post("/login", response_model=LoginResult)
def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    return auth.login(body.login_id, body.password)


@router.post("/refresh", response_model=LoginResult)
def refresh(body: RefreshRequest, auth: AuthService = Depends(get_auth_service)):
    return auth.refresh(body.refresh_token)


@router.post("/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None), auth: AuthService = Depends(get_auth_service)
):
    # Signing out always succeeds, with or without a valid token.
    auth.logout(bearer_token(authorization))


@admin.post("/sessions/logout-all", status_code=204)
def logout_all(
    user: User = Depends(require_role("admin")), auth: AuthService = Depends(get_auth_service)
):
    """Signs the admin out of every device, this one included."""
    auth.logout_all(user)


@admin.post("/customers/{customer_id}/sessions/logout", response_model=CustomerSessionsEnded)
def end_customer_sessions(
    customer_id: uuid.UUID,
    user: User = Depends(require_role("admin")),
    auth: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
):
    """Signs a customer out on every phone (AUTH-17, ADM-CUS-21)."""
    from app.customers.models import Customer

    login_id = db.scalar(select(Customer.login_id).where(Customer.id == customer_id))
    if login_id is None:
        raise ApiError("not_found", "Customer not found.", 404)
    ended = auth.end_customer_sessions(login_id, "admin_logout", actor_id=user.id,
                                       customer_id=customer_id)
    return CustomerSessionsEnded(ended=ended)
