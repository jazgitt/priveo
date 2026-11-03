"""One-time move of every customer to the mobile number and MPIN sign-in.

  python scripts/convert_customer_logins.py            trial run, saves nothing
  python scripts/convert_customer_logins.py --apply    saves

Every customer gets the first MPIN (the last 6 digits of the mobile number),
and must choose their own at the first sign-in. Customers who have no sign-in
(for example those loaded from a sheet) get one; customers who signed in with
an email move to their mobile number, their old password stops working and
their phones are signed out. Safe to run again. Customers whose mobile number
is shared with another customer, or is not 10 digits, are skipped and counted.

Reads DATABASE_URL (the database it works on: check the host it prints first).
The report holds counts only, never a name, number or MPIN. Run it by hand;
nothing in any workflow runs it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.customers.convert_logins import convert_customer_logins
from app.platform.db import get_engine


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    if [a for a in args if a != "--apply"]:
        raise SystemExit(__doc__)
    engine = get_engine()
    print(f"Database: {engine.dialect.name}, host {engine.url.host or 'local file'}")
    with Session(engine) as db:
        report = convert_customer_logins(db, apply=apply)
    print("SAVED" if apply else "TRIAL RUN: nothing was saved")
    print(f"customers: {report.customers}")
    print(f"sign-ins created: {report.logins_created}")
    print(f"sign-ins moved to the mobile number: {report.logins_converted}")
    print(f"already on the mobile number: {report.already_done}")
    skipped = report.shared_mobile + report.bad_mobile + report.login_id_taken
    print(f"skipped: {skipped}")
    print(f"  mobile number shared by customers: {report.shared_mobile}")
    print(f"  mobile number not 10 digits: {report.bad_mobile}")
    print(f"  mobile number already another sign-in: {report.login_id_taken}")
    if skipped:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
