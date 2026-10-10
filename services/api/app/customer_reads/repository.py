"""How the customer reads see visits and jobs.

The `visits` and `jobs` tables belong to the crew slice. This module reads
them only through [VisitReadRepository]; the SQL implementation is bound at
integration (see `app.customer_reads.deps.get_visit_read_repository`).
"""
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

# Visit.status: Scheduled, In progress, Completed, Skipped, Missed.
# Job.status: Pending, In progress, Done, Skipped, Missed.
TERMINAL_VISIT_STATUSES = ("Completed", "Skipped", "Missed")


@dataclass(frozen=True)
class ProofItem:
    kind: str  # "photo" or "video"
    url: str


@dataclass(frozen=True)
class Job:
    id: str
    visit_id: str
    service: str  # Cleaning-External, Cleaning-Internal, Deep Spa
    status: str
    proof: list[ProofItem] = field(default_factory=list)


@dataclass(frozen=True)
class Visit:
    id: str
    vehicle_id: str
    date: date
    status: str


class VisitReadRepository(Protocol):
    def visits_in_range(self, vehicle_ids: Sequence[str], start: date,
                        end: date) -> list[Visit]:
        """Visits of these vehicles with start <= date <= end, oldest first."""
        ...

    def history(self, vehicle_ids: Sequence[str], statuses: Sequence[str],
                limit: int, offset: int) -> list[Visit]:
        """Visits of these vehicles in one of these statuses, newest first."""
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

    def history(self, vehicle_ids, statuses, limit, offset):
        wanted, kinds = set(vehicle_ids), set(statuses)
        rows = [v for v in self.visit_rows
                if v.vehicle_id in wanted and v.status in kinds]
        rows.sort(key=lambda v: (v.date, v.id), reverse=True)
        return rows[offset:offset + limit]

    def visit(self, visit_id):
        return next((v for v in self.visit_rows if v.id == visit_id), None)

    def jobs(self, visit_ids):
        wanted = set(visit_ids)
        return [j for j in self.job_rows if j.visit_id in wanted]
