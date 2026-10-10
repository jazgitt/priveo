from fastapi import Depends, Header

from app.home.repository import HomeRepository, MockHomeRepository
from app.identity.repository import MockUserRepository, User
from app.identity.service import AuthService
from app.platform.config import Settings, get_settings
from app.platform.errors import ApiError


def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    return AuthService(settings, MockUserRepository(settings))


def get_home_repository() -> HomeRepository:
    return MockHomeRepository()


def require_role(role: str):
    def dependency(
        authorization: str | None = Header(default=None),
        auth: AuthService = Depends(get_auth_service),
    ) -> User:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise ApiError("unauthorized", "Please sign in.", 401)
        user = auth.authenticate(authorization[7:].strip())
        if user.role != role:
            raise ApiError("forbidden", "You cannot open this.", 403)
        return user

    return dependency
