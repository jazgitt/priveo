"""The one-off move of existing customers to the mobile number and MPIN sign-in."""
import pytest
from sqlalchemy import select

from app.customers.convert_logins import convert_customer_logins
from app.customers.models import Customer
from app.directory.models import Society
from app.identity.models import AuthSession, EmailCode, Login
from app.identity.service import _password_matches, hash_password
from app.platform.db import utcnow


@pytest.fixture
def society(db):
    row = Society(name="Green Meadows", sector="Sector 1")
    db.add(row)
    db.commit()
    return row


def customer(db, society, mobile, email=None, *, login=False, name="A"):
    row = Customer(first_name=name, last_name="Rao", email=email, mobile=mobile,
                   society_id=society.id)
    db.add(row)
    db.flush()
    if login:
        made = Login(role="customer", login_id=email, display_name=name,
                     password_hash=hash_password("old-password-1"))
        db.add(made)
        db.flush()
        row.login_id = made.id
    db.commit()
    return row


def test_an_old_email_login_moves_to_the_mobile_number(db, society):
    old = customer(db, society, "9000000111", "asha@example.com", login=True)
    db.add(AuthSession(login_id=old.login_id, refresh_hash="a" * 64, channel="mobile"))
    db.commit()

    report = convert_customer_logins(db, apply=True)
    assert (report.customers, report.logins_converted, report.logins_created) == (1, 1, 0)

    db.expire_all()
    login = db.get(Login, old.login_id)
    assert (login.login_id, login.must_change_mpin) == ("9000000111", True)
    assert _password_matches(login.password_hash, "000111")
    assert not _password_matches(login.password_hash, "old-password-1")
    assert db.get(Customer, old.id).email == "asha@example.com"
    assert db.scalar(select(AuthSession.ended_reason)) == "mpin_conversion"


def test_a_customer_with_no_login_gets_one(db, society):
    row = customer(db, society, "9000000222")
    report = convert_customer_logins(db, apply=True)
    assert (report.logins_created, report.logins_converted) == (1, 0)
    db.expire_all()
    login = db.get(Login, db.get(Customer, row.id).login_id)
    assert (login.role, login.login_id, login.must_change_mpin) == ("customer", "9000000222", True)
    assert _password_matches(login.password_hash, "000222")


def test_a_trial_run_saves_nothing(db, society):
    row = customer(db, society, "9000000333", "b@example.com", login=True)
    customer(db, society, "9000000444")
    report = convert_customer_logins(db, apply=False)
    assert (report.applied, report.logins_converted, report.logins_created) == (False, 1, 1)
    db.expire_all()
    assert db.get(Login, row.login_id).login_id == "b@example.com"
    assert db.scalar(select(Customer.login_id).where(Customer.mobile == "9000000444")) is None


def test_it_can_run_again_and_keeps_a_chosen_mpin(db, society):
    row = customer(db, society, "9000000555", "c@example.com", login=True)
    convert_customer_logins(db, apply=True)
    login = db.get(Login, row.login_id)
    login.password_hash, login.must_change_mpin = hash_password("482915"), False
    db.commit()

    again = convert_customer_logins(db, apply=True)
    assert (again.already_done, again.logins_converted, again.logins_created) == (1, 0, 0)
    db.expire_all()
    login = db.get(Login, row.login_id)
    assert _password_matches(login.password_hash, "482915") and login.must_change_mpin is False


def test_a_shared_or_bad_mobile_is_skipped_not_guessed(db, society):
    customer(db, society, "9000000666", "d1@example.com", login=True, name="D1")
    customer(db, society, "9000000666", "d2@example.com", login=True, name="D2")
    bad = customer(db, society, "12345", "e@example.com", login=True, name="E")
    report = convert_customer_logins(db, apply=True)
    assert (report.shared_mobile, report.bad_mobile, report.logins_converted) == (2, 1, 0)
    db.expire_all()
    assert db.get(Login, bad.login_id).login_id == "e@example.com"
    assert {c.login_id for c in db.scalars(select(Login)) if c.role == "customer"} == {
        "d1@example.com", "d2@example.com", "e@example.com"}


def test_a_taken_login_id_is_skipped(db, society):
    customer(db, society, "9000000777", "f@example.com", login=True)
    db.add(Login(role="customer", login_id="9000000777", display_name="Stray"))
    db.commit()
    report = convert_customer_logins(db, apply=True)
    assert (report.login_id_taken, report.logins_converted) == (1, 0)


def test_a_crew_login_with_the_same_mobile_does_not_get_in_the_way(db, society):
    db.add(Login(role="crew", login_id="9000000888", display_name="Crew"))
    db.commit()
    row = customer(db, society, "9000000888")
    assert convert_customer_logins(db, apply=True).logins_created == 1
    db.expire_all()
    assert db.get(Login, db.get(Customer, row.id).login_id).role == "customer"


def test_live_codes_end_with_the_conversion(db, society):
    row = customer(db, society, "9000000999", "g@example.com", login=True)
    db.add(EmailCode(login_id=row.login_id, code_hash="x" * 64, expires_at=utcnow()))
    db.commit()
    convert_customer_logins(db, apply=True)
    assert db.scalar(select(EmailCode.ended_reason)) == "mpin_conversion"


def test_the_script_prints_counts_and_the_database_first(db, society, monkeypatch, capsys):
    from scripts import convert_customer_logins as script

    customer(db, society, "9000000121", "h@example.com", login=True)
    monkeypatch.setattr(script, "get_engine", lambda: db.get_bind())
    monkeypatch.setattr("sys.argv", ["convert_customer_logins"])
    script.main()
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("Database: ") and "TRIAL RUN" in out[1]
    assert "sign-ins moved to the mobile number: 1" in out
    assert "h@example.com" not in "\n".join(out) and "9000000121" not in "\n".join(out)
    db.expire_all()
    assert db.scalar(select(Login.login_id).where(Login.role == "customer")) == "h@example.com"


def test_the_script_refuses_other_arguments(monkeypatch):
    from scripts import convert_customer_logins as script

    monkeypatch.setattr("sys.argv", ["convert_customer_logins", "--oops"])
    with pytest.raises(SystemExit):
        script.main()


def test_the_demo_login_moves_from_the_email_to_the_mobile(client, db):
    from app.identity import seed
    from app.platform.config import get_settings

    demo = db.scalar(select(Login).where(Login.login_id == seed.DEMO_CUSTOMER,
                                         Login.role == "customer"))
    key = demo.id
    demo.login_id = seed._OLD_DEMO_CUSTOMER  # how an earlier deploy left it
    db.commit()
    seed.seed_logins(db, get_settings())
    db.expire_all()
    assert db.get(Login, key).login_id == seed.DEMO_CUSTOMER
    assert db.get(Login, key).must_change_mpin is False
    assert len(list(db.scalars(select(Login).where(Login.role == "customer",
                                                   Login.login_id == seed.DEMO_CUSTOMER)))) == 1
