"""Break rules: which break a cleaner has on a date (SCHR-PAR-09, SCHR-BRK-06,
SCHR-BRK-07, SCHR-BRK-10).

Lookup only: nothing plans around a break yet. The break comes from the first
rule that applies, most specific first (owner, 05-Nov-26):

    date and crew -> date -> crew -> site default

A "date" rule has a date range; a "crew" rule has none. A rule without minutes
uses the site break; a rule that is switched off means no break. The site
default comes from the `site.break_*` settings, never from code. A cleaner whose
working windows on the date do not cover the break has no break (SCHR-BRK-07).
"""
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory import site_settings
from app.directory.service import audit
from app.platform.errors import ApiError
from app.scheduling import windows
from app.scheduling.models import BreakRule, Job, Schedule, SchedulingCrew, Visit

# A rule with no date range is stored over the widest range the column holds.
OPEN_START, OPEN_END = date.min, date.max
# Jobs in these states have not started, so a changed break may still move them.
NOT_STARTED = ("Scheduled",)


@dataclass(frozen=True)
class Break:
    start_minute: int
    end_minute: int
    source: str  # date_crew | date | crew | site


def is_open(rule: BreakRule) -> bool:
    return rule.start_date == OPEN_START and rule.end_date == OPEN_END


def source_of(rule: BreakRule) -> str:
    dated = not is_open(rule)
    if rule.crew_id is not None:
        return "date_crew" if dated else "crew"
    return "date"


_RANK = {"date_crew": 0, "date": 1, "crew": 2}


def affects_job(status: str) -> bool:
    """A break change reaches only a job that has not started (SCHR-BRK-10)."""
    return status in NOT_STARTED


def _site_break(db: Session, society_id: uuid.UUID) -> tuple[int, int]:
    return (site_settings.read(db, society_id, "site.break_start_minute"),
            site_settings.read(db, society_id, "site.break_end_minute"))


def matching_rule(db: Session, society_id: uuid.UUID, crew_id: uuid.UUID | None,
                  day: date) -> BreakRule | None:
    """The most specific rule that applies, or None to use the site default.
    Among rules of the same kind the newest wins."""
    rows = db.scalars(select(BreakRule).where(
        BreakRule.society_id == society_id,
        BreakRule.start_date <= day, BreakRule.end_date >= day,
        (BreakRule.crew_id.is_(None)) | (BreakRule.crew_id == crew_id)))
    ranked = [r for r in rows if r.crew_id is None or r.crew_id == crew_id]
    # A site-wide rule with no dates would be the site default itself; it is not stored.
    ranked = [r for r in ranked if not (r.crew_id is None and is_open(r))]
    if not ranked:
        return None
    return min(ranked, key=lambda r: (_RANK[source_of(r)], -r.created_at.timestamp(), str(r.id)))


def effective_break(db: Session, crew: SchedulingCrew, day: date) -> Break | None:
    """The cleaner's break on `day`, or None (no break set, switched off, or the
    cleaner's windows do not cover it)."""
    rule = matching_rule(db, crew.society_id, crew.id, day)
    if rule is not None:
        if not rule.enabled:
            return None
        start, end = ((rule.start_minute, rule.end_minute) if rule.start_minute is not None
                      else _site_break(db, crew.society_id))
        found = Break(start, end, source_of(rule))
    else:
        if not site_settings.read(db, crew.society_id, "site.break_enabled"):
            return None
        found = Break(*_site_break(db, crew.society_id), "site")
    day_windows = windows.cleaner_windows(db, {crew.id: crew}, [day])[day].get(crew.id, [])
    if not any(s <= found.start_minute and e >= found.end_minute for s, e in day_windows):
        return None
    return found


# ---- changes (admin) -----------------------------------------------------------


def _invalid(field: str, message: str) -> ApiError:
    return ApiError("validation_failed", "Please check the details.", 422, {field: message})


def _check(db, society_id, crew_id, start_date, end_date, start_minute, end_minute) -> None:
    if (start_date is None) != (end_date is None):
        raise _invalid("end_date", "Give both dates, or neither.")
    if start_date is not None and end_date < start_date:
        raise _invalid("end_date", "The end date cannot be before the start date.")
    if (start_minute is None) != (end_minute is None):
        raise _invalid("end_minute", "Give both break times, or neither.")
    if start_minute is not None:
        if not (0 <= start_minute < end_minute <= 1439):
            raise _invalid("end_minute", "The break must end after it starts, within one day.")
    if crew_id is not None:
        crew = db.get(SchedulingCrew, crew_id)
        if crew is None or crew.society_id != society_id:
            raise ApiError("not_found", "This crew member was not found at this site.", 404)


