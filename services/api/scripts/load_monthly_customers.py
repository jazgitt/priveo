"""One-time load of the "Monthly Customer" sheet (3 Nov 2026).

  python scripts/load_monthly_customers.py "<file.xlsx>"                   trial run, saves nothing
  python scripts/load_monthly_customers.py "<file.xlsx>" --apply           saves
  python scripts/load_monthly_customers.py "<file.xlsx>" --society "Name"  names the society

Without --society it uses the only society in the database, and stops if there is
more than one. Reads DATABASE_URL (the database it loads into: check it first).
The report names rows by serial number only, never a name, phone number or car
number. Keep the spreadsheet out of the repository (the /tmp folder is git-ignored).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.customers.sheet_load import load_monthly_customers
from app.platform.db import get_engine


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    society = None
    if "--society" in args:
        at = args.index("--society")
        society = args[at + 1] if at + 1 < len(args) else None
        del args[at:at + 2]
    args = [a for a in args if a != "--apply"]
    if len(args) != 1:
        raise SystemExit(__doc__)
    engine = get_engine()
    print(f"Database: {engine.dialect.name}, host {engine.url.host or 'local file'}")
    with Session(engine) as db:
        try:
            report = load_monthly_customers(db, args[0], society_name=society, apply=apply)
        except ValueError as problem:
            raise SystemExit(str(problem)) from None

    print("SAVED" if apply else "TRIAL RUN: nothing was saved")
    print(f"society: {report.society}")
    print(f"plans: {report.plans_created} new, {report.plans_renamed} renamed")
    print(f"zones: {report.zones_created} new")
    print(f"customers: {report.customers_created} new, {report.customers_kept} already there")
    print(f"vehicles: {report.vehicles_created} new, {report.vehicles_kept} already there")
    print(f"subscriptions: {report.subscriptions_created} new")
    for title, lines in (("Needs attention", report.warnings), ("Not loaded", report.errors)):
        print(f"\n{title}: {len(lines)}")
        for line in lines:
            print(f"  {line}")
    if report.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
