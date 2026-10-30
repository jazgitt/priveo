"""The usage budget (decision D18): one total in US dollars, with no time period. When all
recorded model usage reaches it, Mani stops calling the model until the owner raises it.
A local model costs 0, so only a hosted backend can use it up."""
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.mani.config import ManiSettings
from app.mani.models import ManiModelUsage


@dataclass(frozen=True)
class BudgetState:
    spent: Decimal
    budget: Decimal
    exhausted: bool


def spent_usd(db: Session) -> Decimal:
    """All usage ever recorded, chat and embedding, failed calls included."""
    total = db.scalar(select(func.coalesce(func.sum(ManiModelUsage.cost_usd), 0)))
    return Decimal(str(total or 0))


def check(db: Session, settings: ManiSettings) -> BudgetState:
    spent, budget = spent_usd(db), Decimal(str(settings.budget_usd))
    return BudgetState(spent, budget, spent >= budget)


def run_spent_usd(db: Session, run_id: uuid.UUID) -> Decimal:
    total = db.scalar(select(func.coalesce(func.sum(ManiModelUsage.cost_usd), 0))
                      .where(ManiModelUsage.run_id == run_id))
    return Decimal(str(total or 0))


def request_limit_reached(db: Session, settings: ManiSettings, run_id: uuid.UUID) -> bool:
    """True when this one run has used its per-request limit (0 means no limit)."""
    if settings.per_request_budget_usd <= 0:
        return False
    return run_spent_usd(db, run_id) >= Decimal(str(settings.per_request_budget_usd))
