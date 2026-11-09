"""P3-2.2: the jobs due on one date, for the Demand tab on the capacity page.
Read only. The order is set in app.scheduling.demand_list."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.scheduling import demand_list

router = APIRouter(prefix="/v1/admin/scheduling", tags=["scheduling"])


class DemandItem(BaseModel):
    group: str
    service: str
    service_label: str
    vehicle_id: uuid.UUID
    registration: str
    vehicle: str
    cutoff: str | None
    source: str


@router.get("/demand", response_model=list[DemandItem])
def demand_for_day(
    society_id: uuid.UUID,
    date: date,
    service: str | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = demand_list.due_on(db, society_id, date, service)
    return [DemandItem(**row.__dict__) for row in rows]
