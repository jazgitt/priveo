"""A subscription's schedule pattern, Weekly or Cycle (S-02, S-03, ADM-SCH-41).

The scheduler (`scheduling.service.build_demand`) and the calendar projection
(`changes.projection.day_services`) both ask `day_flags`, so they cannot drift
apart. A subscription with no pattern keeps the default and never reaches this
module's rules: Exterior every day and Interior on the interior care day.

DERIVED details (the owner gave the intent): an Interior weekday is also an
Exterior weekday; Cycle day numbers count from the cycle's first day, which
moves with paused days as the billing cycle does (PAUSE-02); the counts must
match the days chosen."""
import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.cycle import shift_days
from app.customers.models import WEEKDAYS, SchedulePattern, Subscription
from app.directory import lookup
from app.directory.models import DirectoryAudit, Plan
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError

admin = APIRouter(prefix="/v1/admin", tags=["customer-administration"])

EXTERIOR = "Cleaning-External"
INTERIOR = "Cleaning-Internal"
_MEMO = "_schedule_pattern_memo"


def patterns_for(db: Session, subscription_ids: list[uuid.UUID]) -> dict[uuid.UUID, SchedulePattern]:
    if not subscription_ids:
        return {}
    return {p.subscription_id: p for p in db.scalars(
        select(SchedulePattern).where(SchedulePattern.subscription_id.in_(subscription_ids)))}


def pattern_of(db: Session, sub: Subscription) -> SchedulePattern | None:
    """The subscription's pattern, read once for the life of this object."""
    if _MEMO not in sub.__dict__:
        sub.__dict__[_MEMO] = db.scalar(
            select(SchedulePattern).where(SchedulePattern.subscription_id == sub.id))
    return sub.__dict__[_MEMO]


def forget(sub: Subscription) -> None:
    sub.__dict__.pop(_MEMO, None)


def anchor(db: Session, sub: Subscription, pattern: SchedulePattern) -> tuple[date, int]:
    """(the first day of cycle 1, the cycle length). Read once for the pattern object."""
    if "_anchor" not in pattern.__dict__:
        pattern.__dict__["_anchor"] = (
            sub.first_service_date + timedelta(days=shift_days(db, sub.vehicle_id)),
            lookup.setting(db, "billing.cycle_days"))
    return pattern.__dict__["_anchor"]


def day_flags(db: Session, sub: Subscription, pattern: SchedulePattern, day: date) -> tuple[bool, bool]:
    """(Exterior due, Interior due) on `day`. Interior implies Exterior."""
    if pattern.kind == "Weekly":
        name = WEEKDAYS[day.weekday()]
        interior = name in pattern.interior_weekdays
        return interior or name in pattern.exterior_weekdays, interior
    start, length = anchor(db, sub, pattern)
    number = (day - start).days % length + 1
    combined = number in pattern.combined_days
    return combined or number in pattern.exterior_days, combined


class PatternIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    exterior_weekdays: list[str] = []
    interior_weekdays: list[str] = []
    exterior_days: list[int] = []
    combined_days: list[int] = []
    # Optional. When given they must match the days chosen.
    exterior_count: int | None = None
    combined_count: int | None = None


def _sub(db: Session, subscription_id: uuid.UUID) -> Subscription:
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise ApiError("not_found", "Subscription not found.", 404)
    return sub


def _bad(message: str):
    raise ApiError("validation_failed", message, 422)


