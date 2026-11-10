import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.platform.config import get_settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


# What the admin portal loads: its own files, PostHog (analytics, EU region),
# images from any https host (photos come from the media store) and inline
# styles (the component library sets some). Nothing may frame the portal.
_POSTHOG = "https://eu.i.posthog.com https://eu-assets.i.posthog.com https://eu.posthog.com"
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    f"script-src 'self' {_POSTHOG}",
    f"connect-src 'self' {_POSTHOG}",
    "img-src 'self' data: blob: https:",
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data:",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

# Sent on every response, whatever the CSP mode.
STATIC_SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security review R-05: clickjacking, MIME sniffing, referrer and HSTS
    headers, plus a Content-Security-Policy as a backstop against injected script."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in STATIC_SECURITY_HEADERS.items():
            response.headers[name] = value
        mode = get_settings().csp_mode
        if mode == "enforce":
            response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
        elif mode != "off":
            response.headers["Content-Security-Policy-Report-Only"] = CONTENT_SECURITY_POLICY
        return response
