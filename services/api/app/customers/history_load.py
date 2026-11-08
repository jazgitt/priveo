"""Load the service history up to 3 Nov 2026 from the owner's "calendar" sheet
(workbook v4.1) as live history: each day becomes a visit with its jobs and, for
an Interior, its entitlement (see `history_convert`). The days are live and
actual, the same as work done in the app.

The sheet has one row for each vehicle (column B is the car number, the link to
the database) and one column for each day from 14 Sep to 3 Nov 2026. A cell says:

  ext             Exterior was done
  int,ext         Exterior and Interior were done
  skipped         the day was skipped, no reason
  skipped - rain  the day was skipped, reason Rain
  empty           nothing recorded

Owner's rules (3-4 Nov 2026):
- a plain "skipped" on 28 Oct is a Weekly off, and 21 Oct (which has no column)
  is a Weekly off for every vehicle that had started by then;
- an empty cell before the vehicle's first record is "not started yet" and is
  only counted; an empty cell after it is not loaded and is reported, except
  the cells the owner filled in by instruction, which come from a small file
  (`--fills`, see `read_fills`) kept out of the repository;
- any other text in a day cell is ignored but reported.

It can run again: a vehicle and day that is already loaded is left as it is. A
day that already has a completed or other non-scheduled visit from the app is not
loaded and is reported.

From a start day (`since`, 9 Nov 2026 on: columns 4 to 7 Nov) the sheet is the
status of the day: a day with a Scheduled plan visit takes the sheet's status
(see `history_convert.apply_status`), a day without a visit is written as live
history, an empty cell means nothing was recorded and is counted, and a Scheduled
visit with no sheet entry is listed in `report.scheduled_without_entry`. No
notification is sent for any of it.

Every cell that is not loaded is listed in `report.not_loaded` with the reason.
The console report holds counts only; the lists (with car numbers) go to CSV files
the caller writes.
"""
import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.history_convert import (
    LIVE,
    WEEKLY_OFF,
    admin_login_id,
    apply_status,
    parse_cell,
    write_record,
)
from app.customers.importer import _compact, _text
from app.customers.models import Vehicle
from app.scheduling.models import Job, Visit

SHEET = "calendar"
LAST_DAY = date(2026, 11, 3)
WEEKLY_OFF_DAYS = (date(2026, 10, 21), date(2026, 10, 28))
EXTERIOR, BOTH = "Exterior", "Exterior + Interior"

R_NO_VEHICLE = "car number is not in the database"
R_BLANK_AFTER_START = "empty cell after the vehicle started"
R_NOT_A_VALUE = "cell is not a service value"
R_LIVE_VISIT = "a live visit already exists that day"


@dataclass
class NotLoaded:
    sheet_row: int
    day: date
    cell: str
    reason: str
    car_number: str


@dataclass
class HistoryReport:
    vehicles_in_sheet: int = 0
    vehicles_matched: int = 0
    to_load: int = 0            # new rows (saved only with apply)
    completed: int = 0
    skipped: int = 0
    already_loaded: int = 0     # days converted by an earlier run
    before_start: int = 0       # empty cells before the vehicle's first record
    owner_fills: int = 0
    weekly_off: int = 0         # weekly-off days: counted, no visit is written (owner rule)
    no_entry: int = 0           # empty cells in the window: nothing recorded, counted only
    updated: Counter = field(default_factory=Counter)   # scheduled visits set to the sheet's status
    updated_jobs: Counter = field(default_factory=Counter)  # the job statuses written
    not_loaded: list[NotLoaded] = field(default_factory=list)
    # Scheduled plan visits in the window that the sheet does not cover: (car, day, visit id).
    scheduled_without_entry: list[tuple[str, date, str]] = field(default_factory=list)

    def reasons(self) -> Counter:
        return Counter(n.reason for n in self.not_loaded)


def _classify(value) -> tuple[str, str, str] | None:
    """(services, outcome, reason) for a recognised cell, or None."""
    return parse_cell(_text(value))


def read_fills(path: str | Path) -> dict[tuple[str, date], str]:
    """The owner's fill-ins for empty cells: a CSV with the columns car_number,
    day (YYYY-MM-DD) and value (ext, int,ext, skipped or skipped - rain). Keep the
    file out of the repository: it holds car numbers."""
    fills: dict[tuple[str, date], str] = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            try:
                key = (_compact(row["car_number"]), date.fromisoformat(_text(row["day"])))
            except (KeyError, ValueError) as problem:
                raise ValueError(f"Fills file, line {line}: need car_number and day as YYYY-MM-DD.") from problem
            value = _text(row.get("value"))
            if _classify(value) is None:
                raise ValueError(
                    f"Fills file, line {line}: the value must be ext, int,ext, or skipped (with an optional reason).")
            fills[key] = value
    return fills


