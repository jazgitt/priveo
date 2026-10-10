from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.home.repository import HomeRepository, MockHomeRepository
from app.identity.service import AuthService, User
from app.platform.config import Settings, get_settings
from app.platform.db import get_db
from app.platform.errors import ApiError


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
    def dependency(
        authorization: str | None = Header(default=None),
        auth: AuthService = Depends(get_auth_service),
    ) -> User:
        token = bearer_token(authorization)
        if token is None:
            raise ApiError("unauthorized", "Please sign in.", 401)
        user = auth.authenticate(token)
        if user.role != role:
            raise ApiError("forbidden", "You cannot open this.", 403)
        return user

    return dependency
