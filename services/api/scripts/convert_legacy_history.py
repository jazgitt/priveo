"""Convert the migrated service history already in `legacy_service_records` into
live history: a visit, its jobs and the Interior owed that week, the same as work
done in the app (customers.history_convert).

  python scripts/convert_legacy_history.py            trial run, saves nothing (prints the database host)
  python scripts/convert_legacy_history.py --apply    saves

Safe to run again: a day that already has a live visit (from an earlier run, or
from the app) is counted and left as it is. A weekly off writes nothing. The
legacy rows are kept (read-only) until the owner has checked production; a later
migration drops them. Reads DATABASE_URL. Run it on test, then prod, each by hand.
Counts only are printed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.customers.history_convert import LIVE, NOTHING, WRITTEN, admin_login_id, write_record
from app.customers.models import LegacyServiceRecord, Vehicle
from app.platform.db import get_engine
from app.platform.sync_guard import refuse_if_restored


def main() -> None:
    apply = "--apply" in sys.argv[1:]
    if any(a not in ("--apply",) for a in sys.argv[1:]):
        raise SystemExit(__doc__)
    engine = get_engine()
    refuse_if_restored(engine, "convert_legacy_history")
    print(f"Database: {engine.dialect.name}, host {engine.url.host or 'local file'}")
    results: Counter = Counter()
    with Session(engine) as db:
        admin = admin_login_id(db)
        rows = db.scalars(select(LegacyServiceRecord).order_by(LegacyServiceRecord.service_date)).all()
        for row in rows:
            vehicle = db.get(Vehicle, row.vehicle_id)
            results[write_record(db, vehicle, row.service_date, services=row.services,
                                 outcome=row.outcome, skip_reason=row.skip_reason,
                                 admin_id=admin)] += 1
        if apply:
            db.commit()
        else:
            db.rollback()
    print("SAVED" if apply else "TRIAL RUN: nothing was saved")
    print(f"legacy days read: {len(rows)}")
    print(f"  written as live visits: {results[WRITTEN]}")
    print(f"  already live (skipped): {results[LIVE]}")
    print(f"  weekly offs (no visit): {results[NOTHING]}")


if __name__ == "__main__":
    main()
