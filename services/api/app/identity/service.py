import hmac

from pydantic import BaseModel

from app.identity import tokens
from app.identity.repository import User, UserRepository
from app.platform.config import Settings
from app.platform.errors import ApiError


class LoginResult(BaseModel):
    role: str
    display_name: str
    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    def __init__(self, settings: Settings, users: UserRepository):
        self._s = settings
        self._users = users

    def _issue(self, user: User) -> LoginResult:
        access_ttl = self._s.access_token_minutes * 60
        refresh_ttl = self._s.refresh_token_days * 86400
        return LoginResult(
            role=user.role,
            display_name=user.display_name,
            access_token=tokens.issue(self._s, "access", user.role, user.id, access_ttl),
            refresh_token=tokens.issue(self._s, "refresh", user.role, user.id, refresh_ttl),
            expires_in=access_ttl,
        )

    def login(self, login_id: str, password: str) -> LoginResult:
        user = self._users.find_by_login_id(login_id)
        # An empty configured password switches that mock login off.
        if user is None or not user.password or not hmac.compare_digest(
            user.password.encode(), password.encode()
        ):
            raise ApiError("invalid_credentials", "The ID or password is not correct.", 401)
        return self._issue(user)

    def refresh(self, refresh_token: str) -> LoginResult:
        claims = tokens.verify(self._s, refresh_token, "refresh")
        user = self._users.get(claims[1]) if claims else None
        if user is None:
            raise ApiError("invalid_token", "Please sign in again.", 401)
        return self._issue(user)

    def authenticate(self, access_token: str) -> User:
        claims = tokens.verify(self._s, access_token, "access")
        user = self._users.get(claims[1]) if claims else None
        if user is None:
            raise ApiError("unauthorized", "Please sign in again.", 401)
        return user
