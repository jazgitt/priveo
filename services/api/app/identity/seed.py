"""Loads the logins that are not created in the app.

The admin `priveopapa` is always seeded (ADM-ACC-05). Its password comes
from the environment and is never in the repository. The two demo logins are
for the dev environment only, until the admin can create customers and crew.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.models import Login
from app.identity.service import _password_matches, hash_password
from app.platform.config import Settings
from app.platform.db import utcnow

ADMIN_LOGIN_ID = "priveopapa"


def _upsert(db: Session, role: str, login_id: str, display_name: str, password: str) -> str:
    login = db.scalar(select(Login).where(Login.login_id == login_id))
    if login is None:
        login = Login(role=role, login_id=login_id, display_name=display_name)
        db.add(login)
        outcome = "created"
    else:
        outcome = "kept"
    if not _password_matches(login.password_hash, password):
        login.password_hash = hash_password(password)
        login.password_changed_at = utcnow()
        outcome = "created" if outcome == "created" else "password set"
    # Seeding is also how a locked admin gets back in.
    login.locked = False
    login.failed_attempts = 0
    login.blocked_until = None
    return outcome


def seed_logins(db: Session, settings: Settings) -> dict[str, str]:
    """Returns what happened to each login ID. Safe to run again."""
    done: dict[str, str] = {}
    if settings.admin_password:
        done[ADMIN_LOGIN_ID] = _upsert(
            db, "admin", ADMIN_LOGIN_ID, "Priveo Admin", settings.admin_password)
    else:
        done[ADMIN_LOGIN_ID] = "skipped: no admin password is configured"
    if settings.seed_demo_logins:
        demo = [
            ("customer", "customer@priveo.test", "Aarav Mehta", settings.mock_customer_password),
            ("crew", "9000000002", "Ravi Kumar", settings.mock_crew_password),
        ]
        for role, login_id, name, password in demo:
            done[login_id] = (_upsert(db, role, login_id, name, password) if password
                              else "skipped: no password is configured")
    db.commit()
    return done
