import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crew.service import (
    CrewChange,
    CrewDeactivate,
    CrewEdit,
    CrewExceptionEdit,
    CrewExceptionNew,
    CrewExceptionOut,
    CrewExceptionResult,
    CrewHoursChange,
    CrewOut,
    CrewPairChange,
    CrewPassword,
    CrewProfile,
    CrewRoleChange,
    CrewService,
    CrewSessionOut,
    CrewSessionsEnded,
    NewCrew,
)
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
    """Onboards a crew member and makes their scheduler record in the same
    step. The generated password is in this reply only."""
    return crews.create(body)


@admin.get("", response_model=list[CrewOut])
def list_crew(society_id: uuid.UUID | None = None,
              _: User = Depends(require_role("admin")),
              crews: CrewService = Depends(get_crew_service)):
    return crews.list(society_id)


@admin.get("/{crew_id}", response_model=CrewOut)
def get_crew(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
             crews: CrewService = Depends(get_crew_service)):
    return crews.get(crew_id)


@admin.patch("/{crew_id}", response_model=CrewOut)
def edit_crew(crew_id: uuid.UUID, body: CrewEdit,
              _: User = Depends(require_role("admin")),
              crews: CrewService = Depends(get_crew_service)):
    """Name and mobile number (ADM-CRW-02). A new mobile number is the new
    login ID and signs the crew member out."""
    return crews.edit(crew_id, body)


@admin.put("/{crew_id}/role", response_model=CrewChange)
def change_role(crew_id: uuid.UUID, body: CrewRoleChange,
                _: User = Depends(require_role("admin")),
                crews: CrewService = Depends(get_crew_service)):
    """Manager, Member or Trainee (ADM-CRW-03). A Trainee needs a Member."""
    return crews.change_role(crew_id, body)


@admin.put("/{crew_id}/pair", response_model=CrewOut)
def pair_trainee(crew_id: uuid.UUID, body: CrewPairChange,
                 _: User = Depends(require_role("admin")),
                 crews: CrewService = Depends(get_crew_service)):
    """Pairs a Trainee with a Member of the same society (ADM-CRW-19)."""
    return crews.pair(crew_id, body)


@admin.put("/{crew_id}/working-hours", response_model=CrewChange)
def set_hours(crew_id: uuid.UUID, body: CrewHoursChange,
              _: User = Depends(require_role("admin")),
              crews: CrewService = Depends(get_crew_service)):
    """Hours for each weekday, applied from today on (ADM-CRW-05)."""
    return crews.set_hours(crew_id, body)


@admin.get("/{crew_id}/exceptions", response_model=list[CrewExceptionOut])
def list_exceptions(crew_id: uuid.UUID, from_date: date | None = None,
                    _: User = Depends(require_role("admin")),
                    crews: CrewService = Depends(get_crew_service)):
    return crews.list_exceptions(crew_id, from_date)


@admin.post("/{crew_id}/exceptions", response_model=CrewExceptionResult, status_code=201)
def add_exceptions(crew_id: uuid.UUID, body: CrewExceptionNew,
                   _: User = Depends(require_role("admin")),
                   crews: CrewService = Depends(get_crew_service)):
    """Sick, Leave or Late start on one date or a range (ADM-CRW-08). Open
    jobs that no longer fit come back in `released_jobs` (ADM-CRW-12)."""
    return crews.add_exceptions(crew_id, body)


@admin.patch("/{crew_id}/exceptions/{exception_id}", response_model=CrewExceptionResult)
def edit_exception(crew_id: uuid.UUID, exception_id: uuid.UUID, body: CrewExceptionEdit,
                   _: User = Depends(require_role("admin")),
                   crews: CrewService = Depends(get_crew_service)):
    return crews.edit_exception(crew_id, exception_id, body)


@admin.delete("/{crew_id}/exceptions/{exception_id}", response_model=CrewExceptionResult)
def remove_exception(crew_id: uuid.UUID, exception_id: uuid.UUID,
                     _: User = Depends(require_role("admin")),
                     crews: CrewService = Depends(get_crew_service)):
    return crews.remove_exception(crew_id, exception_id)


@admin.post("/{crew_id}/deactivate", response_model=CrewChange)
def deactivate(crew_id: uuid.UUID, body: CrewDeactivate | None = None,
               _: User = Depends(require_role("admin")),
               crews: CrewService = Depends(get_crew_service)):
    """For a crew member who has left (ADM-CRW-15). Frozen jobs need
    `release_jobs: true`."""
    return crews.deactivate(crew_id, body or CrewDeactivate())


@admin.post("/{crew_id}/reactivate", response_model=CrewOut)
def reactivate(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
               crews: CrewService = Depends(get_crew_service)):
    return crews.reactivate(crew_id)


@admin.get("/{crew_id}/sessions", response_model=list[CrewSessionOut])
def list_sessions(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
                  crews: CrewService = Depends(get_crew_service)):
    """The crew member's signed-in devices (ADM-CRW-21)."""
    return crews.sessions(crew_id)


@admin.post("/{crew_id}/sessions/logout", response_model=CrewSessionsEnded)
def end_all_sessions(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
                     crews: CrewService = Depends(get_crew_service)):
    return crews.end_all_sessions(crew_id)


@admin.post("/{crew_id}/sessions/{session_id}/logout", response_model=CrewSessionsEnded)
def end_session(crew_id: uuid.UUID, session_id: uuid.UUID,
                _: User = Depends(require_role("admin")),
                crews: CrewService = Depends(get_crew_service)):
    return crews.end_session(crew_id, session_id)


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
