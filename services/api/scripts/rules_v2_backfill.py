"""Creates this week's Interior entitlement for each Active subscription whose
plan includes Interior care (scheduler rules v1.2, SCHS-51, owner gate OG6).

  python scripts/rules_v2_backfill.py                       trial run, saves nothing
  python scripts/rules_v2_backfill.py --apply               saves
  python scripts/rules_v2_backfill.py --society <uuid>      one site only
  python scripts/rules_v2_backfill.py --undo-since <ISO time>            trial run
  python scripts/rules_v2_backfill.py --undo-since <ISO time> --apply    deletes

Only the CURRENT service week is created: a car owes nothing for weeks before the
run (no past debt). A fully paused week is waived, as the ledger does. Safe to
run again: a second run adds no row. Rows made by a run carry the time they were
created; `--undo-since` deletes the rows created at or after that time that are
still Pending and hold no job (DERIVED: no tag column exists, and none was added).

Reads DATABASE_URL (check the host it prints first). Run it by hand, only when the
owner approves (OG6). Nothing in any workflow runs it. The report holds counts only.
"""
from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.customers.models import Customer, Subscription, Vehicle
from app.platform import clock
from app.platform.db import get_engine
from app.scheduling import entitlements
from app.scheduling.models import InteriorEntitlement


@dataclass
class Report:
    subscriptions: int = 0
    created: int = 0
    waived: int = 0
    deleted: int = 0


def backfill(db: Session, today: date | None = None, society_id: uuid.UUID | None = None,
             apply: bool = False) -> Report:
    """Creates the current week's rows. Saves only when `apply`; a trial run
    counts the rows it would make and leaves the database as it was."""
    today = today or clock.today_ist()
    report = Report()
    query = (select(Subscription)
             .join(Vehicle, Vehicle.id == Subscription.vehicle_id)
             .join(Customer, Customer.id == Vehicle.customer_id)
             .where(Subscription.status == "Active", Vehicle.active.is_(True))
             .order_by(Vehicle.created_at, Vehicle.id))
    if society_id is not None:
        query = query.where(func.coalesce(Vehicle.society_id, Customer.society_id) == society_id)
    for sub in db.scalars(query):
        report.subscriptions += 1
        made = entitlements.ensure(db, sub, through=today, since=today)
        report.created += len(made)
        entitlements.refresh_waivers(db, sub)
        report.waived += sum(1 for r in made if r.status == entitlements.WAIVED)
    if apply:
        db.commit()
    else:
        db.rollback()
    return report


def undo(db: Session, since: datetime, apply: bool = False) -> Report:
    """Deletes the rows made at or after `since` that are still Pending and hold
    no job."""
    report = Report()
    where = (InteriorEntitlement.created_at >= since,
             InteriorEntitlement.status.in_((entitlements.PENDING, entitlements.WAIVED)),
             InteriorEntitlement.job_id.is_(None))
    report.deleted = db.scalar(select(func.count()).select_from(InteriorEntitlement).where(*where)) or 0
    if apply:
        db.execute(delete(InteriorEntitlement).where(*where))
        db.commit()
    return report


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    society = None
    since = None
    rest = [a for a in args if a != "--apply"]
    while rest:
        flag = rest.pop(0)
        if flag == "--society" and rest:
            society = uuid.UUID(rest.pop(0))
        elif flag == "--undo-since" and rest:
            since = datetime.fromisoformat(rest.pop(0))
        else:
            raise SystemExit(__doc__)
    engine = get_engine()
    print(f"Database: {engine.dialect.name}, host {engine.url.host or 'local file'}")
    with Session(engine) as db:
        if since is not None:
            report = undo(db, since, apply=apply)
            print("SAVED" if apply else "TRIAL RUN: nothing was deleted")
            print(f"rows deleted: {report.deleted}")
            return
        report = backfill(db, society_id=society, apply=apply)
    print("SAVED" if apply else "TRIAL RUN: nothing was saved")
    print(f"active subscriptions looked at: {report.subscriptions}")
    print(f"rows created: {report.created} (of which waived: {report.waived})")


if __name__ == "__main__":
    main()
