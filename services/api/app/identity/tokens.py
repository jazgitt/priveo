"""Stateless signed mock tokens. Phase 1 replaces these with real sessions."""
import base64
import hashlib
import hmac
import time

from app.platform.config import Settings


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def issue(settings: Settings, kind: str, role: str, user_id: str, ttl_seconds: int) -> str:
    payload = f"{kind}|{role}|{user_id}|{int(time.time()) + ttl_seconds}"
    body = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{body}.{_sign(settings.token_secret, payload)}"


def verify(settings: Settings, token: str, kind: str) -> tuple[str, str] | None:
    """Return (role, user_id) when the token is genuine, of this kind and not expired."""
    try:
        body, sig = token.split(".", 1)
        payload = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
        if not hmac.compare_digest(sig, _sign(settings.token_secret, payload)):
            return None
        tkind, role, user_id, exp = payload.split("|")
        if tkind != kind or int(exp) < time.time():
            return None
        return role, user_id
    except (ValueError, UnicodeDecodeError):
        return None
