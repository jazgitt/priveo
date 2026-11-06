"""The break rules that reach one cleaner, for the crew screen (SCHS-28).

The break API (`break-rules`) names a cleaner by the scheduling id; the crew
screen knows the crew member's id. This route translates and returns the rules
that can apply to the cleaner: their own and the site-wide date ranges."""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling.models import BreakRule, SchedulingCrew
from app.scheduling.routes.breaks import BreakRuleOut, _out

router = APIRouter(prefix="/v1/admin/crew", tags=["admin"])


class CrewBreakRules(BaseModel):
    scheduling_crew_id: uuid.UUID
    society_id: uuid.UUID
    rules: list[BreakRuleOut]


@router.get("/{crew_id}/break-rules", response_model=CrewBreakRules)
def crew_break_rules(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
                     db: Session = Depends(get_db)):
    member = db.get(CrewMember, crew_id)
    sc = db.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == member.login_id)) \
        if member else None
    if sc is None:
        raise ApiError("not_found", "This crew member was not found.", 404)
    rows = db.scalars(select(BreakRule).where(
        BreakRule.society_id == sc.society_id,
        (BreakRule.crew_id.is_(None)) | (BreakRule.crew_id == sc.id))
        .order_by(BreakRule.start_date, BreakRule.created_at))
    return CrewBreakRules(scheduling_crew_id=sc.id, society_id=sc.society_id,
                          rules=[_out(r) for r in rows])
