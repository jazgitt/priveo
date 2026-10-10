"""Access tokens are short-lived JWTs tied to a server session.
Refresh tokens are random strings; the database keeps only their hash."""
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

import jwt

from app.platform.config import Settings
from app.platform.db import utcnow

_ALGORITHM = "HS256"


@dataclass(frozen=True)
class AccessClaims:
    login_id: uuid.UUID
    session_id: uuid.UUID
    role: str


def issue_access(settings: Settings, login_id: uuid.UUID, session_id: uuid.UUID,
                 role: str) -> str:
    payload = {
        "sub": str(login_id),
        "sid": str(session_id),
        "role": role,
        "exp": utcnow() + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.token_secret, algorithm=_ALGORITHM)


def read_access(settings: Settings, token: str) -> AccessClaims | None:
    """The claims when the token is genuine and not expired."""
    try:
        p = jwt.decode(token, settings.token_secret, algorithms=[_ALGORITHM],
                       options={"require": ["sub", "sid", "role", "exp"]})
        return AccessClaims(uuid.UUID(p["sub"]), uuid.UUID(p["sid"]), p["role"])
    except (jwt.InvalidTokenError, ValueError):
        return None


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def keyed_hash(settings: Settings, value: str) -> str:
    """For short values such as a 6-digit code, which a plain hash would not
    protect: the key is the token secret, so the database alone is not enough."""
    return hmac.new(settings.token_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def same(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
