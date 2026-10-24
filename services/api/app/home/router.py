import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.home import admin as admin_reads
from app.home.schemas import AdminDaySchedule, AdminHome, DaySummary
from app.identity.service import User
from app.platform.clock import today_ist
from app.platform.db import get_db
from app.platform.deps import require_role

# Kept empty: the mock crew home was removed (the crew app reads /v1/crew/visits).
crew = APIRouter(prefix="/v1/crew", tags=["crew"])
admin = APIRouter(prefix="/v1/admin", tags=["admin"])


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


@admin.get("/home/day-summary", response_model=DaySummary)
def admin_day_summary(date: date | None = None, crew_id: uuid.UUID | None = None,
                      vehicle_id: uuid.UUID | None = None,
                      society_id: uuid.UUID | None = None,
                      registration: str | None = None,
                      user: User = Depends(require_role("admin")),
                      db: Session = Depends(get_db)):
    """A-02: today's (IST) visits by outcome. No customer name or mobile number."""
    return admin_reads.day_summary(db, date or today_ist(), crew_id, vehicle_id, society_id,
                                    registration)
