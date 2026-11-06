"""Scheduler rules v1.2: move one live site to the new weekly off and durations.

  python scripts/rules_v2_site_data.py --site "Society name"             dry run
  python scripts/rules_v2_site_data.py --site "Society name" --apply     saves
  python scripts/rules_v2_site_data.py --durations                       dry run
  python scripts/rules_v2_site_data.py --durations --apply               saves
  python scripts/rules_v2_site_data.py --revert printout.json --apply    reverses

What it changes (SCHS-50; owner gates OG3, OG4, OG5):
  --site        the weekly-off weekday (Wednesday) is taken out of every working
                slot of that site (OG3), and made a day off in the per-weekday
                hours of that site's crew (OG3). Crew with no per-weekday hours
                are listed and left alone: the closed day gives them no
                capacity anyway.
  --durations   Cleaning-External and Cleaning-Internal 20 to 30 minutes, and the
                two extra add-ons (Extra interior cleaning, Special exterior
                cleaning) 20 to 30 (OG4). Durations are shared by all sites, so
                this is its own run. Deep Spa is not touched.
Schedules that already hold Wednesday jobs are not touched (OG5).

A dry run is the default and saves nothing. Applying twice changes nothing: a
row that already has the new value is not listed. The printout ends with a JSON
block that holds every old and new value; save it, and pass it to --revert to
put the old values back (a value is put back only if it still has the new value).

Reads DATABASE_URL (the database it works on: check the host it prints first).
Run it by hand, on test first. Nothing in any workflow runs it. It does not set
`scheduler.rules_version`.
"""
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers the tables)
from app.directory import lookup
from app.directory.models import AddonCatalogueItem, DirectoryService, Society, WorkingSlot
from app.scheduling.models import SchedulingCrew

WEEKLY_OFF_WEEKDAY = 2  # Wednesday; Monday is 0 (the owner's default of 05-Nov-26)
NEW_MINUTES = 30
OLD_MINUTES = 20
DURATION_SERVICES = ("Cleaning-External", "Cleaning-Internal")
DURATION_ADDONS = ("Extra interior cleaning", "Special exterior cleaning")
BLOCK_START = "-----BEGIN CHANGES-----"
BLOCK_END = "-----END CHANGES-----"


@dataclass
class Change:
    table: str
    row_id: str
    label: str
    field: str
    old: object
    new: object


@dataclass
class Plan:
    changes: list[Change]
    skipped: list[str]


def find_site(db: Session, text: str) -> Society:
    """A society by exact name or by id."""
    try:
        by_id = db.get(Society, uuid.UUID(text))
    except ValueError:
        by_id = None
    site = by_id or db.scalar(select(Society).where(Society.name == text))
    if site is None:
        raise SystemExit(f"No site named or numbered {text!r}.")
    return site


def plan_site(db: Session, society: Society) -> Plan:
    changes: list[Change] = []
    skipped: list[str] = []
    slots = db.scalars(select(WorkingSlot).where(WorkingSlot.society_id == society.id)
                       .order_by(WorkingSlot.service, WorkingSlot.start_minute))
    for slot in slots:
        days = list(slot.days or [])
        if WEEKLY_OFF_WEEKDAY in days:
            new = [d for d in days if d != WEEKLY_OFF_WEEKDAY]
            changes.append(Change("working_slots", str(slot.id), slot.service, "days", days, new))
    crew = db.scalars(select(SchedulingCrew).where(SchedulingCrew.society_id == society.id)
                      .order_by(SchedulingCrew.id))
    for member in crew:
        hours = member.working_hours
        if not hours:
            skipped.append(f"crew {member.id}: no per-weekday hours, left alone")
            continue
        entry = hours[WEEKLY_OFF_WEEKDAY] if WEEKLY_OFF_WEEKDAY < len(hours) else None
        if entry and entry.get("working"):
            new_hours = [dict(h) for h in hours]
            new_hours[WEEKLY_OFF_WEEKDAY]["working"] = False
            changes.append(Change("scheduling_crew", str(member.id), f"crew {member.id}",
                                  "working_hours", hours, new_hours))
    return Plan(changes, skipped)


def plan_durations(db: Session) -> Plan:
    changes: list[Change] = []
    for svc in db.scalars(select(DirectoryService).where(
            DirectoryService.name.in_(DURATION_SERVICES)).order_by(DirectoryService.name)):
        if svc.duration_minutes == OLD_MINUTES:
            changes.append(Change("directory_services", str(svc.id), svc.name,
                                  "duration_minutes", OLD_MINUTES, NEW_MINUTES))
    for item in db.scalars(select(AddonCatalogueItem).where(
            AddonCatalogueItem.name.in_(DURATION_ADDONS)).order_by(AddonCatalogueItem.name)):
        if item.duration_minutes == OLD_MINUTES:
            changes.append(Change("addon_catalogue", str(item.id), item.name,
                                  "duration_minutes", OLD_MINUTES, NEW_MINUTES))
    return Plan(changes, [])


def _model(table: str):
    return {"working_slots": WorkingSlot, "scheduling_crew": SchedulingCrew,
            "directory_services": DirectoryService,
            "addon_catalogue": AddonCatalogueItem}[table]


def apply_changes(db: Session, changes: list[Change], reverse: bool = False) -> int:
    """Writes the new value (or, reversed, the old one). A row whose current value
    is not the expected one is left alone. Returns how many rows were written."""
    written = 0
    for c in changes:
        row = db.get(_model(c.table), uuid.UUID(c.row_id))
        expect, target = (c.new, c.old) if reverse else (c.old, c.new)
        if row is None or getattr(row, c.field) != expect:
            continue
        setattr(row, c.field, target)
        written += 1
    db.flush()
    lookup.invalidate(db)
    return written


def render(plan: Plan, apply: bool) -> str:
    lines = ["SAVED" if apply else "DRY RUN: nothing was saved"]
    for c in plan.changes:
        lines.append(f"{c.table} {c.label} {c.field}: {json.dumps(c.old)} -> {json.dumps(c.new)}")
    lines += [f"skipped: {s}" for s in plan.skipped]
    lines.append(f"changes: {len(plan.changes)}")
    lines += [BLOCK_START, json.dumps([asdict(c) for c in plan.changes]), BLOCK_END]
    return "\n".join(lines)


def read_printout(text: str) -> list[Change]:
    if BLOCK_START not in text or BLOCK_END not in text:
        raise SystemExit("That file has no changes block.")
    block = text.split(BLOCK_START, 1)[1].split(BLOCK_END, 1)[0]
    return [Change(**row) for row in json.loads(block)]


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    site = args[args.index("--site") + 1] if "--site" in args and args.index("--site") + 1 < len(args) else None
    revert = args[args.index("--revert") + 1] if "--revert" in args and args.index("--revert") + 1 < len(args) else None
    durations = "--durations" in args
    modes = [bool(site), durations, bool(revert)]
    if sum(modes) != 1 or "--help" in args:
        raise SystemExit(__doc__)
    from app.platform.db import get_engine
    engine = get_engine()
    print(f"Database: {engine.dialect.name}, host {engine.url.host or 'local file'}")
    with Session(engine) as db:
        if revert:
            plan = Plan(read_printout(Path(revert).read_text()), [])
            if apply:
                apply_changes(db, plan.changes, reverse=True)
                db.commit()
            print("REVERSE " + render(plan, apply))
            return
        plan = plan_durations(db) if durations else plan_site(db, find_site(db, site))
        if apply:
            apply_changes(db, plan.changes)
            db.commit()
        print(render(plan, apply))


if __name__ == "__main__":
    main()
