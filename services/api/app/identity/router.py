from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.identity.service import (
    AuthService,
    CodeSent,
    CodeVerified,
    LoginResult,
    StartResult,
    User,
)
from app.platform.deps import bearer_token, get_auth_service, require_role

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


class SetPasswordRequest(BaseModel):
    password_token: str
    password: str


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
def logout(authorization: str | None = Header(default=None),
           auth: AuthService = Depends(get_auth_service)):
    # Signing out always succeeds, with or without a valid token.
    auth.logout(bearer_token(authorization))


@admin.post("/sessions/logout-all", status_code=204)
def logout_all(user: User = Depends(require_role("admin")),
               auth: AuthService = Depends(get_auth_service)):
    """Signs the admin out of every device, this one included."""
    auth.logout_all(user)
