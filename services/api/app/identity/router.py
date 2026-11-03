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
    User,
)
from app.platform.db import get_db
from app.platform.deps import bearer_token, get_auth_service, require_role
from app.platform.errors import ApiError

router = APIRouter(prefix="/v1/auth", tags=["auth"])
admin = APIRouter(prefix="/v1/admin", tags=["admin"])


class LoginRequest(BaseModel):
    login_id: str
    # The customer's 6-digit MPIN, or the crew or admin password.
    password: str
    # Which sign-in this is: "customer", "crew" or "admin". Leave it out and a
    # 10-digit ID is crew and any other ID is an admin.
    role: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class CodeRequest(BaseModel):
    mobile: str


class VerifyCodeRequest(BaseModel):
    mobile: str
    code: str


class AuthSupportContact(BaseModel):
    helpline: str
    whatsapp: str
    hours: str


class CustomerSessionsEnded(BaseModel):
    ended: int


class SetMpinRequest(BaseModel):
    mpin_token: str
    mpin: str


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


@router.post("/code", response_model=CodeSent)
def send_code(body: CodeRequest, auth: AuthService = Depends(get_auth_service)):
    """Emails a customer a code to the email on file: "resend" and "forgot MPIN"."""
    return auth.send_code(body.mobile)


@router.post("/code/verify", response_model=CodeVerified)
def verify_code(body: VerifyCodeRequest, auth: AuthService = Depends(get_auth_service)):
    return auth.verify_code(body.mobile, body.code)


@router.post("/mpin", response_model=LoginResult)
def set_mpin(body: SetMpinRequest, auth: AuthService = Depends(get_auth_service)):
    """Sets a new MPIN after a correct code and signs the customer in."""
    return auth.set_mpin(body.mpin_token, body.mpin)


@router.post("/login", response_model=LoginResult)
def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    return auth.login(body.login_id, body.password, role=body.role)


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

    found = db.execute(select(Customer.login_id).where(Customer.id == customer_id)).first()
    if found is None:
        raise ApiError("not_found", "Customer not found.", 404)
    login_id = found[0]
    if login_id is None:  # No sign-in, so no sessions to end.
        return CustomerSessionsEnded(ended=0)
    ended = auth.end_customer_sessions(login_id, "admin_logout", actor_id=user.id,
                                       customer_id=customer_id)
    return CustomerSessionsEnded(ended=ended)
