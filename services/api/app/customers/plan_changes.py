"""A subscription's plan change from a date the admin chooses, and the history
of plan changes (S-11, ADM-SUB-08).

DERIVED: the new plan starts on the chosen date for visits (the scheduler) and
for the price of the next payment that is created. There is no proration
(owner decision S-10): a payment that already exists keeps its price. Without
a date the change starts on the next renewal date, as before (ADM-CUS-15). The
owner has not yet decided whether the chosen date replaces that rule."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customers.models import PlanChange, Subscription
from app.directory.models import DirectoryAudit, Plan
from app.identity.service import User
from app.platform.clock import today_ist
from app.platform.db import get_db, utcnow
from app.platform.deps import require_role
from app.platform.errors import ApiError

admin = APIRouter(prefix="/v1/admin", tags=["customer-administration"])


def _plan_name(db: Session, plan_id: uuid.UUID | None) -> str:
    plan = db.get(Plan, plan_id) if plan_id else None
    return plan.name if plan else ""


def cancel_scheduled(db: Session, sub: Subscription) -> None:
    """Ends the scheduled change of a subscription, if there is one."""
    for old in db.scalars(select(PlanChange).where(
            PlanChange.subscription_id == sub.id, PlanChange.status == "Scheduled")):
        old.status, old.ended_at = "Cancelled", utcnow()
    sub.pending_plan_id, sub.pending_from = None, None


def schedule(db: Session, sub: Subscription, plan: Plan, starts: date, chosen: bool,
             by: uuid.UUID) -> PlanChange:
    """Schedules `plan` from `starts`. A change already scheduled is cancelled."""
    cancel_scheduled(db, sub)
    sub.pending_plan_id, sub.pending_from = plan.id, starts
    change = PlanChange(
        subscription_id=sub.id, from_plan_id=sub.plan_id,
        from_plan_name=_plan_name(db, sub.plan_id), from_price_rupees=sub.monthly_price_rupees,
        to_plan_id=plan.id, to_plan_name=plan.name, to_price_rupees=plan.monthly_price_rupees,
        effective_from=starts, chosen=chosen, created_by=by)
    db.add(change)
    return change


def is_fixed(db: Session, sub: Subscription) -> bool:
    """True when the scheduled change has a date the admin chose. A pause does not move it."""
    return db.scalar(select(PlanChange.id).where(
        PlanChange.subscription_id == sub.id, PlanChange.status == "Scheduled",
        PlanChange.chosen.is_(True)).limit(1)) is not None


def follow_pending(db: Session, sub: Subscription) -> None:
    """Keeps the history's date in step when a pause moves a renewal-based change."""
    for change in db.scalars(select(PlanChange).where(
            PlanChange.subscription_id == sub.id, PlanChange.status == "Scheduled")):
        if sub.pending_from:
            change.effective_from = sub.pending_from


def mark_applied(db: Session, sub: Subscription, plan: Plan) -> None:
    """Called when the daily job moves the subscription onto its new plan."""
    for change in db.scalars(select(PlanChange).where(
            PlanChange.subscription_id == sub.id, PlanChange.status == "Scheduled")):
        change.status, change.ended_at = "Applied", utcnow()
        change.to_price_rupees = plan.monthly_price_rupees


def _row(c: PlanChange) -> dict:
    return {
        "id": str(c.id), "from_plan": c.from_plan_name, "from_price_rupees": c.from_price_rupees,
        "to_plan": c.to_plan_name, "to_price_rupees": c.to_price_rupees,
        "effective_from": c.effective_from.isoformat(), "status": c.status,
        "chosen": c.chosen, "created_at": c.created_at,
    }


def _subscription(db: Session, subscription_id: uuid.UUID) -> Subscription:
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise ApiError("not_found", "Subscription not found.", 404)
    return sub


@admin.get("/subscriptions/{subscription_id}/plan-history")
def plan_history(subscription_id: uuid.UUID, user: User = Depends(require_role("admin")),
                 db: Session = Depends(get_db)):
    sub = _subscription(db, subscription_id)
    rows = db.scalars(select(PlanChange).where(PlanChange.subscription_id == sub.id)
                      .order_by(PlanChange.created_at.desc(), PlanChange.id)).all()
    return {
        "current_plan": _plan_name(db, sub.plan_id),
        "current_price_rupees": sub.monthly_price_rupees,
        "changes": [_row(c) for c in rows],
    }


@admin.delete("/subscriptions/{subscription_id}/plan-change", status_code=204)
def cancel_plan_change(subscription_id: uuid.UUID, user: User = Depends(require_role("admin")),
                       db: Session = Depends(get_db)):
    """Cancels the plan change that has not started yet. It stays in the history."""
    sub = _subscription(db, subscription_id)
    if sub.pending_plan_id is None:
        raise ApiError("not_found", "No plan change is scheduled.", 404)
    cancel_scheduled(db, sub)
    db.add(DirectoryAudit(admin_login_id=user.id, entity="subscription", entity_id=str(sub.id),
                          action="update", detail={"plan_change": ["scheduled", "cancelled"]}))
    db.commit()
    from app.scheduling.service import reconcile_vehicle

    reconcile_vehicle(db, sub.vehicle_id)


def validate_start(starts: date) -> None:
    if starts < today_ist():
        raise ApiError("validation_failed", "Choose today or a later date.", 422)