def _validated(db: Session, sub: Subscription, body: PatternIn) -> dict:
    if body.kind not in ("Weekly", "Cycle"):
        _bad("Choose a Weekly or a Cycle pattern.")
    plan = db.get(Plan, sub.pending_plan_id or sub.plan_id) if (sub.pending_plan_id or sub.plan_id) else None
    interior_ok = plan is None or plan.includes_interior
    if body.kind == "Weekly":
        for name in (*body.exterior_weekdays, *body.interior_weekdays):
            if name not in WEEKDAYS:
                _bad(f"{name} is not a weekday.")
        exterior = [d for d in WEEKDAYS if d in body.exterior_weekdays]
        interior = [d for d in WEEKDAYS if d in body.interior_weekdays]
        if not exterior:
            _bad("Choose at least one Exterior weekday.")
        if any(d not in exterior for d in interior):
            _bad("An Interior weekday must also be an Exterior weekday.")
        if interior and not interior_ok:
            _bad("The plan does not include interior care.")
        return {"kind": "Weekly", "exterior_weekdays": exterior, "interior_weekdays": interior,
                "exterior_days": [], "combined_days": []}
    length = lookup.setting(db, "billing.cycle_days")
    only, combined = sorted(set(body.exterior_days)), sorted(set(body.combined_days))
    if len(only) != len(body.exterior_days) or len(combined) != len(body.combined_days):
        _bad("A day number is listed twice.")
    if any(n < 1 or n > length for n in (*only, *combined)):
        _bad(f"Day numbers run from 1 to {length}.")
    if set(only) & set(combined):
        _bad("A day cannot be both Exterior only and Exterior + Interior.")
    if not only and not combined:
        _bad("Choose at least one day.")
    if body.exterior_count is not None and body.exterior_count != len(only):
        _bad(f"The Exterior-only count is {body.exterior_count} but {len(only)} days are chosen.")
    if body.combined_count is not None and body.combined_count != len(combined):
        _bad(f"The Exterior + Interior count is {body.combined_count} but {len(combined)} days are chosen.")
    if combined and not interior_ok:
        _bad("The plan does not include interior care.")
    return {"kind": "Cycle", "exterior_weekdays": [], "interior_weekdays": [],
            "exterior_days": only, "combined_days": combined}


def _view(db: Session, sub: Subscription, pattern: SchedulePattern | None) -> dict:
    out = {
        "kind": pattern.kind if pattern else "Default",
        "exterior_weekdays": pattern.exterior_weekdays if pattern else [],
        "interior_weekdays": pattern.interior_weekdays if pattern else [],
        "exterior_days": pattern.exterior_days if pattern else [],
        "combined_days": pattern.combined_days if pattern else [],
        "cycle_days": lookup.setting(db, "billing.cycle_days"),
        "default_interior_day": sub.interior_day,
    }
    if pattern is None:
        out["exterior_count"] = out["combined_count"] = None
    elif pattern.kind == "Cycle":
        out["exterior_count"], out["combined_count"] = len(pattern.exterior_days), len(pattern.combined_days)
    else:  # per week
        out["exterior_count"] = len(pattern.exterior_weekdays) - len(pattern.interior_weekdays)
        out["combined_count"] = len(pattern.interior_weekdays)
    return out


@admin.get("/subscriptions/{subscription_id}/schedule-pattern")
def read_pattern(subscription_id: uuid.UUID, user: User = Depends(require_role("admin")),
                 db: Session = Depends(get_db)):
    sub = _sub(db, subscription_id)
    return _view(db, sub, pattern_of(db, sub))


@admin.put("/subscriptions/{subscription_id}/schedule-pattern")
def set_pattern(subscription_id: uuid.UUID, body: PatternIn,
                user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    sub = _sub(db, subscription_id)
    fields = _validated(db, sub, body)
    pattern = pattern_of(db, sub)
    before = _view(db, sub, pattern)
    if pattern is None:
        pattern = SchedulePattern(subscription_id=sub.id, created_by=user.id, **fields)
        db.add(pattern)
    else:
        for k, v in fields.items():
            setattr(pattern, k, v)
        pattern.__dict__.pop("_anchor", None)
    db.flush()
    forget(sub)
    after = _view(db, sub, pattern)
    db.add(DirectoryAudit(
        admin_login_id=user.id, entity="subscription", entity_id=str(sub.id), action="update",
        detail={"schedule_pattern": [before["kind"], after["kind"]], "after": after}))
    db.commit()
    _reconcile(db, sub)
    return after


@admin.delete("/subscriptions/{subscription_id}/schedule-pattern", status_code=204)
def clear_pattern(subscription_id: uuid.UUID, user: User = Depends(require_role("admin")),
                  db: Session = Depends(get_db)):
    """Back to the default: Exterior every day, Interior on the interior care day."""
    sub = _sub(db, subscription_id)
    pattern = pattern_of(db, sub)
    if pattern is None:
        return
    db.delete(pattern)
    forget(sub)
    db.add(DirectoryAudit(
        admin_login_id=user.id, entity="subscription", entity_id=str(sub.id), action="update",
        detail={"schedule_pattern": [pattern.kind, "Default"]}))
    db.commit()
    _reconcile(db, sub)


def _reconcile(db: Session, sub: Subscription) -> None:
    from app.scheduling.service import reconcile_vehicle

    reconcile_vehicle(db, sub.vehicle_id)
