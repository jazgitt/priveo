"""Smoke test for a deployed API: health, a wrong password and each role's entry data.

Usage: python scripts/smoke_test.py https://api-dev.example.com
The admin's password comes from SMOKE_ADMIN_PASSWORD. Nothing is printed except IDs and status codes.

SMOKE_ROLES (default "customer,crew,admin") limits the logins tried.

SMOKE_CREATE_USERS=true (the test deployment): the customer and crew are not
existing logins. The test creates its own for this run through the admin API,
checks their entry data, then removes them (DELETE /v1/admin/test-users/...,
which exists only in the test environment). The admin logs in with its
password as usual.

Without it (production, which has no demo logins: SMOKE_ROLES=admin), the
customer and crew come from SMOKE_CUSTOMER_PASSWORD and SMOKE_CREW_PASSWORD.
"""
import json
import os
import random
import sys
import urllib.error
import urllib.request

LOGINS = [
    ("customer", "9000000001", "SMOKE_CUSTOMER_PASSWORD"),
    ("crew", "9000000002", "SMOKE_CREW_PASSWORD"),
    ("admin", "priveopapa", "SMOKE_ADMIN_PASSWORD"),
]


def call(base: str, path: str, body: dict | None = None, token: str | None = None,
         method: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
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


def create_users(base: str, token: str, roles: list[str], created: list[str]) -> dict:
    """Makes a customer and a crew member for this run, in the smoke-test number range.
    Each login is added to `created` as soon as it exists, so cleanup removes it
    even if a later step fails. Returns {role: (login_id, password)}."""
    suffix = random.randrange(0, 1000)
    customer_mobile = f"9000099{suffix:03d}"
    crew_mobile = f"9000099{(suffix + 500) % 1000:03d}"
    made: dict[str, tuple[str, str]] = {}

    status, societies = call(base, "/v1/admin/directory/societies", token=token)
    check(status == 200 and societies, "smoke users: a society to use")
    # The parking basement must be one the society offers, so use a society that has one and its first basement.
    with_basement = [x for x in societies if x.get("parking_basements")]
    check(bool(with_basement), "smoke users: a society with a parking basement")
    society = with_basement[0]["id"]
    basement = with_basement[0]["parking_basements"][0]
    status, catalogue = call(base, "/v1/admin/directory/vehicle-catalogue", token=token)
    check(status == 200 and catalogue, "smoke users: a vehicle to use")
    status, plans = call(base, "/v1/admin/directory/plans", token=token)
    check(status == 200 and plans, "smoke users: a plan to use")

    if "customer" in roles:
        vehicle = {"society_id": society, "plan_id": plans[0]["id"],
                   "catalogue_id": catalogue[0]["id"],
                   "registration": f"HR99SM{suffix:04d}", "parking_basement": basement,
                   "parking_number": "99", "cutoff_time": "09:00", "interior_day": "Monday"}
        status, body = call(base, "/v1/admin/customers", token=token, body={
            "first_name": "Smoke", "last_name": "Customer", "mobile": customer_mobile,
            "flat": "SMOKE", "vehicle": vehicle})
        check(status == 201, f"smoke customer created (HTTP {status}: {body})")
        created.append(customer_mobile)
        # The MPIN starts as the last six digits of the mobile number.
        made["customer"] = (customer_mobile, customer_mobile[-6:])

    if "crew" in roles:
        status, hours = call(base, f"/v1/admin/crew/default-hours?society_id={society}", token=token)
        check(status == 200, f"smoke crew: default hours (HTTP {status})")
        status, body = call(base, "/v1/admin/crew", token=token, body={
            "name": "Smoke Crew", "mobile": crew_mobile, "society_id": society,
            "role": "Member", "working_hours": hours})
        check(status == 201, f"smoke crew created (HTTP {status})")
        created.append(body["login_id"])
        made["crew"] = (body["login_id"], body["password"])
    return made


def remove_users(base: str, token: str, created: list[str]) -> None:
    for login_id in created:
        status, _ = call(base, f"/v1/admin/test-users/{login_id}", token=token, method="DELETE")
        check(status == 204, f"smoke user removed (HTTP {status})")


def main() -> None:
    base = sys.argv[1].rstrip("/")
    status, body = call(base, "/v1/public/health")
    check(status == 200 and body.get("status") == "ok",
          f"health (build {body.get('build_number')})")
    # The wrong password goes first. The admin's right password below then
    # clears the wrong-attempt count, so a deploy never uses up a try.
    status, body = call(base, "/v1/auth/login",
                        {"login_id": "priveopapa", "password": "wrong", "role": "admin"})
    check(status == 401 and body.get("code") == "invalid_credentials", "wrong password rejected")
    roles = os.environ.get("SMOKE_ROLES", "customer,crew,admin").split(",")
    create = os.environ.get("SMOKE_CREATE_USERS", "").lower() == "true"
    created: list[str] = []
    token = None
    try:
        made: dict = {}
        if create:
            status, body = call(base, "/v1/auth/login", {
                "login_id": "priveopapa", "password": os.environ.get("SMOKE_ADMIN_PASSWORD", ""),
                "role": "admin"})
            check(status == 200 and body.get("access_token"), "admin login for the smoke users")
            token = body["access_token"]
            made = create_users(base, token, roles, created)
        for role, login_id, env in LOGINS:
            if role not in roles:
                continue
            if role in made:
                login_id, password = made[role]
            else:
                password = os.environ.get(env, "")
            status, body = call(base, "/v1/auth/login",
                                {"login_id": login_id, "password": password, "role": role})
            check(status == 200 and body.get("role") == role, f"login {role}")
            token = body["access_token"]
            if body.get("must_change_mpin"):
                # A new customer chooses its own MPIN first, as the app asks it to (CUS-01).
                new_mpin = f"{random.randrange(100000, 1000000)}"
                status, _ = call(base, "/v1/customer/mpin", token=token,
                                 body={"current_mpin": password, "new_mpin": new_mpin})
                check(status == 204, f"{role} chose a new MPIN (HTTP {status})")
            # Crew home now reads real visits; the old mock /crew/home was removed.
            path = "/v1/crew/visits" if role == "crew" else f"/v1/{role}/home"
            status, entry = call(base, path, token=token)
            check(status == 200, f"entry data {role} ({path}, HTTP {status})")
            if role == "crew":
                check(isinstance(entry.get("jobs"), list), "crew visits response")
    finally:
        if created:
            if token is None:
                status, body = call(base, "/v1/auth/login", {
                    "login_id": "priveopapa", "password": os.environ.get("SMOKE_ADMIN_PASSWORD", ""),
                    "role": "admin"})
                token = body.get("access_token")
            remove_users(base, token, created)


if __name__ == "__main__":
    main()
