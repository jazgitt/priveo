"""One-time move of every customer to the mobile number and MPIN sign-in (3 Nov 2026).

Before this, a customer signed in with their email and a password, and a
customer loaded from the owner's sheet had no sign-in at all. Now the sign-in
is the mobile number and a 6-digit MPIN. Every customer gets the first MPIN
(the last 6 digits of the mobile number) and must choose their own at the first
sign-in. Old passwords stop working and every signed-in phone is signed out.

It is run by hand, never by a migration or a workflow, and it can run again: a
customer whose login ID is already the mobile number is left as it is.

A mobile number that two customers share is not guessed at: both customers are
skipped and counted. The report holds counts only, no name, number or MPIN.
"""
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.customers.logins import ensure_login, give_default_mpin
from app.customers.models import Customer
from app.identity.models import AuthSession, EmailCode, Login
from app.platform.db import utcnow


@dataclass
class ConvertReport:
    applied: bool = False
    customers: int = 0
    logins_created: int = 0
    logins_converted: int = 0
    already_done: int = 0
    # Skipped, for the admin to settle.
    shared_mobile: int = 0
    bad_mobile: int = 0
    login_id_taken: int = 0


def convert_customer_logins(db: Session, *, apply: bool) -> ConvertReport:
    """With apply=False nothing is saved: it is a trial run that reports what
    would happen."""
    report = ConvertReport(applied=apply)
    try:
        shared = set(db.scalars(
            select(Customer.mobile).group_by(Customer.mobile).having(func.count() > 1)))
        for c in db.scalars(select(Customer).order_by(Customer.created_at, Customer.id)):
            report.customers += 1
            if len(c.mobile) != 10 or not c.mobile.isdigit():
                report.bad_mobile += 1
            elif c.mobile in shared:
                report.shared_mobile += 1
            elif c.login_id is None:
                if db.scalar(select(Login.id).where(
                        Login.role == "customer", Login.login_id == c.mobile)) is not None:
                    report.login_id_taken += 1
                else:
                    ensure_login(db, c)
                    report.logins_created += 1
            else:
                login = db.get(Login, c.login_id)
                if login.login_id == c.mobile:
                    report.already_done += 1
                elif db.scalar(select(Login.id).where(
                        Login.role == "customer", Login.login_id == c.mobile,
                        Login.id != login.id)) is not None:
                    report.login_id_taken += 1
                else:
                    login.login_id = c.mobile
                    give_default_mpin(login, c.mobile)
                    now = utcnow()
                    db.execute(update(AuthSession).where(
                        AuthSession.login_id == login.id, AuthSession.ended_at.is_(None)
                    ).values(ended_at=now, ended_reason="mpin_conversion"))
                    db.execute(update(EmailCode).where(
                        EmailCode.login_id == login.id, EmailCode.ended_at.is_(None)
                    ).values(ended_at=now, ended_reason="mpin_conversion"))
                    report.logins_converted += 1
        if apply:
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise
    return report
