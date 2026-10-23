from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.directory import lookup
from app.identity.service import User
from app.platform.clock import today_ist
from app.platform.db import get_db
from app.platform.deps import require_role
from app.scheduling import queue
from app.visits import manager as manager_ops
from app.visits import manager_schemas as ms
from app.visits import schemas as s
from app.visits import service

router = APIRouter(prefix="/v1/crew", tags=["crew"])


@router.get("/visits", response_model=s.VisitList)
def my_jobs(day: Annotated[date | None, Query(alias="date")] = None,
            all: bool = False,
            user: User = Depends(require_role("crew")), db: Session = Depends(get_db)):
    """The job cards for one day (today when `date` is left out), or every
    card when `all=true` (CRW-SCH-06)."""
    return service.list_jobs(db, user.id, None if all else (day or today_ist()))


@router.get("/reasons", response_model=list[s.Reason])
def reasons(user: User = Depends(require_role("crew")), db: Session = Depends(get_db)):
    return [s.Reason(key=r.key, label=r.label) for r in lookup.reasons(db)]


@router.get("/jobs/{job_id}", response_model=s.JobDetail)
def job(job_id: str, user: User = Depends(require_role("crew")),
        db: Session = Depends(get_db)):
    return service.job_detail(db, service.visible_job(db, user.id, job_id))


@router.post("/jobs/{job_id}/start", response_model=s.JobDetail)
def start(job_id: str, user: User = Depends(require_role("crew")),
          db: Session = Depends(get_db)):
    j = service.visible_job(db, user.id, job_id)
    queue.require_unlocked(db, j)  # S-13: the crew's own routes only
    service.start_job(db, j)
    return service.job_detail(db, j)


@router.put("/jobs/{job_id}/checklist/{item_id}", response_model=s.JobDetail)
def tick(job_id: str, item_id: str, body: s.ChecklistTick,
         user: User = Depends(require_role("crew")), db: Session = Depends(get_db)):
    j = service.visible_job(db, user.id, job_id)
    queue.require_unlocked(db, j)  # S-13: the crew's own routes only
    service.set_checked(db, j, item_id, body.checked, user.id)
    return service.job_detail(db, j)


@router.post("/jobs/{job_id}/complete", response_model=s.JobDetail)
def complete(job_id: str, user: User = Depends(require_role("crew")),
             db: Session = Depends(get_db)):
    j = service.visible_job(db, user.id, job_id)
    queue.require_unlocked(db, j)  # S-13: the crew's own routes only
    service.complete_job(db, j)
    return service.job_detail(db, j)


@router.post("/jobs/{job_id}/could-not-complete", response_model=s.JobDetail)
def could_not_complete(job_id: str, body: s.CouldNotComplete,
                       user: User = Depends(require_role("crew")),
                       db: Session = Depends(get_db)):
    j = service.visible_job(db, user.id, job_id)
    queue.require_unlocked(db, j)  # S-13: the crew's own routes only
    service.could_not_complete(db, j, body, user.id)
    return service.job_detail(db, j)


@router.get("/profile/photo", response_model=s.PhotoState)
def photo(user: User = Depends(require_role("crew")), db: Session = Depends(get_db)):
    """The profile itself is `GET /v1/crew/profile` of the crew module."""
    return service.photo_state(db, user.id)


@router.put("/profile/photo", response_model=s.PhotoState)
def set_photo(body: s.ProfilePhoto, user: User = Depends(require_role("crew")),
              db: Session = Depends(get_db)):
    return service.set_profile_photo(db, user.id, body.upload_id)


# ---- Manager (CRW-MGR) -----------------------------------------------------------

@router.get("/manager/schedule", response_model=s.ManagerSchedule)
def manager_schedule(day: Annotated[date | None, Query(alias="date")] = None,
                     user: User = Depends(require_role("crew")),
                     db: Session = Depends(get_db)):
    manager = service.require_manager(db, user.id)
    return service.manager_schedule(db, manager, day or today_ist())


@router.get("/manager/crew", response_model=list[s.CrewRef])
def manager_crew(user: User = Depends(require_role("crew")), db: Session = Depends(get_db)):
    return service.crew_options(db, service.require_manager(db, user.id))


@router.get("/manager/jobs/{job_id}", response_model=s.JobDetail)
def manager_job(job_id: str, user: User = Depends(require_role("crew")),
                db: Session = Depends(get_db)):
    return service.job_detail(db, service.managed_job(db, user.id, job_id))


@router.post("/manager/jobs/{job_id}/could-not-complete", response_model=s.JobDetail)
def manager_could_not_complete(job_id: str, body: s.CouldNotComplete,
                               user: User = Depends(require_role("crew")),
                               db: Session = Depends(get_db)):
    j = service.managed_job(db, user.id, job_id)
    service.could_not_complete(db, j, body, user.id)
    return service.job_detail(db, j)


@router.post("/manager/jobs/{job_id}/skip", response_model=s.JobDetail)
def manager_skip(job_id: str, user: User = Depends(require_role("crew")),
                 db: Session = Depends(get_db)):
    j = service.managed_job(db, user.id, job_id)
    service.manager_skip(db, j, user.id)
    return service.job_detail(db, j)


@router.post("/manager/jobs/{job_id}/reassign", response_model=s.JobDetail)
def manager_reassign(job_id: str, body: s.Reassign,
                     user: User = Depends(require_role("crew")),
                     db: Session = Depends(get_db)):
    manager = service.require_manager(db, user.id)
    j = service.managed_job(db, user.id, job_id)
    service.manager_reassign(db, j, manager, body.crew_id, user.id)
    return service.job_detail(db, j)


# ---- Manager attendance, hours and reassign checks (CRW-MGR-03 to CRW-MGR-05) -----

@router.get("/manager/attendance", response_model=ms.CrewManagerAttendance)
def manager_attendance(day: Annotated[date | None, Query(alias="date")] = None,
                       user: User = Depends(require_role("crew")),
                       db: Session = Depends(get_db)):
    manager = service.require_manager(db, user.id)
    return manager_ops.attendance(db, manager, day or today_ist())


@router.put("/manager/attendance/{crew_id}", response_model=ms.CrewManagerAttendanceResult)
def manager_set_attendance(crew_id: str, body: ms.CrewManagerAttendanceSet,
                           user: User = Depends(require_role("crew")),
                           db: Session = Depends(get_db)):
    manager = service.require_manager(db, user.id)
    return manager_ops.set_attendance(db, manager, crew_id, body, user.id)


@router.get("/manager/hours", response_model=list[ms.CrewManagerHours])
def manager_hours(user: User = Depends(require_role("crew")), db: Session = Depends(get_db)):
    return manager_ops.hours_list(db, service.require_manager(db, user.id))


@router.put("/manager/hours/{crew_id}", response_model=ms.CrewManagerHoursResult)
def manager_set_hours(crew_id: str, body: ms.CrewManagerHoursSet,
                      user: User = Depends(require_role("crew")),
                      db: Session = Depends(get_db)):
    manager = service.require_manager(db, user.id)
    return manager_ops.set_hours(db, manager, crew_id, body, user.id)


@router.get("/manager/jobs/{job_id}/reassign-options",
            response_model=list[ms.CrewManagerReassignOption])
def manager_reassign_options(job_id: str, user: User = Depends(require_role("crew")),
                             db: Session = Depends(get_db)):
    manager = service.require_manager(db, user.id)
    job = service.managed_job(db, user.id, job_id)
    return manager_ops.reassign_options(db, manager, job)
