from fastapi import APIRouter, Depends, Query

from app.customer_reads.deps import get_customer_reads
from app.customer_reads.schemas import (
    CalendarMonth,
    HistoryItem,
    HistoryMetaOut,
    NextServiceItem,
    TodayCleanOut,
    VehicleDetail,
    VehicleSummary,
    VisitDetail,
)
from app.customer_reads.service import CustomerReads
from app.identity.service import User
from app.platform.clock import today_ist
from app.platform.deps import require_role

router = APIRouter(prefix="/v1/customer", tags=["customer"])
customer = require_role("customer")


@router.get("/calendar", response_model=CalendarMonth)
def calendar(month: str = Query(pattern=r"^\d{4}-\d{2}$", description="yyyy-mm"),
             vehicle_id: str | None = None, user: User = Depends(customer),
             reads: CustomerReads = Depends(get_customer_reads)):
    """The visits and their jobs in a month, for one vehicle or all (CAL-01)."""
    return reads.calendar(user.id, month, vehicle_id)


@router.get("/next-service", response_model=list[NextServiceItem])
def next_service(user: User = Depends(customer),
                 reads: CustomerReads = Depends(get_customer_reads)):
    """The next visit of each vehicle that has one (HOME-04)."""
    return reads.next_services(user.id, today_ist())


@router.get("/visits/{visit_id}", response_model=VisitDetail)
def visit_detail(visit_id: str, user: User = Depends(customer),
                 reads: CustomerReads = Depends(get_customer_reads)):
    """A visit with its jobs and their proof media (SVC-01, SVC-04, SVC-06)."""
    return reads.visit_detail(user.id, visit_id)


@router.get("/history", response_model=list[HistoryItem])
def history(vehicle_id: str | None = None, limit: int = Query(30, ge=1, le=100),
            offset: int = Query(0, ge=0),
            month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="yyyy-mm"),
            user: User = Depends(customer),
            reads: CustomerReads = Depends(get_customer_reads)):
    """Visits that are over, newest first, one month when `month` is given. Each
    has the finish time and the rating given (SVC-09, HIST-01, HIST-02)."""
    return reads.history(user.id, vehicle_id, limit, offset, month)


@router.get("/history/meta", response_model=HistoryMetaOut)
def history_meta(vehicle_id: str | None = None, user: User = Depends(customer),
                 reads: CustomerReads = Depends(get_customer_reads)):
    """Member-since and the first and last month of the history (HIST-02)."""
    return reads.history_meta(user.id, vehicle_id)


@router.get("/today", response_model=list[TodayCleanOut])
def today_cleans(user: User = Depends(customer),
                 reads: CustomerReads = Depends(get_customer_reads)):
    """Visits completed today, with finish time, checks and photo count, for
    the Home strip (HOME-03)."""
    return reads.today(user.id, today_ist())


@router.get("/vehicles", response_model=list[VehicleSummary])
def vehicles(user: User = Depends(customer),
             reads: CustomerReads = Depends(get_customer_reads)):
    """My vehicles (VEH-06)."""
    return reads.vehicles(user.id)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleDetail)
def vehicle(vehicle_id: str, user: User = Depends(customer),
            reads: CustomerReads = Depends(get_customer_reads)):
    """One vehicle's details (VEH-02, VEH-03)."""
    return reads.vehicle(user.id, vehicle_id)
