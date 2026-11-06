"""Admin API for break override rows (SCHR-PAR-09, SCHR-BRK-06). Today,
Tomorrow and Date range are screen conveniences: the API takes dates."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import breaks
from app.scheduling.models import BreakRule, SchedulingCrew

router = APIRouter(prefix="/v1/admin/scheduling/break-rules", tags=["scheduling"])


class BreakRuleIn(BaseModel):
    society_id: uuid.UUID
    crew_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_minute: int | None = None
    end_minute: int | None = None
    enabled: bool = True


class BreakRuleUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    start_minute: int | None = None
    end_minute: int | None = None
    enabled: bool | None = None


class BreakRuleOut(BaseModel):
    id: uuid.UUID
    society_id: uuid.UUID
    crew_id: uuid.UUID | None
    start_date: date | None
    end_date: date | None
    start_minute: int | None
    end_minute: int | None
    enabled: bool


class EffectiveBreak(BaseModel):
    crew_id: uuid.UUID
    date: date
    start_minute: int | None
    end_minute: int | None
    source: str | None


def _out(rule: BreakRule) -> BreakRuleOut:
    open_ = breaks.is_open(rule)
    return BreakRuleOut(
        id=rule.id, society_id=rule.society_id, crew_id=rule.crew_id,
        start_date=None if open_ else rule.start_date, end_date=None if open_ else rule.end_date,
        start_minute=rule.start_minute, end_minute=rule.end_minute, enabled=rule.enabled)


@router.get("", response_model=list[BreakRuleOut])
def list_rules(society_id: uuid.UUID, crew_id: uuid.UUID | None = None,
               _: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    query = select(BreakRule).where(BreakRule.society_id == society_id)
    if crew_id is not None:
        query = query.where(BreakRule.crew_id == crew_id)
    return [_out(r) for r in db.scalars(query.order_by(BreakRule.start_date, BreakRule.created_at))]


@router.get("/effective", response_model=EffectiveBreak)
def effective(crew_id: uuid.UUID, date: date, _: User = Depends(require_role("admin")),
              db: Session = Depends(get_db)):
    crew = db.get(SchedulingCrew, crew_id)
    if crew is None:
        raise ApiError("not_found", "This crew member was not found.", 404)
    found = breaks.effective_break(db, crew, date)
    return EffectiveBreak(crew_id=crew_id, date=date,
                          start_minute=found.start_minute if found else None,
                          end_minute=found.end_minute if found else None,
                          source=found.source if found else None)


@router.post("", response_model=BreakRuleOut, status_code=201)
def create_rule(body: BreakRuleIn, user: User = Depends(require_role("admin")),
                db: Session = Depends(get_db)):
    rule = breaks.save_rule(db, user.id, body.society_id, **body.model_dump(exclude={"society_id"}))
    return _out(rule)


@router.patch("/{rule_id}", response_model=BreakRuleOut)
def update_rule(rule_id: uuid.UUID, body: BreakRuleUpdate,
                user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    changes = body.model_dump(exclude_unset=True)
    if changes.get("enabled", True) is None:
        raise breaks._invalid("enabled", "Choose on or off.")
    return _out(breaks.update_rule(db, user.id, breaks.get_rule(db, rule_id), changes))


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: uuid.UUID, user: User = Depends(require_role("admin")),
                db: Session = Depends(get_db)):
    breaks.delete_rule(db, user.id, breaks.get_rule(db, rule_id))
    return Response(status_code=204)
