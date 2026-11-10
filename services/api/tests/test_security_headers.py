"""Security review R-05: every response carries the security headers."""
import pytest

from app.platform.config import get_settings
from app.platform.middleware import CONTENT_SECURITY_POLICY, STATIC_SECURITY_HEADERS

PATHS = ["/health", "/v1/public/config", "/portal/", "/v1/admin/customers", "/no-such-page"]


@pytest.mark.parametrize("path", PATHS)
def test_static_headers_on_every_response(client, path):
    response = client.get(path)
    for name, value in STATIC_SECURITY_HEADERS.items():
        assert response.headers[name] == value, (path, name)


def test_csp_is_report_only_by_default(client):
    response = client.get("/health")
    assert response.headers["Content-Security-Policy-Report-Only"] == CONTENT_SECURITY_POLICY
    assert "Content-Security-Policy" not in response.headers


def test_csp_enforced_when_configured(client, monkeypatch):
    monkeypatch.setenv("CSP_MODE", "enforce")
    get_settings.cache_clear()
    response = client.get("/health")
    assert response.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert "Content-Security-Policy-Report-Only" not in response.headers


def test_csp_can_be_switched_off(client, monkeypatch):
    monkeypatch.setenv("CSP_MODE", "off")
    get_settings.cache_clear()
    response = client.get("/health")
    assert "Content-Security-Policy" not in response.headers
    assert "Content-Security-Policy-Report-Only" not in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"


def test_policy_blocks_framing_and_plugins():
    directives = {d.split()[0]: d for d in CONTENT_SECURITY_POLICY.split("; ")}
    assert directives["frame-ancestors"] == "frame-ancestors 'none'"
    assert directives["object-src"] == "object-src 'none'"
    assert directives["default-src"] == "default-src 'self'"
    assert "'unsafe-inline'" not in directives["script-src"]
    assert "'unsafe-eval'" not in directives["script-src"]


def test_error_responses_also_carry_headers(client):
    response = client.get("/v1/admin/customers")  # 401 without a login
    assert response.status_code == 401
    assert response.headers["X-Content-Type-Options"] == "nosniff"
