"""Plan extension for a visit skipped by operations (ADM-OPS-03)."""

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.changes.models import PlanExtension
from app.customers.models import Subscription
from app.scheduling.models import Job, Visit


def extend_for_skipped_job(db: Session, job: Job, by_login_id: uuid.UUID) -> bool:
    """Adds one day to the plan when `job` is a Cleaning-External job skipped
    by operations. A skipped Cleaning-Internal or Deep Spa job does not extend
    it. Returns True when a day was added. Flushes and does not commit, so it
    shares the caller's transaction."""
    if job.service != "Cleaning-External":
        return False
    if db.scalar(select(PlanExtension.id).where(PlanExtension.job_id == job.id)) is not None:
        return False
    visit = db.get(Visit, job.visit_id)
    sub = db.scalar(select(Subscription).where(Subscription.vehicle_id == visit.vehicle_id))
    # A vehicle with no subscription has no plan to extend.
    if sub is None:
        return False
    db.add(
        PlanExtension(
            vehicle_id=visit.vehicle_id, job_id=job.id, on_date=visit.date, by_login_id=by_login_id
        )
    )
    db.flush()
    from app.billing.models import Payment

    for payment in db.scalars(
        select(Payment).where(
            Payment.subscription_id == sub.id,
            Payment.kind == "Plan",
            Payment.status != "Received",
            Payment.voided_at.is_(None),
            Payment.cycle_start >= visit.date,
        )
    ):
        payment.cycle_start += timedelta(days=1)
        if payment.cycle_end:
            payment.cycle_end += timedelta(days=1)
        payment.due_date += timedelta(days=1)
        if payment.overdue_since:
            payment.overdue_since += timedelta(days=1)
    return True
