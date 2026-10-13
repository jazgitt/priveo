"""Browser sign-in for the admin portal. The portal and the API share one
origin, so a session cookie plus a CSRF header replaces the bearer token."""
import uuid

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.identity import tokens
from app.identity.service import AuthService, User, normalise, role_for
from app.platform.config import Settings, get_settings
from app.platform.deps import get_auth_service, require_role
from app.platform.errors import ApiError
from app.platform.websession import (
    SESSION_COOKIE,
    check_csrf,
    clear_session_cookies,
    set_session_cookies,
)

router = APIRouter(prefix="/v1/web", tags=["web"])


class WebAuthLoginRequest(BaseModel):
    login_id: str
    password: str


class WebAuthProfile(BaseModel):
    user_id: uuid.UUID
    role: str
    display_name: str


@router.post("/login", response_model=WebAuthProfile)
def web_login(body: WebAuthLoginRequest, response: Response,
              auth: AuthService = Depends(get_auth_service),
              settings: Settings = Depends(get_settings)):
    """Admin user ID and password. The same lockout rules as the app apply.
    On success the session and CSRF cookies are set."""
    if role_for(normalise(body.login_id)) != "admin":
        # The portal is for admins. Crew and customers are told nothing more.
        raise ApiError("invalid_credentials", "The ID or password is not correct.", 401)
    result = auth.login(body.login_id, body.password, channel="web")
    claims = tokens.read_access(settings, result.access_token)
    assert claims is not None
    set_session_cookies(response, settings, result.access_token, claims.session_id,
                        result.expires_in)
    return WebAuthProfile(user_id=claims.login_id, role=result.role,
                          display_name=result.display_name)


@router.get("/me", response_model=WebAuthProfile)
def web_me(user: User = Depends(require_role("admin"))):
    return WebAuthProfile(user_id=user.id, role=user.role, display_name=user.display_name)


@router.post("/logout", status_code=204)
def web_logout(request: Request,
               auth: AuthService = Depends(get_auth_service),
               settings: Settings = Depends(get_settings)):
    """Ends the session and clears both cookies. With no session, or one that
    has already ended, it only clears the cookies. A live session needs the
    CSRF header like any other change."""
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        try:
            user = auth.authenticate(token)
        except ApiError:
            user = None
        if user is not None:
            check_csrf(settings, request, user.session_id)
            auth.logout(token)
    response = Response(status_code=204)
    clear_session_cookies(response)
    return response