def frozen_impact(db: Session, society_id: uuid.UUID, crew_id: uuid.UUID | None,
                  start: date, end: date) -> dict:
    """Frozen dates in the range and how many jobs a change reaches (not started)
    or leaves alone (started or finished) (SCHR-BRK-10)."""
    query = (select(Visit.date, Job.status, Job.crew_id)
             .join(Visit, Visit.id == Job.visit_id)
             .join(Schedule, Schedule.id == Visit.schedule_id)
             .where(Schedule.society_id == society_id, Schedule.status == "Frozen",
                    Visit.date >= start, Visit.date <= end, Job.crew_id.is_not(None)))
    if crew_id is not None:
        query = query.where(Job.crew_id == crew_id)
    rows = db.execute(query).all()
    dates = sorted({d for d, _, _ in rows})
    affected = sum(1 for _, status, _ in rows if affects_job(status))
    return {"frozen_dates": [d.isoformat() for d in dates], "jobs_affected": affected,
            "jobs_not_affected": len(rows) - affected}


def _snapshot(rule: BreakRule) -> dict:
    return {"crew_id": str(rule.crew_id) if rule.crew_id else None,
            "start_date": None if is_open(rule) else rule.start_date.isoformat(),
            "end_date": None if is_open(rule) else rule.end_date.isoformat(),
            "start_minute": rule.start_minute, "end_minute": rule.end_minute,
            "enabled": rule.enabled}


def _audit(db, admin_id, rule: BreakRule, action: str, detail: dict) -> None:
    impact = frozen_impact(db, rule.society_id, rule.crew_id, rule.start_date, rule.end_date)
    audit(db, admin_id, "break_rule", rule.id, action,
          {"society_id": str(rule.society_id), **detail, **impact})


def save_rule(db: Session, admin_id, society_id: uuid.UUID, *, crew_id=None, start_date=None,
              end_date=None, start_minute=None, end_minute=None, enabled=True) -> BreakRule:
    _check(db, society_id, crew_id, start_date, end_date, start_minute, end_minute)
    if crew_id is None and start_date is None:
        raise _invalid("start_date", "Give a date range, or a crew member. "
                                     "The site break is set in the site settings.")
    rule = BreakRule(society_id=society_id, crew_id=crew_id,
                     start_date=start_date or OPEN_START, end_date=end_date or OPEN_END,
                     start_minute=start_minute, end_minute=end_minute, enabled=enabled,
                     created_by=admin_id)
    db.add(rule)
    db.flush()
    _audit(db, admin_id, rule, "create", _snapshot(rule))
    db.commit()
    return rule


def get_rule(db: Session, rule_id: uuid.UUID) -> BreakRule:
    rule = db.get(BreakRule, rule_id)
    if rule is None:
        raise ApiError("not_found", "This break rule was not found.", 404)
    return rule


def update_rule(db: Session, admin_id, rule: BreakRule, changes: dict) -> BreakRule:
    """Apply the given fields (start_date, end_date, start_minute, end_minute,
    enabled; null clears a field). The crew member does not change."""
    now = _snapshot(rule)
    merged = {**now, **{k: (v.isoformat() if isinstance(v, date) else v) for k, v in changes.items()}}
    _check(db, rule.society_id, rule.crew_id,
           date.fromisoformat(merged["start_date"]) if merged["start_date"] else None,
           date.fromisoformat(merged["end_date"]) if merged["end_date"] else None,
           merged["start_minute"], merged["end_minute"])
    if rule.crew_id is None and merged["start_date"] is None:
        raise _invalid("start_date", "A site-wide break rule needs a date range.")
    rule.start_date = date.fromisoformat(merged["start_date"]) if merged["start_date"] else OPEN_START
    rule.end_date = date.fromisoformat(merged["end_date"]) if merged["end_date"] else OPEN_END
    rule.start_minute, rule.end_minute = merged["start_minute"], merged["end_minute"]
    rule.enabled = merged["enabled"]
    after = _snapshot(rule)
    diff = {k: [now[k], after[k]] for k in now if now[k] != after[k]}
    if diff:
        _audit(db, admin_id, rule, "update", diff)
    db.commit()
    return rule


def delete_rule(db: Session, admin_id, rule: BreakRule) -> None:
    _audit(db, admin_id, rule, "delete", _snapshot(rule))
    db.delete(rule)
    db.commit()
