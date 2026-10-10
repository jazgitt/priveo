import re
import uuid
from dataclasses import dataclass
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.identity import tokens
from app.identity.models import AuthEvent, AuthSession, Login
from app.platform.config import Settings
from app.platform.db import utcnow
from app.platform.errors import ApiError

MAX_WRONG_ATTEMPTS = 5  # CRW-ACC-07, AUTH-13
CUSTOMER_BLOCK = timedelta(minutes=15)  # AUTH-13
ADMIN_MOBILE_IDLE = timedelta(hours=24)  # ADM-ACC-13
_TOUCH_EVERY = timedelta(minutes=5)

_hasher = PasswordHasher()
# Checked when the login does not exist, so the reply takes as long either way.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


class LoginResult(BaseModel):
    role: str
    display_name: str
    access_token: str
    refresh_token: str
    expires_in: int


@dataclass(frozen=True)
class User:
    """The signed-in person behind a request."""

    id: uuid.UUID
    role: str
    display_name: str
    session_id: uuid.UUID


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _password_matches(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and bool(password_hash)
    except (VerificationError, InvalidHashError):
        return False


def role_for(login_id: str) -> str:
    """An email is a customer, a 10-digit mobile is crew, the rest is an admin
    user ID (CRW-ACC-02)."""
    if "@" in login_id:
        return "customer"
    if re.fullmatch(r"\d{10}", login_id):
        return "crew"
    return "admin"


def normalise(login_id: str) -> str:
    return login_id.strip().lower()


def _invalid() -> ApiError:
    return ApiError("invalid_credentials", "The ID or password is not correct.", 401)


def _signed_out() -> ApiError:
    return ApiError("unauthorized", "Please sign in again.", 401)


class AuthService:
    def __init__(self, settings: Settings, db: Session):
        self._s = settings
        self._db = db

    def _event(self, login: Login | None, kind: str) -> None:
        self._db.add(AuthEvent(login_id=login.id if login else None, kind=kind))

    def _result(self, login: Login, session: AuthSession, refresh_token: str) -> LoginResult:
        return LoginResult(
            role=login.role,
            display_name=login.display_name,
            access_token=tokens.issue_access(self._s, login.id, session.id, login.role),
            refresh_token=refresh_token,
            expires_in=self._s.access_token_minutes * 60,
        )

    def _end(self, session: AuthSession, reason: str) -> None:
        if session.ended_at is None:
            session.ended_at = utcnow()
            session.ended_reason = reason

    def login(self, login_id: str, password: str, channel: str = "mobile") -> LoginResult:
        key = normalise(login_id)
        login = self._db.scalar(
            select(Login).where(Login.login_id == key, Login.role == role_for(key)))
        if login is None or not login.active:
            _password_matches(None, password)
            raise _invalid()

        now = utcnow()
        if login.locked:
            raise ApiError("account_locked",
                           "This login is locked. Ask the admin to reset your password.", 403)
        if login.blocked_until and login.blocked_until > now:
            raise ApiError("too_many_attempts",
                           "Too many wrong attempts. Try again in 15 minutes.", 429)

        if not _password_matches(login.password_hash, password):
            login.failed_attempts += 1
            self._event(login, "login_failed")
            error = _invalid()
            if login.failed_attempts >= MAX_WRONG_ATTEMPTS:
                login.failed_attempts = 0
                if login.role == "customer":
                    login.blocked_until = now + CUSTOMER_BLOCK
                    error = ApiError("too_many_attempts",
                                     "Too many wrong attempts. Try again in 15 minutes.", 429)
                else:
                    login.locked = True
                    error = ApiError(
                        "account_locked",
                        "This login is locked. Ask the admin to reset your password.", 403)
                self._event(login, "locked")
            self._db.commit()
            raise error

        login.failed_attempts = 0
        login.blocked_until = None
        refresh_token = tokens.new_refresh_token()
        session = AuthSession(login_id=login.id, channel=channel,
                              refresh_hash=tokens.refresh_hash(refresh_token))
        self._db.add(session)
        self._event(login, "login")
        self._db.commit()
        return self._result(login, session, refresh_token)

    def _live(self, session: AuthSession | None) -> tuple[AuthSession, Login]:
        """The session and its login, when the device is still signed in."""
        if session is None or session.ended_at is not None:
            raise _signed_out()
        login = self._db.get(Login, session.login_id)
        if login is None or not login.active:
            raise _signed_out()
        idle = utcnow() - session.last_used_at
        if login.role == "admin" and session.channel == "mobile" and idle > ADMIN_MOBILE_IDLE:
            self._end(session, "idle")
            self._db.commit()
            raise _signed_out()
        return session, login

    def refresh(self, refresh_token: str) -> LoginResult:
        found = self._db.scalar(select(AuthSession).where(
            AuthSession.refresh_hash == tokens.refresh_hash(refresh_token)))
        session, login = self._live(found)
        # Each refresh token works once.
        new_token = tokens.new_refresh_token()
        session.refresh_hash = tokens.refresh_hash(new_token)
        session.last_used_at = utcnow()
        self._db.commit()
        return self._result(login, session, new_token)

    def authenticate(self, access_token: str) -> User:
        claims = tokens.read_access(self._s, access_token)
        if claims is None:
            raise _signed_out()
        session, login = self._live(self._db.get(AuthSession, claims.session_id))
        now = utcnow()
        if now - session.last_used_at > _TOUCH_EVERY:
            session.last_used_at = now
            self._db.commit()
        return User(login.id, login.role, login.display_name, session.id)

    def logout(self, access_token: str | None) -> None:
        """Ends this device's session. Never fails: the phone signs out anyway."""
        claims = tokens.read_access(self._s, access_token) if access_token else None
        session = self._db.get(AuthSession, claims.session_id) if claims else None
        if session is not None and session.ended_at is None:
            self._end(session, "logout")
            self._event(self._db.get(Login, session.login_id), "logout")
            self._db.commit()

    def logout_all(self, user: User) -> None:
        """Ends every session of this login, the one in use included (ADM-ACC-14)."""
        self._db.execute(
            update(AuthSession)
            .where(AuthSession.login_id == user.id, AuthSession.ended_at.is_(None))
            .values(ended_at=utcnow(), ended_reason="logout_all"))
        self._event(self._db.get(Login, user.id), "logout_all")
        self._db.commit()
