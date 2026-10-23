from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.home.repository import HomeRepository, MockHomeRepository
from app.identity.service import AuthService, User
from app.platform.config import Settings, get_settings
from app.platform.db import get_db
from app.platform.errors import ApiError
from app.platform.websession import SAFE_METHODS, SESSION_COOKIE, check_csrf


def get_auth_service(settings: Settings = Depends(get_settings),
                     db: Session = Depends(get_db)) -> AuthService:
    return AuthService(settings, db)


def get_home_repository() -> HomeRepository:
    return MockHomeRepository()


def bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization[7:].strip()


def require_role(role: str):
    """The signed-in person, when they hold `role`. A bearer token (the mobile
    app) or the portal's session cookie both work. A request that changes data
    and comes by cookie must also carry the matching CSRF header."""

    def dependency(
        request: Request,
        authorization: str | None = Header(default=None),
        auth: AuthService = Depends(get_auth_service),
        settings: Settings = Depends(get_settings),
    ) -> User:
        token = bearer_token(authorization)
        by_cookie = False
        if token is None:
            token = request.cookies.get(SESSION_COOKIE)
            by_cookie = token is not None
        if token is None:
            raise ApiError("unauthorized", "Please sign in.", 401)
        user = auth.authenticate(token)
        if by_cookie and request.method not in SAFE_METHODS:
            check_csrf(settings, request, user.session_id)
        if user.role != role:
            raise ApiError("forbidden", "You cannot open this.", 403)
        return user

    return dependency


def require_feature(key: str):
    """Refuse a request while the admin has switched the feature off. Put it in
    an endpoint's `dependencies=[...]`. It adds no query: flags are cached."""
    from app.features import registry, service

    if key not in registry.BY_KEY:
        raise KeyError(key)

    def dependency(db: Session = Depends(get_db)) -> None:
        if not service.is_enabled(db, key):
            raise ApiError("feature_disabled", "This is not available right now.", 403)

    return dependency
