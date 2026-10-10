from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.identity.service import AuthService, LoginResult
from app.platform.deps import get_auth_service

router = APIRouter(prefix="/v1/auth", tags=["auth"])


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
def logout():
    # Mock tokens are stateless. Phase 1 revokes the server session here.
    return None
