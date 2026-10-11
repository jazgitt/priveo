import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.home import admin as admin_reads
from app.home.repository import HomeRepository
from app.home.schemas import AdminDaySchedule, AdminHome, CrewHome
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import get_home_repository, require_role

crew = APIRouter(prefix="/v1/crew", tags=["crew"])
admin = APIRouter(prefix="/v1/admin", tags=["admin"])


@crew.get("/home", response_model=CrewHome)
def crew_home(user: User = Depends(require_role("crew")),
              repo: HomeRepository = Depends(get_home_repository)):
    # Crew responses never carry a customer name or mobile number.
    return repo.crew_home(str(user.id))


@admin.get("/home", response_model=AdminHome)
def admin_home(user: User = Depends(require_role("admin")),
               db: Session = Depends(get_db)):
    return admin_reads.admin_home(db)


@admin.get("/schedule/day", response_model=AdminDaySchedule)
def admin_day_schedule(date: date, society_id: uuid.UUID | None = None,
                       user: User = Depends(require_role("admin")),
                       db: Session = Depends(get_db)):
    # Read only, for the phone. No customer name or mobile number.
    return admin_reads.day_schedule(db, date, society_id)
