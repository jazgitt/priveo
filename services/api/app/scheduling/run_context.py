"""The run context: what one `run_schedule` call knows and records (SCHS-06).

At `scheduler.rules_version` 2 the context reads every scheduler setting of the
site once, through the site-settings lookup, and keeps it as `settings`. `save`
stores that snapshot in `schedule_run_config` (SCHR-CFG-08) and the findings the
hooks collected in `schedule_findings`. Handlers read values from the snapshot
and never from the database, so a run uses one consistent set of values and a
later change of a setting touches no stored snapshot (SCHR-CFG-07).

At version 1 nothing is read beyond the version and nothing is stored, so the
old behaviour and its data stay as they are. A missing version setting counts
as 1.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.scheduling import hand_placement, hooks
from app.scheduling.models import Schedule, ScheduleFinding, ScheduleRunConfig


def _plain(value: Any) -> Any:
    """A value that can be stored as JSON."""
    if isinstance(value, (set, frozenset, tuple, list)):
        return [_plain(v) for v in (sorted(value) if isinstance(value, (set, frozenset)) else value)]
    return value


@dataclass
class RunContext:
    db: Session
    schedule: Schedule
    admin_id: uuid.UUID | None
    frozen: bool
    rules_version: int
    settings: dict[str, Any] = field(default_factory=dict)
    findings: list[dict] = field(default_factory=list)

    @property
    def society_id(self) -> uuid.UUID:
        return self.schedule.society_id

    @property
    def active(self) -> bool:
        """True when the new rules apply; the hooks run only then."""
        return self.rules_version == 2

    def setting(self, key: str) -> Any:
        """A value of the snapshot. KeyError when the run is not on version 2."""
        return self.settings[key]

    def add_finding(self, code: str, detail: str = "", job_id: uuid.UUID | None = None) -> None:
        self.findings.append({"code": code, "detail": detail, "job_id": job_id})

    def save(self) -> None:
        """Write the snapshot and the findings. Does not commit."""
        if not self.active:
            return
        self.db.add(ScheduleRunConfig(schedule_id=self.schedule.id, values=dict(self.settings)))
        # The findings describe the plan as this run left it.
        # Breaches of a hand placement stay: the placement is kept by a re-run (SCHS-22).
        self.db.execute(delete(ScheduleFinding).where(
            ScheduleFinding.schedule_id == self.schedule.id,
            ~ScheduleFinding.code.like(hand_placement.PREFIX + "%")))
        for item in self.findings:
            self.db.add(ScheduleFinding(schedule_id=self.schedule.id, job_id=item["job_id"],
                                        code=item["code"], detail=item["detail"]))
        self.db.flush()


def start(db: Session, schedule: Schedule, admin_id: uuid.UUID | None) -> RunContext:
    from app.directory import lookup

    version = hooks._version(db, schedule.society_id)
    settings: dict[str, Any] = {}
    if version == 2:
        settings = {k: _plain(v) for k, v in lookup.site_settings_all(db, schedule.society_id).items()}
    return RunContext(db=db, schedule=schedule, admin_id=admin_id,
                      frozen=schedule.status == "Frozen", rules_version=version, settings=settings)
