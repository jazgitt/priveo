import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crew.service import CrewOut, CrewPassword, CrewProfile, CrewService, NewCrew
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role

admin = APIRouter(prefix="/v1/admin/crew", tags=["admin"])
crew = APIRouter(prefix="/v1/crew", tags=["crew"])


def get_crew_service(db: Session = Depends(get_db)) -> CrewService:
    return CrewService(db)


@admin.post("", response_model=CrewPassword, status_code=201)
def create_crew(body: NewCrew, _: User = Depends(require_role("admin")),
                crews: CrewService = Depends(get_crew_service)):
    """Onboards a crew member. The generated password is in this reply only."""
    return crews.create(body)


@admin.get("", response_model=list[CrewOut])
def list_crew(society_id: uuid.UUID | None = None,
              _: User = Depends(require_role("admin")),
              crews: CrewService = Depends(get_crew_service)):
    return crews.list(society_id)


@admin.post("/{crew_id}/password", response_model=CrewPassword)
def reset_password(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
                   crews: CrewService = Depends(get_crew_service)):
    """Generates a new password, shown once (ADM-CRW-18)."""
    return crews.reset_password(crew_id)


@admin.post("/{crew_id}/unlock", response_model=CrewOut)
def unlock(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
           crews: CrewService = Depends(get_crew_service)):
    return crews.unlock(crew_id)


@crew.get("/profile", response_model=CrewProfile)
def profile(user: User = Depends(require_role("crew")),
            crews: CrewService = Depends(get_crew_service)):
    """The crew member's own profile (CRW-PRF-01). No customer data."""
    return crews.profile(user.id)
