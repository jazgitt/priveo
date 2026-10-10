import re
import uuid
from dataclasses import dataclass
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.customers.models import Customer
from app.identity import tokens
from app.identity.models import AuthEvent, AuthSession, EmailCode, Login
from app.platform.config import Settings
from app.platform.db import utcnow
from app.platform.errors import ApiError

MAX_WRONG_ATTEMPTS = 5  # CRW-ACC-07, AUTH-13
CUSTOMER_BLOCK = timedelta(minutes=15)  # AUTH-13
ADMIN_MOBILE_IDLE = timedelta(hours=24)  # ADM-ACC-13
_TOUCH_EVERY = timedelta(minutes=5)
CODE_LIFETIME = timedelta(minutes=10)  # AUTH-05
CODE_RESEND_AFTER = timedelta(seconds=30)  # AUTH-05
MAX_WRONG_CODES = 5  # AUTH-07
MAX_CODES_AN_HOUR = 5  # AUTH-07
# How long a customer has to set the password after a correct code.
PASSWORD_TOKEN_LIFETIME = timedelta(minutes=10)

_hasher = PasswordHasher()
# Checked when the login does not exist, so the reply takes as long either way.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


class LoginResult(BaseModel):
    role: str
    display_name: str
    access_token: str
    refresh_token: str
    expires_in: int


class StartResult(BaseModel):
    # "password": ask for the password. "code": a code was emailed.
    next: str
    resend_in_seconds: int


class CodeSent(BaseModel):
    resend_in_seconds: int


class CodeVerified(BaseModel):
    password_token: str


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


def _not_registered() -> ApiError:
    return ApiError("email_not_registered",
                    "This email is not registered. Contact Priveo.", 404)  # AUTH-15


def _new_code_needed(message: str) -> ApiError:
    return ApiError("code_ended", message, 400)


