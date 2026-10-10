"""Smoke test for a deployed API: health, three mock logins, three home calls.

Usage: python scripts/smoke_test.py https://api-dev.example.com
Passwords come from SMOKE_CUSTOMER_PASSWORD, SMOKE_CREW_PASSWORD and
SMOKE_ADMIN_PASSWORD. Nothing is printed except IDs and status codes.
"""
import json
import os
import sys
import urllib.error
import urllib.request

LOGINS = [
    ("customer", "customer@priveo.test", "SMOKE_CUSTOMER_PASSWORD"),
    ("crew", "9000000002", "SMOKE_CREW_PASSWORD"),
    ("admin", "priveopapa", "SMOKE_ADMIN_PASSWORD"),
]


def call(base: str, path: str, body: dict | None = None, token: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(ok: bool, what: str) -> None:
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        sys.exit(1)


def main() -> None:
    base = sys.argv[1].rstrip("/")
    status, body = call(base, "/v1/public/health")
    check(status == 200 and body.get("status") == "ok", f"health (build {body.get('build_number')})")
    for role, login_id, env in LOGINS:
        password = os.environ.get(env, "")
        status, body = call(base, "/v1/auth/login", {"login_id": login_id, "password": password})
        check(status == 200 and body.get("role") == role, f"login {role}")
        status, _ = call(base, f"/v1/{role}/home", token=body["access_token"])
        check(status == 200, f"home {role}")
    status, body = call(base, "/v1/auth/login", {"login_id": "priveopapa", "password": "wrong"})
    check(status == 401 and body.get("code") == "invalid_credentials", "wrong password rejected")


if __name__ == "__main__":
    main()
