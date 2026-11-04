"""One-time load of the existing customers from the owner's spreadsheet.

  python scripts/import_customers.py "<file.xlsx>"           trial run, saves nothing
  python scripts/import_customers.py "<file.xlsx>" --apply   saves

Reads DATABASE_URL. The report names rows by serial number only, never a
name, phone number, email or registration number. Keep the spreadsheet out
of the repository (the /seed folder is git-ignored).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.customers.importer import import_workbook
from app.platform.db import get_engine


def run_payments_job() -> None:
    """The daily payments job, run once after loading so each subscription has its current
    cycle's payment and its status (from the cycle dates) straight away. No payment is invented
    beyond what the job makes; payments the admin records later set Paid or Initiated."""
    from app.billing.service import generate_due_payments, mark_overdue_and_inactive
    from app.platform.db import utcnow

    now = utcnow()
    made = generate_due_payments(now)
    report = mark_overdue_and_inactive(now)
    print(f"payments job: {made} cycle payments made, {report.marked_overdue} marked Over due, "
          f"{len(report.inactivated)} subscriptions made Inactive")


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--apply"]
    if len(args) != 1:
        raise SystemExit(__doc__)
    apply = "--apply" in sys.argv
    with Session(get_engine()) as db:
        report = import_workbook(db, args[0], apply=apply)

    print("SAVED" if apply else "TRIAL RUN: nothing was saved")
    print(f"customers: {report.customers_created} new, {report.customers_kept} already there")
    print(f"customers moved from the placeholder society to a named one: "
          f"{report.societies_set}")
    print(f"vehicles with a subscription: {report.vehicles_created} new, "
          f"{report.vehicles_kept} already there")
    print(f"vehicles without a subscription (standalone Deep Spa): "
          f"{report.standalone_vehicles_created} new, "
          f"{report.standalone_vehicles_kept} already there")
    print(f"add-on requests: {report.addons_created} new, {report.addons_kept} already there")
    for title, lines in (("Needs attention", report.warnings), ("Not loaded", report.errors)):
        print(f"\n{title}: {len(lines)}")
        for line in lines:
            print(f"  {line}")
    if report.errors:
        raise SystemExit(1)
    if apply:
        run_payments_job()


if __name__ == "__main__":
    main()
