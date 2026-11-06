"""SCHS-27: the exception report (SCHR-OUT-03, SCHR-WKE-06). Read only.

One list for each kind of exception, always present and empty when there is
nothing to report. Each row has the date, the car, the cleaner and a code.
Sources: the job rows (unassigned work, cross-zone reasons, weekend lateness)
and the schedule findings (everything the run and the Board's hand placements
record). Kinds whose producer is a later story (keys and cars, breaks) read
findings with their agreed codes and stay empty until those stories write them."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.directory import lookup
from app.directory.site_settings import SettingMissing
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import hand_placement, hooks, service
from app.scheduling.codes import ReasonCode
from app.scheduling.models import SERVICES, Job, Schedule, ScheduleFinding, Visit

router = APIRouter(prefix="/v1/admin/scheduling/reports", tags=["scheduling"])

EXTERIOR, INTERIOR = SERVICES[0], SERVICES[1]

# kind -> (label, finding codes it reads). Kinds with no codes are built from job rows.
KINDS: dict[str, tuple[str, tuple[str, ...]]] = {
    "unassigned_exteriors": ("Unassigned Exteriors", ()),
    "deferred_interiors": ("Interiors not planned", ()),
    "unavailable_keys_cars": ("Keys or cars unavailable", ("key_unavailable", "car_unavailable")),
    "cross_zone": ("Cross-zone jobs", (ReasonCode.CROSS_ZONE.value,)),
    "infeasible": ("Shift or cutoff infeasibility", (
        ReasonCode.SHIFT_TOO_SHORT.value, ReasonCode.CUSTOMER_CUTOFF.value,
        ReasonCode.NO_SLOT.value, ReasonCode.NO_PLAN.value)),
    "weekend_lateness": ("Weekend lateness", ()),
    "hand_placement": ("Hand placement breaches", ()),
    "missed_breaks": ("Missed breaks", ("break_missed",)),
}


class ExceptionRow(BaseModel):
    date: date | None
    job_id: uuid.UUID | None
    vehicle_id: uuid.UUID | None
    registration: str
    cleaner_id: uuid.UUID | None
    cleaner_name: str
    code: str
    detail: str = ""


class ExceptionKind(BaseModel):
    kind: str
    label: str
    rows: list[ExceptionRow]


class ExceptionReport(BaseModel):
    society_id: uuid.UUID
    start_date: date
    end_date: date
    kinds: list[ExceptionKind]


def _row(r: dict, code: str, detail: str = "") -> ExceptionRow:
    return ExceptionRow(date=r["date"], job_id=r["id"], vehicle_id=r["vehicle_id"],
                        registration=r["registration"], cleaner_id=r["crew_id"],
                        cleaner_name=r["crew_name"] or "", code=code, detail=detail)


def _weekend_days(db: Session, society_id: uuid.UUID) -> set[int]:
    """The weekend days of a site on rules version 2; none otherwise."""
    if hooks._version(db, society_id) != 2:
        return set()
    try:
        return set(lookup.site_setting(db, society_id, "site.weekend_weekdays"))
    except SettingMissing:
        return set()


@router.get("/exceptions", response_model=ExceptionReport)
def exception_report(
    society_id: uuid.UUID,
    start_date: date,
    end_date: date,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if end_date < start_date:
        raise ApiError("validation_failed", "The end date cannot be before the start date.", 422,
                       {"end_date": "Choose a date on or after the start date."})
    rows = [r for r in service.job_rows(
        db, Schedule.society_id == society_id, Visit.date >= start_date, Visit.date <= end_date)
        if r["status"] != "Skipped"]
    by_id = {r["id"]: r for r in rows}
    weekend = _weekend_days(db, society_id)
    manual = {i for i, in db.execute(select(Job.id).where(Job.id.in_(list(by_id)), Job.manual.is_(True)))} \
        if by_id else set()
    cross = dict(db.execute(select(Job.id, Job.cross_zone_reason).where(
        Job.id.in_(list(by_id)), Job.cross_zone_reason.is_not(None))).all()) if by_id else {}

    out: dict[str, list[ExceptionRow]] = {k: [] for k in KINDS}
    for r in rows:
        open_unassigned = r["crew_id"] is None and r["status"] == "Scheduled" and r["id"] not in manual
        code = r["reason_code"] or ""
        if open_unassigned and r["service"] == EXTERIOR:
            out["unassigned_exteriors"].append(_row(r, code, r["reason"]))
        elif open_unassigned and r["service"] == INTERIOR:
            out["deferred_interiors"].append(_row(r, code, r["reason"]))
        if r["id"] in cross:
            out["cross_zone"].append(_row(r, ReasonCode.CROSS_ZONE.value, cross[r["id"]]))
        if r["late"] and r["date"].weekday() in weekend:
            out["weekend_lateness"].append(_row(r, "weekend_late", f"Ends after {r['finish_by']}."))

    findings = db.execute(
        select(ScheduleFinding, Schedule).join(Schedule, Schedule.id == ScheduleFinding.schedule_id)
        .where(Schedule.society_id == society_id, Schedule.start_date <= end_date,
               Schedule.end_date >= start_date)
        .order_by(ScheduleFinding.created_at, ScheduleFinding.id)).all()
    for f, _schedule in findings:
        row_of = by_id.get(f.job_id)
        if f.job_id is not None and row_of is None:
            continue  # a job outside the dates, or Skipped
        row = _row(row_of, f.code, f.detail) if row_of else ExceptionRow(
            date=None, job_id=None, vehicle_id=None, registration="", cleaner_id=None,
            cleaner_name="", code=f.code, detail=f.detail)
        if f.code.startswith(hand_placement.PREFIX):
            out["hand_placement"].append(row)
            continue
        for kind, (_label, codes) in KINDS.items():
            if f.code in codes:
                out[kind].append(row)
    for kind in out:
        out[kind].sort(key=lambda x: (x.date or date.min, x.registration, x.code))
    return ExceptionReport(
        society_id=society_id, start_date=start_date, end_date=end_date,
        kinds=[ExceptionKind(kind=k, label=KINDS[k][0], rows=out[k]) for k in KINDS])
