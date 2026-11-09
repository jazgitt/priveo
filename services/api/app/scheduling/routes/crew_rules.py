"""A cleaner's reporting and first-job times, as the admin edits them (SCHS-16).
The cleaner's own value is an override; null means the site value
(`app.scheduling.crew_rules`). Admin only. Edit surface only: nothing here
plans a day."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
from app.directory import lookup
from app.directory.service import audit
from app.identity.service import User
from app.platform.clock import today_ist
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import crew_roles, crew_rules, home_zone
from app.scheduling import service as scheduling
from app.scheduling.models import SchedulingCrew, SchedulingCrewRolePeriod

router = APIRouter(prefix="/v1/admin/crew", tags=["admin"])

FIELDS = ("reporting_minute", "first_job_minute")


class CrewTimesIn(BaseModel):
    """Minutes after midnight. null clears the override."""
    reporting_minute: int | None = Field(None, ge=0, le=1439)
    first_job_minute: int | None = Field(None, ge=0, le=1439)


class CrewTimesOut(BaseModel):
    reporting_minute: int | None
    first_job_minute: int | None
    site_reporting_minute: int
    site_first_job_minute: int


def _load(db: Session, crew_id: uuid.UUID) -> tuple[CrewMember, SchedulingCrew]:
    member = db.get(CrewMember, crew_id)
    sc = db.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == member.login_id)) \
        if member else None
    if member is None or sc is None:
        raise ApiError("not_found", "This crew member was not found.", 404)
    return member, sc


def _out(db: Session, sc: SchedulingCrew) -> CrewTimesOut:
    return CrewTimesOut(
        reporting_minute=sc.reporting_minute, first_job_minute=sc.first_job_minute,
        site_reporting_minute=lookup.site_setting(db, sc.society_id, "site.reporting_minute"),
        site_first_job_minute=lookup.site_setting(db, sc.society_id, "site.first_job_minute"))


@router.get("/{crew_id}/times", response_model=CrewTimesOut)
def get_times(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
              db: Session = Depends(get_db)):
    """The cleaner's overrides and the site values they fall back to."""
    return _out(db, _load(db, crew_id)[1])


@router.put("/{crew_id}/times", response_model=CrewTimesOut)
def put_times(crew_id: uuid.UUID, body: CrewTimesIn, user: User = Depends(require_role("admin")),
              db: Session = Depends(get_db)):
    """Sets both overrides (null clears one) and audits what changed."""
    member, sc = _load(db, crew_id)
    new = {f: getattr(body, f) for f in FIELDS}
    old = {f: getattr(sc, f) for f in FIELDS}
    for f in FIELDS:
        setattr(sc, f, new[f])
    if crew_rules.first_job_minute(db, sc) < crew_rules.reporting_minute(db, sc):
        db.rollback()
        raise ApiError("validation_failed", "The first job cannot be before the reporting time.",
                       422, {"first_job_minute": "Choose a time at or after the reporting time."})
    diff = {f: [old[f], new[f]] for f in FIELDS if old[f] != new[f]}
    if diff:
        audit(db, user.id, "crew", member.id, "update", diff)
    db.commit()
    return _out(db, sc)


class ZoneChoice(BaseModel):
    id: str
    name: str


class HomeZoneIn(BaseModel):
    """The cleaner's home zones. An empty list clears them."""
    home_zone_ids: list[uuid.UUID] = Field(default_factory=list)


class HomeZoneOut(BaseModel):
    home_zone_ids: list[str]  # the zones in force; a Trainee shows the Member's
    follows_member: str | None  # the Member's name when a Trainee follows one
    editable: bool
    zones: list[ZoneChoice]


def _zone_out(db: Session, sc: SchedulingCrew) -> HomeZoneOut:
    mate = home_zone.paired_member(db, sc)
    mate_name = None
    if mate is not None:
        mate_member = db.scalar(select(CrewMember).where(CrewMember.login_id == mate.login_id))
        mate_name = mate_member.name if mate_member else None
    return HomeZoneOut(
        home_zone_ids=[str(z.id) for z in home_zone.effective_zones(db, sc)],
        follows_member=mate_name, editable=sc.role != "Trainee",
        zones=[ZoneChoice(id=str(z.id), name=z.name) for z in home_zone.zones_of(db, sc.society_id)])


