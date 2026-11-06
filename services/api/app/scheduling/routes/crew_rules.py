"""A cleaner's reporting and first-job times, as the admin edits them (SCHS-16).
The cleaner's own value is an override; null means the site value
(`app.scheduling.crew_rules`). Admin only. Edit surface only: nothing here
plans a day."""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crew.models import CrewMember
from app.directory import lookup
from app.directory.service import audit
from app.identity.service import User
from app.platform.db import get_db
from app.platform.deps import require_role
from app.platform.errors import ApiError
from app.scheduling import crew_rules, home_zone
from app.scheduling.models import SchedulingCrew

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
    """null clears the home zone."""
    home_zone_id: uuid.UUID | None = None


class HomeZoneOut(BaseModel):
    home_zone_id: str | None  # the zone in force; a Trainee shows the Member's
    follows_member: str | None  # the Member's name when a Trainee follows one
    editable: bool
    zones: list[ZoneChoice]


def _zone_out(db: Session, sc: SchedulingCrew) -> HomeZoneOut:
    mate = home_zone.paired_member(db, sc)
    mate_name = None
    if mate is not None:
        mate_member = db.scalar(select(CrewMember).where(CrewMember.login_id == mate.login_id))
        mate_name = mate_member.name if mate_member else None
    zone_id = home_zone.effective_zone_id(db, sc)
    return HomeZoneOut(
        home_zone_id=str(zone_id) if zone_id else None,
        follows_member=mate_name, editable=sc.role != "Trainee",
        zones=[ZoneChoice(id=str(z.id), name=z.name) for z in home_zone.zones_of(db, sc.society_id)])


@router.get("/{crew_id}/home-zone", response_model=HomeZoneOut)
def get_home_zone(crew_id: uuid.UUID, _: User = Depends(require_role("admin")),
                  db: Session = Depends(get_db)):
    """The home zone in force and the zones of the cleaner's society to pick from."""
    return _zone_out(db, _load(db, crew_id)[1])


@router.put("/{crew_id}/home-zone", response_model=HomeZoneOut)
def put_home_zone(crew_id: uuid.UUID, body: HomeZoneIn, user: User = Depends(require_role("admin")),
                  db: Session = Depends(get_db)):
    """Sets or clears the home zone (SCHR-ZONE-07) and audits the change."""
    member, sc = _load(db, crew_id)
    old = sc.home_zone_id
    home_zone.set_home_zone(db, sc, body.home_zone_id)
    if old != sc.home_zone_id:
        audit(db, user.id, "crew", member.id, "update",
              {"home_zone_id": [str(old) if old else None,
                                str(sc.home_zone_id) if sc.home_zone_id else None]})
    db.commit()
    return _zone_out(db, sc)
