"""Helpers for tests that make customers: a customer signs in with a mobile
number, so each test customer needs its own."""
import hashlib


def mobile_for(label: str) -> str:
    """A 10-digit mobile number that belongs to this label only (an email or a
    name). The same label always gives the same number."""
    return "9" + str(int(hashlib.sha1(label.encode()).hexdigest(), 16) % 10**9).zfill(9)


def sign_in_customer(client, label_or_mobile: str, password: str):
    """Signs a customer in. A label that is not a number is turned into one."""
    mobile = label_or_mobile if label_or_mobile.isdigit() else mobile_for(label_or_mobile)
    return client.post("/v1/auth/login", json={
        "login_id": mobile, "password": password, "role": "customer"})