def load_service_history(db: Session, path: str | Path, *, apply: bool,
                         fills: dict[tuple[str, date], str] | None = None,
                         through: date = LAST_DAY, since: date | None = None) -> HistoryReport:
    """Load the sheet's day columns up to and including `through`. With `since`, only
    the columns from that day on are read, in status mode (see the module notes)."""
    book = load_workbook(path, data_only=True, read_only=True)
    if SHEET not in book.sheetnames:
        raise ValueError(f'The workbook has no "{SHEET}" sheet.')
    rows = list(book[SHEET].iter_rows(values_only=True))
    book.close()
    if not rows:
        raise ValueError("The calendar sheet is empty.")
    header = rows[0]
    day_cols = [(i, h.date()) for i, h in enumerate(header)
                if isinstance(h, datetime) and h.date() <= through
                and (since is None or h.date() >= since)]
    if not day_cols:
        raise ValueError("The calendar sheet has no date columns.")
    columns = {d for _, d in day_cols}

    vehicles = {_compact(r): vid for r, vid in db.execute(
        select(Vehicle.registration, Vehicle.id).where(Vehicle.registration.is_not(None)))}
    # Visits made by an earlier run of this load carry the legacy marker on their jobs.
    converted = {(vid, d) for vid, d, snap in db.execute(
        select(Visit.vehicle_id, Visit.date, Job.checklist_snapshot)
        .join(Job, Job.visit_id == Visit.id)) if snap and snap.get("legacy")}
    scheduled: dict[tuple, Visit] = {}
    live_days = set()
    for visit in db.scalars(select(Visit)):
        key = (visit.vehicle_id, visit.date)
        if key in converted:
            continue
        in_window = (since is None or visit.date >= since) and visit.date <= through
        if visit.status == "Scheduled" and visit.addon_key == "" and in_window:
            scheduled[key] = visit
        else:
            live_days.add(key)
    admin = admin_login_id(db)

    report = HistoryReport()
    seen: set[tuple] = set()
    handled: set[tuple] = set()

    def add(vid, row_no, day, cell, car, services, outcome, reason):
        key = (vid, day)
        if reason == WEEKLY_OFF:
            report.weekly_off += 1  # no visit: a weekly off is not work (owner rule)
            return
        if key in converted or key in seen:
            report.already_loaded += 1
            return
        if key in scheduled:
            seen.add(key)
            handled.add(key)
            report.updated[outcome] += 1
            report.updated_jobs.update(apply_status(
                db, scheduled[key], services, outcome, reason, admin))
            return
        if key in live_days:
            report.not_loaded.append(NotLoaded(row_no, day, cell, R_LIVE_VISIT, car))
            return
        seen.add(key)
        report.to_load += 1
        report.completed += outcome == "Completed"
        report.skipped += outcome == "Skipped"
        if apply:
            result = write_record(db, db.get(Vehicle, vid), day, services=services, outcome=outcome,
                                  skip_reason=reason, admin_id=admin)
            if result == LIVE:  # written by another path after the check above
                report.not_loaded.append(NotLoaded(row_no, day, cell, R_LIVE_VISIT, car))
                report.to_load -= 1
                report.completed -= outcome == "Completed"
                report.skipped -= outcome == "Skipped"

    for offset, row in enumerate(rows[1:], start=2):
        car = _compact(row[1]) if len(row) > 1 else ""
        if not car:
            continue
        report.vehicles_in_sheet += 1
        vid = vehicles.get(car)
        if vid:
            report.vehicles_matched += 1
        cells: dict[date, object] = {d: (row[i] if i < len(row) else None) for i, d in day_cols}
        for (reg, day), value in (fills or {}).items():
            if reg == car and day in cells and _text(cells[day]) == "":
                cells[day] = value
                report.owner_fills += 1
        parsed = {d: _classify(v) for d, v in cells.items()}
        starts = [d for d in sorted(cells) if parsed[d]]
        first = starts[0] if starts else None

        for day in sorted(cells):
            raw = _text(cells[day])
            got = parsed[day]
            if got and day in WEEKLY_OFF_DAYS and got[1] == "Skipped" and not got[2]:
                got = (got[0], got[1], WEEKLY_OFF)
            if got is None and raw == "" and since is not None:
                report.no_entry += 1  # status mode: an empty cell records nothing
                continue
            if got is None and raw == "":
                if first is None or day < first:
                    report.before_start += 1
                    continue
                report.not_loaded.append(NotLoaded(offset, day, "", R_BLANK_AFTER_START, car))
                continue
            if got is None:
                report.not_loaded.append(NotLoaded(offset, day, raw, R_NOT_A_VALUE, car))
                continue
            if vid is None:
                report.not_loaded.append(NotLoaded(offset, day, raw, R_NO_VEHICLE, car))
                continue
            add(vid, offset, day, raw, car, *got)

        # A weekly-off day that has no column: skipped for every vehicle that had started.
        for off_day in WEEKLY_OFF_DAYS:
            if off_day in columns or first is None or first >= off_day:
                continue
            if since is not None and off_day < since:
                continue
            if vid is None:
                report.not_loaded.append(NotLoaded(offset, off_day, "(no column)", R_NO_VEHICLE, car))
                continue
            add(vid, offset, off_day, "(no column)", car, "", "Skipped", WEEKLY_OFF)

    for key, visit in scheduled.items():
        if key not in handled:
            reg = db.get(Vehicle, key[0]).registration or ""
            report.scheduled_without_entry.append((reg, key[1], str(visit.id)))

    if apply:
        db.commit()
    else:
        db.rollback()  # a trial run changes nothing, including the scheduled visits
    return report
