"""Read fixture data through a RUNNING API. This is an API smoke suite, not UI E2E.

Uses fixture passwords from the environment. Never prints tokens/passwords.
Logins create sessions; GET endpoints may apply normal billing reconciliation.
"""

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def run_suite(call, data, password, admin_password, selected=None):
    results = []

    def request(path, *, body=None, token=None, expected=200):
        status, response = call(path, body, token)
        if status != expected:
            raise AssertionError(f"{path}: expected {expected}, received {status}")
        return response

    def login(login_id, secret, role):
        body = request("/v1/auth/login", body={"login_id": login_id, "password": secret})
        assert body["role"] == role, f"Wrong role for {login_id}"
        return body["access_token"]

    scenarios = [row for row in data["scenarios"] if not selected or row["id"] in selected]
    if not scenarios:
        raise AssertionError("Manifest contains none of the requested scenarios.")
    for row in scenarios:
        token = login(row["customer_login"], password, "customer")
        request("/v1/customer/home", token=token)
        vehicles = request("/v1/customer/vehicles", token=token)
        assert {item["id"] for item in vehicles} == set(
            row.get("active_vehicle_ids", row["vehicle_ids"])
        ), row["id"]
        request("/v1/customer/calendar?month=" + row["as_of"][:7], token=token)
        request("/v1/customer/notifications", token=token)
        if row["id"] in {"C22", "C23"}:
            pending = request("/v1/customer/checkins/pending", token=token)
            assert len(pending) == (1 if row["id"] == "C23" else 0), row["id"]
        for visit_id in row["visit_ids"]:
            visit = request("/v1/customer/visits/" + visit_id, token=token)
            assert visit["vehicle_id"] in row["vehicle_ids"], row["id"]
        for payment_id in row["payment_ids"]:
            request(
                "/v1/customer/payments/" + payment_id,
                token=token,
                expected=404 if payment_id in row.get("voided_payment_ids", []) else 200,
            )
        other = next(
            (item for item in data["scenarios"] if item["id"] != row["id"] and item["vehicle_ids"]),
            None,
        )
        if other:
            request("/v1/customer/vehicles/" + other["vehicle_ids"][0], token=token, expected=404)
        if row["id"].startswith(("R", "A")):
            for crew_login in row["crew_logins"][:3]:
                crew_token = login(crew_login, password, "crew")
                request("/v1/crew/profile", token=crew_token)
                request("/v1/crew/day?date=" + row["as_of"], token=crew_token)
                request("/v1/crew/visits?date=" + row["as_of"], token=crew_token)
        results.append({"scenario": row["id"], "status": "passed"})
    admin_token = login(data["admin_login"], admin_password, "admin")
    for path in [
        "/v1/admin/home",
        "/v1/admin/complaints",
        "/v1/admin/alerts",
        "/v1/admin/ratings",
        "/v1/admin/checkins",
    ]:
        request(path, token=admin_token)
    for row in scenarios:
        for schedule_id in row["schedule_ids"]:
            request("/v1/admin/scheduling/board?schedule_id=" + schedule_id, token=admin_token)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--scenarios", help="Comma-separated scenario IDs; default all in manifest")
    args = parser.parse_args()
    password = os.environ.get("TEST_DATA_PASSWORD", "")
    admin_password = os.environ.get("TEST_DATA_ADMIN_PASSWORD", "")
    if not password or not admin_password:
        parser.error("Set TEST_DATA_PASSWORD and TEST_DATA_ADMIN_PASSWORD.")
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    selected = (
        {item.strip().upper() for item in args.scenarios.split(",")} if args.scenarios else None
    )
    if selected and selected - {item["id"] for item in data["scenarios"]}:
        parser.error("Requested scenarios are missing from the manifest.")
    base = args.base_url.rstrip("/")

    def call(path, body, token):
        payload = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(base + path, data=payload)
        if payload:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    print(json.dumps(run_suite(call, data, password, admin_password, selected), indent=2))


if __name__ == "__main__":
    main()
