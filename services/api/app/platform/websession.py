"""The browser session: two cookies and a double-submit CSRF check.

The session cookie holds the same signed token the mobile app sends as a
bearer token. It is httpOnly, so page scripts cannot read it. The CSRF cookie
is readable on purpose: the portal copies it into the X-CSRF-Token header on
every request that changes data. Its value is derived from the session, so a
cookie planted from another site does not match."""
import uuid

from fastapi import Request, Response

from app.identity import tokens
from app.platform.config import Settings
from app.platform.errors import ApiError

SESSION_COOKIE = "priveo_session"
CSRF_COOKIE = "priveo_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def csrf_value(settings: Settings, session_id: uuid.UUID) -> str:
    return tokens.keyed_hash(settings, f"csrf:{session_id}")


def set_session_cookies(response: Response, settings: Settings, access_token: str,
                        session_id: uuid.UUID, max_age: int) -> None:
    response.set_cookie(SESSION_COOKIE, access_token, max_age=max_age, path="/",
                        httponly=True, secure=True, samesite="strict")
    response.set_cookie(CSRF_COOKIE, csrf_value(settings, session_id), max_age=max_age,
                        path="/", httponly=False, secure=True, samesite="strict")


def clear_session_cookies(response: Response) -> None:
    for name, httponly in ((SESSION_COOKIE, True), (CSRF_COOKIE, False)):
        response.delete_cookie(name, path="/", httponly=httponly, secure=True,
                               samesite="strict")


def check_csrf(settings: Settings, request: Request, session_id: uuid.UUID) -> None:
    """Raises 403 unless the header, the cookie and the session all agree."""
    header = request.headers.get(CSRF_HEADER, "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    expected = csrf_value(settings, session_id)
    if not (header and tokens.same(header, expected) and tokens.same(cookie, expected)):
        raise ApiError("csrf_failed", "Please reload the page and try again.", 403)