@router.get("/{crew_id}/home-zone", response_model=HomeZoneOut)
def get_home_zone(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
                  db: Session = Depends(get_db)):
    """The home zones in force and the zones of the cleaner's society to pick from."""
    return _zone_out(db, _load(db, crew_id)[1])


@router.put("/{crew_id}/home-zone", response_model=HomeZoneOut)
def put_home_zone(crew_id: uuid.UUID, body: HomeZoneIn, user: User = Depends(require_role("admin")),
                  db: Session = Depends(get_db)):
    """Replaces the home zones (SCHR-ZONE-07) and audits the change."""
    member, sc = _load(db, crew_id)
    old = sorted(str(z.id) for z in home_zone.own_zones(db, sc))
    home_zone.set_home_zones(db, sc, body.home_zone_ids)
    new = sorted(str(z.id) for z in home_zone.own_zones(db, sc))
    if old != new:
        audit(db, user.id, "crew", member.id, "update", {"home_zone_ids": [old, new]})
    db.commit()
    return _zone_out(db, sc)


class RolePeriodIn(BaseModel):
    """A role for a date range (P2-4). Both dates are optional, but at least one
    is needed: with no dates the role is changed on the crew member's page.
    No start date means from today. No end date means until the role is changed."""
    role: str
    start_date: date | None = None
    end_date: date | None = None


class RolePeriodOut(BaseModel):
    id: str
    role: str
    start_date: date
    end_date: date | None


class ReleasedJobOut(BaseModel):
    job_id: str
    date: date
    service: str
    vehicle_id: str
    registration: str


class RolePeriodResult(BaseModel):
    periods: list[RolePeriodOut]
    # Open jobs that no longer fit the new role went to the Needs scheduling list.
    released_jobs: list[ReleasedJobOut]


def _periods_out(db: Session, sc: SchedulingCrew) -> list[RolePeriodOut]:
    return [RolePeriodOut(id=str(p.id), role=p.role, start_date=p.start_date, end_date=p.end_date)
            for p in crew_roles.periods_of(db, sc)]


@router.get("/{crew_id}/role-periods", response_model=list[RolePeriodOut])
def list_role_periods(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
                      db: Session = Depends(get_db)):
    """The dated roles that have not ended, soonest first."""
    return _periods_out(db, _load(db, crew_id)[1])


@router.post("/{crew_id}/role-periods", response_model=RolePeriodResult, status_code=201)
def add_role_period(crew_id: uuid.UUID, body: RolePeriodIn, user: User = Depends(require_role("admin")),
                    db: Session = Depends(get_db)):
    """Adds a dated role and frees the open jobs it no longer fits. Days already
    run are not changed (owner decision 7)."""
    member, sc = _load(db, crew_id)
    today = today_ist()
    row = crew_roles.add_period(db, sc, body.role, body.start_date, body.end_date, user.id)
    crew_roles.attach(db, {sc.id: sc}, today)
    released = scheduling.release_unfit(db, sc, today)
    audit(db, user.id, "crew", member.id, "update", {"role_period": [None, {
        "role": row.role, "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat() if row.end_date else None}]})
    db.commit()
    return RolePeriodResult(periods=_periods_out(db, sc), released_jobs=[
        ReleasedJobOut(job_id=str(j["job_id"]), date=j["date"], service=j["service"],
                       vehicle_id=str(j["vehicle_id"]), registration=j["registration"])
        for j in released])


@router.delete("/{crew_id}/role-periods/{period_id}", response_model=list[RolePeriodOut])
def cancel_role_period(crew_id: uuid.UUID, period_id: uuid.UUID,
                       user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Removes a dated role that has not ended. The permanent role applies again."""
    member, sc = _load(db, crew_id)
    old = db.get(SchedulingCrewRolePeriod, period_id)
    crew_roles.cancel_period(db, sc, period_id)
    crew_roles.attach(db, {sc.id: sc}, today_ist())
    if old is not None:
        audit(db, user.id, "crew", member.id, "update", {"role_period": [{
            "role": old.role, "start_date": old.start_date.isoformat(),
            "end_date": old.end_date.isoformat() if old.end_date else None}, None]})
    db.commit()
    return _periods_out(db, sc)
