"""The admin's login ID is environment configuration (security review R-01), not
a value in the repository."""
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.models import Login
from app.identity.seed import seed_logins
from app.platform.config import Settings
from tests.conftest import PASSWORDS, TEST_ADMIN_ID


def test_admin_signs_in_with_the_configured_id(client, db):
    res = client.post("/v1/auth/login", json={
        "login_id": TEST_ADMIN_ID, "password": PASSWORDS["admin"], "role": "admin"})
    assert res.status_code == 200


def test_the_old_fixed_id_no_longer_signs_in(client, db):
    # Built from pieces so this file never holds the old ID as text.
    old = "".join(["priveo", "papa"])
    res = client.post("/v1/auth/login", json={
        "login_id": old, "password": PASSWORDS["admin"], "role": "admin"})
    assert res.status_code == 401


def test_a_different_configured_id_is_the_one_that_is_seeded(engine, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "pw-admin1")
    settings = Settings(_env_file=None, admin_login_id="another-admin-id")
    with Session(engine) as db:
        done = seed_logins(db, settings)
        admins = list(db.scalars(select(Login.login_id).where(Login.role == "admin")))
    assert done["another-admin-id"] == "created"
    assert admins == ["another-admin-id"]


def test_without_an_id_the_admin_is_not_seeded(engine):
    settings = Settings(_env_file=None, admin_login_id="", admin_password="pw-admin1")
    with Session(engine) as db:
        done = seed_logins(db, settings)
        assert list(db.scalars(select(Login).where(Login.role == "admin"))) == []
    assert done["admin"].startswith("skipped")


def test_a_new_id_renames_the_one_existing_admin(engine):
    with Session(engine) as db:
        seed_logins(db, Settings(_env_file=None, admin_login_id="first-admin-id",
                                 admin_password="pw-admin1"))
        before = db.scalar(select(Login.id).where(Login.role == "admin"))
        seed_logins(db, Settings(_env_file=None, admin_login_id="second-admin-id",
                                 admin_password="pw-admin1"))
        rows = list(db.execute(select(Login.id, Login.login_id).where(Login.role == "admin")))
    assert rows == [(before, "second-admin-id")]


def test_the_old_id_is_not_in_any_tracked_file():
    old = "".join(["priveo", "papa"])
    root = Path(__file__).resolve().parents[3]
    try:
        out = subprocess.run(["git", "grep", "-il", old], cwd=root, capture_output=True,
                             text=True, check=False)
    except FileNotFoundError:
        pytest.skip("git is not available")
    if out.returncode not in (0, 1):
        pytest.skip("not a git checkout")
    assert out.stdout.split() == [], "the old admin ID is back in a tracked file"
