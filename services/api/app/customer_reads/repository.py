"""How the customer reads see visits and jobs.

The `visits` and `jobs` tables belong to the crew slice. This module reads
them only through [VisitReadRepository]; the SQL implementation is bound at
integration (see `app.customer_reads.deps.get_visit_read_repository`).
"""
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol

# Visit.status: Scheduled, In progress, Completed, Skipped, Missed.
# Job.status: Pending, In progress, Done, Skipped, Missed.
TERMINAL_VISIT_STATUSES = ("Completed", "Skipped", "Missed")


@dataclass(frozen=True)
class ProofItem:
    kind: str  # "photo" or "video"
    url: str
    stage: str | None = None  # Before, During or After
    taken_at: datetime | None = None
    id: str | None = None


@dataclass(frozen=True)
class ChecklistEntry:
    key: str
    label: str
    checked_at: datetime | None = None


@dataclass(frozen=True)
class Job:
    id: str
    visit_id: str
    service: str  # Cleaning-External, Cleaning-Internal, Deep Spa
    status: str
    proof: list[ProofItem] = field(default_factory=list)
    # The crew member's first name only. Never a mobile number (SVC-02).
    crew_name: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    checklist: list[ChecklistEntry] = field(default_factory=list)
    # The assignment (CAL-10). Empty until the admin or the scheduler placed it.
    start_minute: int | None = None
    duration_minutes: int = 0
    # The cutoff time of the job, in minutes after midnight.
    finish_by_minute: int | None = None
    addon_request_id: str | None = None
    source_job_id: str | None = None


@dataclass(frozen=True)
class Visit:
    id: str
    vehicle_id: str
    date: date
    status: str
    # True when the schedule the visit belongs to is frozen (CAL-07, CAL-10).
    frozen: bool = False


class VisitReadRepository(Protocol):
    def visits_in_range(self, vehicle_ids: Sequence[str], start: date,
                        end: date) -> list[Visit]:
        """Visits of these vehicles with start <= date <= end, oldest first."""
        ...

    def history(self, vehicle_ids: Sequence[str], statuses: Sequence[str],
                limit: int, offset: int, start: date | None = None,
                end: date | None = None) -> list[Visit]:
        """Visits of these vehicles in one of these statuses, newest first.
        `start` and `end` limit them to a date range (HIST-02)."""
        ...

    def visit(self, visit_id: str) -> Visit | None: ...

    def jobs(self, visit_ids: Sequence[str]) -> list[Job]:
        """The jobs of these visits, in the order they are done."""
        ...


class InMemoryVisitReadRepository:
    """For tests, and for a deployment where the crew tables are not bound."""

    def __init__(self, visits: Sequence[Visit] = (), jobs: Sequence[Job] = ()):
        self.visit_rows = list(visits)
        self.job_rows = list(jobs)

    def visits_in_range(self, vehicle_ids, start, end):
        wanted = set(vehicle_ids)
        rows = [v for v in self.visit_rows
                if v.vehicle_id in wanted and start <= v.date <= end]
        return sorted(rows, key=lambda v: (v.date, v.id))

    def history(self, vehicle_ids, statuses, limit, offset, start=None, end=None):
        wanted, kinds = set(vehicle_ids), set(statuses)
        rows = [v for v in self.visit_rows
                if v.vehicle_id in wanted and v.status in kinds
                and (start is None or v.date >= start) and (end is None or v.date <= end)]
        rows.sort(key=lambda v: (v.date, v.id), reverse=True)
        return rows[offset:offset + limit]

    def visit(self, visit_id):
        return next((v for v in self.visit_rows if v.id == visit_id), None)

    def jobs(self, visit_ids):
        wanted = set(visit_ids)
        return [j for j in self.job_rows if j.visit_id in wanted]
