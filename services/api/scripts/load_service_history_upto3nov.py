"""One-time load of the service history up to 3 Nov 2026 ("calendar" sheet, workbook v4.1).

  python scripts/load_service_history_upto3nov.py "<file.xlsx>"                  trial run, saves nothing
  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --apply          saves
  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --report out.csv  where the not-loaded list goes
  python scripts/load_service_history_upto3nov.py "<file.xlsx>" --fills fills.csv  empty cells the owner filled in

The car number links a sheet row to a vehicle. Safe to run again: a vehicle and
day that is already loaded is left as it is. Reads DATABASE_URL (the database it
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.customers.history_load import load_service_history, read_fills
from app.platform.db import get_engine

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
    args = [a for a in args if a != "--apply"]
    if len(args) != 1:
        raise SystemExit(__doc__)
    engine = get_engine()
    print(f"Database: {engine.dialect.name}, host {engine.url.host or 'local file'}")
    with Session(engine) as db:
        try:
            fills = read_fills(fills_path) if fills_path else None
            report = load_service_history(db, args[0], apply=apply, fills=fills)
        except ValueError as problem:
            raise SystemExit(f"Stopped: {problem}") from problem
    print("SAVED" if apply else "TRIAL RUN: nothing was saved")
    print(f"vehicles in the sheet: {report.vehicles_in_sheet}, found in the database: {report.vehicles_matched}")
    print(f"days {'loaded' if apply else 'to load'}: {report.to_load}")
    print(f"  completed: {report.completed}")
    print(f"  skipped: {report.skipped} (of these, {report.weekly_off_added} are the 21 Oct weekly off with no column)")
    print(f"already loaded earlier: {report.already_loaded}")
    print(f"empty cells before the vehicle started (ignored): {report.before_start}")
    print(f"empty cells filled by the owner's instruction: {report.owner_fills}")
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
    if report.not_loaded:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
