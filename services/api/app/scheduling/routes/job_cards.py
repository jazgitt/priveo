"""Job cards as PDF (P1-2). Admin only, read only.

Two options on the Schedule page:
- `GET /v1/admin/scheduling/job-cards/pdf`: one PDF for all crew, not split.
- `GET /v1/admin/scheduling/job-cards/crews/{crew_id}/pdf`: one PDF for one crew member.

Both take `schedule_id` and `date` (the day of the cards, inside the schedule)."""
import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import service
from app.scheduling.job_card_pdf import render_job_cards
from app.scheduling.job_cards import crew_cards, crew_name
from app.scheduling.models import Schedule, SchedulingCrew

router = APIRouter(prefix="/v1/admin/scheduling/job-cards", tags=["scheduling"])


def _schedule_on(db: Session, schedule_id: uuid.UUID, day: date) -> Schedule:
    schedule = service.get_schedule(db, schedule_id)
    if not schedule.start_date <= day <= schedule.end_date:
        raise ApiError("validation_failed", "That day is not part of this schedule.", 422)
    return schedule


def _pdf(content: bytes, name: str) -> Response:
    return Response(
        content=content, media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/pdf")
def all_crew_cards(
    schedule_id: uuid.UUID,
    day: date = Query(alias="date"),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    schedule = _schedule_on(db, schedule_id, day)
    content = render_job_cards(day, crew_cards(db, schedule, day))
    return _pdf(content, f"job-cards-{day.isoformat()}.pdf")


@router.get("/crews/{crew_id}/pdf")
def one_crew_cards(
    crew_id: uuid.UUID,
    schedule_id: uuid.UUID,
    day: date = Query(alias="date"),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    schedule = _schedule_on(db, schedule_id, day)
    member = db.get(SchedulingCrew, crew_id)
    if member is None or member.society_id != schedule.society_id:
        raise ApiError("not_found", "That crew member does not exist.", 404)
    content = render_job_cards(day, crew_cards(db, schedule, day, crew_id=crew_id))
    slug = re.sub(r"[^A-Za-z0-9]+", "-", crew_name(db, crew_id) or "").strip("-") or str(crew_id)
    return _pdf(content, f"job-cards-{slug}-{day.isoformat()}.pdf")
