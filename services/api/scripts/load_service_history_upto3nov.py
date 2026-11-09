"""One-time load of the service history up to 3 Nov 2026 ("calendar" sheet, workbook v4.1).

  python scripts/load_service_history_upto3nov.py "<file.xlsx>"                  trial run, saves nothing
  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --apply          saves
  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --report out.csv  where the not-loaded list goes
  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --fills fills.csv  empty cells the owner filled in

  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --through 2026-11-10  day columns up to that date
  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --alias 2001=XXXXXX2001 --alias 7577=XXXXXX7577
      a car number on the sheet that is registered under another number in the database
  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --from 2026-11-04 --through 2026-11-07
      status mode: the sheet sets the status of each Scheduled visit in those days, a day with no
      visit is written as live history, an empty cell records nothing. Nothing is notified.

Each day is written as live history (a visit, its jobs, and any Interior owed that
week), the same as work done in the app. The car number links a sheet row to a
vehicle. Safe to run again: a vehicle and day that is already loaded is left as it is.
Reads DATABASE_URL (the database it
loads into: check the host it prints first). Run it on local, then test, then
prod, each by hand; nothing in any workflow runs it.

--fills is a CSV with the columns car_number, day (YYYY-MM-DD) and value (ext, int,ext,
skipped, skipped - rain): the empty cells the owner decided. It holds car numbers, so keep it
in the tmp folder, never in the repository.

The console shows counts only. Every cell that could not be loaded is written to
a CSV (sheet row, day, cell, reason, car number), by default
tmp/service_history_not_loaded.csv in the repository (the tmp folder is
git-ignored). Keep the spreadsheet and that file out of the repository.
"""
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.customers.history_load import LAST_DAY, load_service_history, read_fills
from app.platform.db import get_engine
from app.platform.sync_guard import refuse_if_restored

DEFAULT_REPORT = Path(__file__).resolve().parents[3] / "tmp" / "service_history_not_loaded.csv"


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    report_path = DEFAULT_REPORT
    if "--report" in args:
        at = args.index("--report")
        if at + 1 >= len(args):
            raise SystemExit(__doc__)
        report_path = Path(args[at + 1])
        del args[at:at + 2]
    fills_path = None
    if "--fills" in args:
        at = args.index("--fills")
        if at + 1 >= len(args):
            raise SystemExit(__doc__)
        fills_path = Path(args[at + 1])
        del args[at:at + 2]
    aliases = {}
    while "--alias" in args:
        at = args.index("--alias")
        if at + 1 >= len(args) or "=" not in args[at + 1]:
            raise SystemExit(__doc__)
        sheet_car, registration = args[at + 1].split("=", 1)
        aliases[sheet_car.strip()] = registration.strip()
        del args[at:at + 2]
    since = None
    if "--from" in args:
        at = args.index("--from")
        if at + 1 >= len(args):
            raise SystemExit(__doc__)
        since = date.fromisoformat(args[at + 1])
        del args[at:at + 2]
    through = LAST_DAY
    if "--through" in args:
        at = args.index("--through")
        if at + 1 >= len(args):
            raise SystemExit(__doc__)
        through = date.fromisoformat(args[at + 1])
        del args[at:at + 2]
    args = [a for a in args if a != "--apply"]
    if len(args) != 1:
        raise SystemExit(__doc__)
    engine = get_engine()
    refuse_if_restored(engine, "load_service_history_upto3nov")
    print(f"Database: {engine.dialect.name}, host {engine.url.host or 'local file'}")
    with Session(engine) as db:
        try:
            fills = read_fills(fills_path) if fills_path else None
            report = load_service_history(db, args[0], apply=apply, fills=fills, through=through,
                                          since=since, aliases=aliases)
        except ValueError as problem:
            raise SystemExit(f"Stopped: {problem}") from problem
    print("SAVED" if apply else "TRIAL RUN: nothing was saved")
    print(f"vehicles in the sheet: {report.vehicles_in_sheet}, found in the database: {report.vehicles_matched}")
    print(f"days {'loaded' if apply else 'to load'}: {report.to_load}")
    print(f"  completed: {report.completed}")
    print(f"  skipped: {report.skipped}")
    print(f"weekly offs (counted, no visit written): {report.weekly_off}")
    print(f"already loaded earlier: {report.already_loaded}")
    print(f"empty cells before the vehicle started (ignored): {report.before_start}")
    print(f"empty cells filled by the owner's instruction: {report.owner_fills}")
    if report.updated or report.scheduled_without_entry or report.no_entry:
        print("scheduled visits set to the sheet's status:")
        for outcome, count in report.updated.most_common():
            print(f"  {outcome}: {count}")
        print("job statuses written:")
        for name, count in report.updated_jobs.most_common():
            print(f"  {name}: {count}")
        print(f"empty cells in the window (nothing recorded): {report.no_entry}")
        print(f"scheduled visits the sheet does not cover: {len(report.scheduled_without_entry)}")
    print(f"NOT LOADED: {len(report.not_loaded)}")
    for reason, count in report.reasons().most_common():
        print(f"  {reason}: {count}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["sheet_row", "day", "cell", "reason", "car_number"])
        for n in report.not_loaded:
            writer.writerow([n.sheet_row, n.day.isoformat(), n.cell, n.reason, n.car_number])
    print(f"not-loaded list written to: {report_path}")
    if report.scheduled_without_entry:
        extra = report_path.with_name(report_path.stem + "_scheduled_without_entry.csv")
        with extra.open("w", newline="", encoding="utf-8") as out:
            writer = csv.writer(out)
            writer.writerow(["car_number", "day", "visit_id"])
            for reg, day, visit_id in report.scheduled_without_entry:
                writer.writerow([reg, day.isoformat(), visit_id])
        print(f"scheduled visits the sheet does not cover written to: {extra}")
    if report.not_loaded:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
