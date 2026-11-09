"""The working slot a service has on a day (ADM-SVS-12, ADM-CAP-08, SCHR-PAR-02).

Capacity, the scheduler's demand and job windows, the Interior ledger and the
weekly off all read the slot through this module, so they cannot disagree. For
a service and a date the first rule that applies wins:

1. an exception for that service whose date range covers the date and whose
   `days` include the weekday. Its windows are the only slots the service has
   that day, and no windows means the service is closed that day. It can open a
   weekday the weekly off would close (decision 8, 9-Nov-26);
2. Root: the site's `working_slots` rows for the service on that weekday;
3. weekly off: the service has Root slots, but none on that weekday.

A service with no Root slot and no exception covering the date has source
"no_slots". The demand is not filtered for it (ADM-CAP-08) and it has no job
window (SCHR-PAR-16), as before this module existed.

Nothing here is hard-coded: the weekdays and times are the stored values.
"""
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory.models import WorkingSlot, WorkingSlotException

EXCEPTION = "exception"
ROOT = "root"
WEEKLY_OFF = "weekly_off"
NO_SLOTS = "no_slots"

Window = tuple[int, int]


@dataclass(frozen=True)
class RootSlot:
    service: str
    start_minute: int
    end_minute: int
    days: frozenset[int]


@dataclass(frozen=True)
class SlotException:
    service: str
    start_date: date
    end_date: date
    days: frozenset[int]
    windows: tuple[Window, ...]
    id: uuid.UUID | None = None


@dataclass(frozen=True)
class Effective:
    """The slot one service has on one day. `windows` are (start, end) minutes
    after midnight, sorted; empty means no work for that service that day."""

    service: str
    day: date
    source: str
    windows: tuple[Window, ...]
    exception_id: uuid.UUID | None = None

    @property
    def open(self) -> bool:
        return bool(self.windows)


def _sorted(spans: Iterable[Window]) -> tuple[Window, ...]:
    return tuple(sorted((s, e) for s, e in spans if e > s))


class SiteSlots:
    """The Root slots and the exceptions of one site, held in memory. Load it
    once with `load` and ask it for each day; no query runs per question."""

    def __init__(self, root: Iterable[RootSlot], exceptions: Iterable[SlotException]):
        self.root = tuple(root)
        self.exceptions = tuple(exceptions)

    def services(self) -> set[str]:
        """Every service the site has Root slots or exceptions for."""
        return {r.service for r in self.root} | {x.service for x in self.exceptions}

    def effective(self, service: str, day: date) -> Effective:
        weekday = day.weekday()
        for ex in self.exceptions:
            if (ex.service == service and ex.start_date <= day <= ex.end_date
                    and weekday in ex.days):
                return Effective(service, day, EXCEPTION, _sorted(ex.windows), ex.id)
        mine = [r for r in self.root if r.service == service]
        if not mine:
            return Effective(service, day, NO_SLOTS, ())
        spans = _sorted((r.start_minute, r.end_minute) for r in mine if weekday in r.days)
        return Effective(service, day, ROOT if spans else WEEKLY_OFF, spans)

    def closed(self, day: date) -> bool:
        """The site's weekly off (SCHR-PAR-02, SCHR-PAR-16): the site has Root
        slots and no service is open on the day, exceptions included. A site
        with no Root slots has no weekly off."""
        if not self.root:
            return False
        return not any(self.effective(s, day).open for s in self.services())

    def allows_demand(self, service: str, day: date) -> bool:
        """Whether demand for the service on the day is kept (ADM-CAP-08)."""
        eff = self.effective(service, day)
        return eff.source == NO_SLOTS or eff.open


def load(db: Session, society_id: uuid.UUID) -> SiteSlots:
    """The site's Root slots and exceptions, read once."""
    root = [
        RootSlot(row.service, row.start_minute, row.end_minute,
                 frozenset(int(d) for d in row.days))
        for row in db.scalars(select(WorkingSlot).where(WorkingSlot.society_id == society_id))
    ]
    exceptions = [
        SlotException(
            service=row.service,
            start_date=row.start_date,
            end_date=row.end_date,
            days=frozenset(int(d) for d in row.days or []),
            windows=tuple((int(w["start_minute"]), int(w["end_minute"]))
                          for w in row.windows or []),
            id=row.id,
        )
        for row in db.scalars(
            select(WorkingSlotException)
            .where(WorkingSlotException.society_id == society_id)
            .order_by(WorkingSlotException.start_date, WorkingSlotException.service)
        )
    ]
    return SiteSlots(root, exceptions)


def effective(db: Session, society_id: uuid.UUID, service: str, day: date) -> Effective:
    """The slot one service has on one day, for a caller that asks once."""
    return load(db, society_id).effective(service, day)
