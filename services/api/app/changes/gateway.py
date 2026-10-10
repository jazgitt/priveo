"""What the changes module needs from the visits and jobs of the scheduling
slice. The scheduling slice implements this Protocol; until then an in-memory
stub stands in. Visits and jobs are never read or written here directly."""
import uuid
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import Protocol


@dataclass(frozen=True)
class ServiceDay:
    day: date
    # For example ("Cleaning-External", "Cleaning-Internal").
    services: tuple[str, ...]


class ScheduleChangeGateway(Protocol):
    def upcoming_days(self, vehicle_id: uuid.UUID, start: date, count: int) -> list[ServiceDay]:
        """The next `count` service days of the vehicle, from `start` on."""
        ...

    def is_frozen(self, vehicle_id: uuid.UUID, day: date) -> bool:
        """True when the schedule for `day` is frozen (a change is then only a request)."""
        ...

    def skip_day(self, vehicle_id: uuid.UUID, day: date) -> None: ...

    def unskip_day(self, vehicle_id: uuid.UUID, day: date) -> None: ...

    def pause_range(self, vehicle_id: uuid.UUID, start: date, end: date) -> int:
        """Pauses the visits from `start` to `end`. Returns how many visits were paused."""
        ...

    def resume_range(self, vehicle_id: uuid.UUID, start: date, end: date) -> int:
        """Puts back the visits from `start` to `end`. Returns how many were put back."""
        ...

    def set_cutoff(self, vehicle_id: uuid.UUID, day: date, cutoff: time) -> None: ...


@dataclass
class InMemoryScheduleChangeGateway:
    """A stand-in: every day has an exterior clean, and `interior_weekday`
    (Monday = 0) also has an interior clean. Remembers what it was told."""

    interior_weekday: int | None = 4
    frozen_days: set[date] = field(default_factory=set)
    skipped: set[tuple[uuid.UUID, date]] = field(default_factory=set)
    paused: set[tuple[uuid.UUID, date]] = field(default_factory=set)
    cutoffs: dict[tuple[uuid.UUID, date], time] = field(default_factory=dict)

    def upcoming_days(self, vehicle_id, start, count):
        days = []
        for i in range(count):
            d = start + timedelta(days=i)
            services = ["Cleaning-External"]
            if self.interior_weekday is not None and d.weekday() == self.interior_weekday:
                services.append("Cleaning-Internal")
            days.append(ServiceDay(d, tuple(services)))
        return days

    def is_frozen(self, vehicle_id, day):
        return day in self.frozen_days

    def skip_day(self, vehicle_id, day):
        self.skipped.add((vehicle_id, day))

    def unskip_day(self, vehicle_id, day):
        self.skipped.discard((vehicle_id, day))

    @staticmethod
    def _span(start, end):
        return [start + timedelta(days=i) for i in range((end - start).days + 1)]

    def pause_range(self, vehicle_id, start, end):
        days = self._span(start, end)
        self.paused.update((vehicle_id, d) for d in days)
        # Skipped days are taken into the pause (PAUSE-06).
        self.skipped -= {(vehicle_id, d) for d in days}
        return len(days)

    def resume_range(self, vehicle_id, start, end):
        days = self._span(start, end)
        self.paused -= {(vehicle_id, d) for d in days}
        return len(days)

    def set_cutoff(self, vehicle_id, day, cutoff):
        self.cutoffs[(vehicle_id, day)] = cutoff


_gateway: ScheduleChangeGateway = InMemoryScheduleChangeGateway()


def set_schedule_gateway(gateway: ScheduleChangeGateway) -> None:
    """Bound once at start-up, when the scheduling slice is wired in."""
    global _gateway
    _gateway = gateway


def get_schedule_gateway() -> ScheduleChangeGateway:
    return _gateway
