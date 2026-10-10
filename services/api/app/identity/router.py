from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from app.identity.service import AuthService, LoginResult, User
from app.platform.deps import bearer_token, get_auth_service, require_role

router = APIRouter(prefix="/v1/auth", tags=["auth"])
admin = APIRouter(prefix="/v1/admin", tags=["admin"])


class LoginRequest(BaseModel):
    login_id: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


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