def password_problem(password: str) -> str | None:
    """What is wrong with a new password, if anything (AUTH-12)."""
    if len(password) < 8:
        return "Use at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Use at least one letter and one number."
    if len(password) > 128:
        return "Use at most 128 characters."
    return None


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

    def _open_session(self, login: Login, channel: str, event: str) -> LoginResult:
        refresh_token = tokens.new_refresh_token()
        session = AuthSession(login_id=login.id, channel=channel,
                              refresh_hash=tokens.refresh_hash(refresh_token))
        self._db.add(session)
        self._event(login, event)
        self._db.commit()
        return self._result(login, session, refresh_token)

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
        return self._open_session(login, channel, "login")

    # --- A customer's first sign-in and forgotten password (AUTH-03, AUTH-16) ---

    def _customer(self, email: str) -> Login:
        key = normalise(email)
        login = self._db.scalar(
            select(Login).where(Login.login_id == key, Login.role == "customer"))
        if login is None or not login.active:
            raise _not_registered()
        return login

    def start(self, login_id: str) -> StartResult:
        """What the sign-in screen asks for next (AUTH-03, AUTH-11)."""
        if role_for(normalise(login_id)) != "customer":
            return StartResult(next="password", resend_in_seconds=0)
        login = self._customer(login_id)
        if login.password_hash:
            return StartResult(next="password", resend_in_seconds=0)
        return StartResult(next="code", resend_in_seconds=self._send_code(login))

    def send_code(self, email: str) -> CodeSent:
        """Sends a code: "resend", and the start of "forgot password"."""
        return CodeSent(resend_in_seconds=self._send_code(self._customer(email)))

    def _code_hash(self, code_id: uuid.UUID, code: str) -> str:
        return tokens.keyed_hash(self._s, f"{code_id}:{code}")

    def _live_code(self, login: Login) -> EmailCode | None:
        return self._db.scalar(
            select(EmailCode)
            .where(EmailCode.login_id == login.id, EmailCode.ended_at.is_(None))
            .order_by(EmailCode.created_at.desc()))

    def _send_code(self, login: Login) -> int:
        """Returns the seconds until another code can be asked for."""
        now = utcnow()
        wait = int(CODE_RESEND_AFTER.total_seconds())
        current = self._live_code(login)
        if (current is not None and current.verified_at is None
                and now - current.created_at < CODE_RESEND_AFTER):
            # Asked again within the countdown: the code already sent stands.
            return wait - int((now - current.created_at).total_seconds())

        sent = self._db.scalars(select(EmailCode.created_at).where(
            EmailCode.login_id == login.id,
            EmailCode.created_at > now - timedelta(hours=1))).all()
        if len(sent) >= MAX_CODES_AN_HOUR:
            raise ApiError("too_many_codes",
                           "Too many codes were requested. Try again in an hour.", 429)

        code = self._s.fixed_email_code
        if code is None:
            # Email is not connected yet. Nothing is stored and nothing is sent.
            raise ApiError("not_configured", "Email is not set up yet.", 503)

        self._db.execute(
            update(EmailCode)
            .where(EmailCode.login_id == login.id, EmailCode.ended_at.is_(None))
            .values(ended_at=now, ended_reason="replaced"))
        row = EmailCode(id=uuid.uuid4(), login_id=login.id, created_at=now,
                        expires_at=now + CODE_LIFETIME, code_hash="")
        row.code_hash = self._code_hash(row.id, code)
        self._db.add(row)
        self._event(login, "code_sent")
        self._db.commit()
        return wait

    def verify_code(self, email: str, code: str) -> CodeVerified:
        login = self._customer(email)
        row = self._live_code(login)
        now = utcnow()
        if row is None or row.verified_at is not None:
            raise _new_code_needed("Request a new code.")
        if row.expires_at <= now:
            row.ended_at, row.ended_reason = now, "expired"
            self._db.commit()
            raise _new_code_needed("The code has expired. Request a new one.")

        if not tokens.same(row.code_hash, self._code_hash(row.id, code.strip())):
            row.wrong_attempts += 1
            self._event(login, "code_failed")
            error = ApiError("invalid_code", "The code is not correct.", 400)
            if row.wrong_attempts >= MAX_WRONG_CODES:
                row.ended_at, row.ended_reason = now, "cancelled"
                error = _new_code_needed("Too many wrong attempts. Request a new code.")
            self._db.commit()
            raise error

        password_token = tokens.new_refresh_token()
        row.verified_at = now
        row.password_token_hash = tokens.refresh_hash(password_token)
        row.password_token_expires_at = now + PASSWORD_TOKEN_LIFETIME
        self._event(login, "code_verified")
        self._db.commit()
        return CodeVerified(password_token=password_token)

    def set_password(self, password_token: str, password: str,
                     channel: str = "mobile") -> LoginResult:
        """Sets the password after a correct code, and signs the customer in."""
        now = utcnow()
        row = self._db.scalar(select(EmailCode).where(
            EmailCode.password_token_hash == tokens.refresh_hash(password_token),
            EmailCode.ended_at.is_(None)))
        login = self._db.get(Login, row.login_id) if row else None
        if (row is None or login is None or not login.active
                or row.password_token_expires_at is None
                or row.password_token_expires_at <= now):
            raise _new_code_needed("This took too long. Request a new code.")
        problem = password_problem(password)
        if problem:
            raise ApiError("weak_password", problem, 422, {"password": problem})

        first_time = login.password_hash is None
        login.password_hash = hash_password(password)
        login.password_changed_at = now
        login.failed_attempts = 0
        login.blocked_until = None
        row.ended_at, row.ended_reason = now, "used"
        # The old password stops working everywhere (AUTH-16, AUTH-17).
        self._db.execute(
            update(AuthSession)
            .where(AuthSession.login_id == login.id, AuthSession.ended_at.is_(None))
            .values(ended_at=now, ended_reason="password_reset"))
        customer = self._db.scalar(select(Customer).where(Customer.login_id == login.id))
        if customer is not None and customer.terms_accepted_at is None:
            customer.terms_accepted_at = now  # AUTH-04
        return self._open_session(
            login, channel, "password_set" if first_time else "password_reset")

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
