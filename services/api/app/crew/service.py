"""Crew accounts: onboarding, password reset and unlock (ADM-CRW-17,
ADM-CRW-18), and what a crew member sees of themselves (CRW-PRF-01)."""
import re
import secrets
import uuid
from datetime import time

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.crew.models import CREW_ROLES, CrewMember
from app.customers.models import WEEKDAYS
from app.directory.models import Society
from app.identity.models import AuthEvent, AuthSession, Login
from app.identity.service import hash_password
from app.platform.db import utcnow
from app.platform.errors import ApiError

_MOBILE = re.compile(r"\d{10}")
_TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


class DayHours(BaseModel):
    day: str
    working: bool
    # "HH:MM". Empty on a day off.
    start: str = ""
    end: str = ""


class NewCrew(BaseModel):
    name: str
    mobile: str
    society_id: uuid.UUID
    role: str
    working_hours: list[DayHours]


class CrewOut(BaseModel):
    id: str
    name: str
    mobile: str
    society_id: str
    society: str
    role: str
    active: bool
    locked: bool
    working_hours: list[DayHours]


class CrewPassword(BaseModel):
    """Shown to the admin once. Only the hash is kept (CRW-ACC-05)."""

    crew: CrewOut
    login_id: str
    password: str


class CrewProfile(BaseModel):
    """What a crew member sees of themselves (CRW-PRF-01). The photo comes
    with the media slice."""

    name: str
    mobile: str
    society: str
    role: str
    working_hours: list[DayHours]


def generate_password(name: str) -> str:
    """First 3 letters of the name, 4 random digits and `$` (CRW-ACC-04), for
    example `Raj4821$`. A name with fewer than 3 letters is padded with `x`."""
    letters = "".join(ch for ch in name if ch.isalpha())[:3].capitalize().ljust(3, "x")
    return f"{letters}{secrets.randbelow(10_000):04d}$"


def _problem(message: str, **fields: str) -> ApiError:
    return ApiError("validation_failed", message, 422, fields)


def check_hours(hours: list[DayHours]) -> list[dict]:
    """Seven days in week order, a start before the end on working days."""
    if [h.day for h in hours] != list(WEEKDAYS):
        raise _problem("Give the working hours for each day, Monday to Sunday.",
                       working_hours="Give all seven days.")
    out = []
    for h in hours:
        if h.working:
            if not (_TIME.fullmatch(h.start) and _TIME.fullmatch(h.end)):
                raise _problem(f"Set a start and end time for {h.day}.",
                               working_hours=f"{h.day}: use HH:MM.")
            if time.fromisoformat(h.start) >= time.fromisoformat(h.end):
                raise _problem(f"The start must be before the end on {h.day}.",
                               working_hours=f"{h.day}: start is after end.")
            out.append(h.model_dump())
        else:
            out.append(DayHours(day=h.day, working=False).model_dump())
    return out


class CrewService:
    def __init__(self, db: Session):
        self._db = db

    def _out(self, crew: CrewMember, login: Login, society: str) -> CrewOut:
        return CrewOut(
            id=str(crew.id), name=crew.name, mobile=crew.mobile,
            society_id=str(crew.society_id), society=society, role=crew.role,
            active=login.active, locked=login.locked,
            working_hours=[DayHours(**h) for h in crew.working_hours])

    def _get(self, crew_id: uuid.UUID) -> tuple[CrewMember, Login]:
        crew = self._db.get(CrewMember, crew_id)
        login = self._db.get(Login, crew.login_id) if crew else None
        if crew is None or login is None:
            raise ApiError("not_found", "This crew member was not found.", 404)
        return crew, login

    def create(self, body: NewCrew) -> CrewPassword:
        name = " ".join(body.name.split())
        mobile = body.mobile.strip()
        if not name or not any(ch.isalpha() for ch in name) or len(name) > 80:
            raise _problem("Enter the crew member's name.", name="Enter a name.")
        if not _MOBILE.fullmatch(mobile):
            raise _problem("The mobile number must have 10 digits.",
                           mobile="Use a 10-digit mobile number.")
        if body.role not in CREW_ROLES:
            raise _problem("Choose Manager, Member or Trainee.", role="Choose a role.")
        society = self._db.get(Society, body.society_id)
        if society is None:
            raise _problem("Choose a society.", society_id="Choose a society.")
        hours = check_hours(body.working_hours)
        # A mobile number is one login only (ADM-CRW-06, CRW-ACC-10).
        if self._db.scalar(select(Login.id).where(Login.login_id == mobile)) is not None:
            raise ApiError("mobile_in_use",
                           "This mobile number already belongs to a login.", 409,
                           {"mobile": "Already in use."})

        password = generate_password(name)
        login = Login(role="crew", login_id=mobile, display_name=name,
                      password_hash=hash_password(password), password_changed_at=utcnow())
        self._db.add(login)
        self._db.flush()
        crew = CrewMember(login_id=login.id, name=name, mobile=mobile,
                          society_id=society.id, role=body.role, working_hours=hours)
        self._db.add(crew)
        self._db.add(AuthEvent(login_id=login.id, kind="crew_created"))
        self._db.commit()
        return CrewPassword(crew=self._out(crew, login, society.name),
                            login_id=mobile, password=password)

    def list(self, society_id: uuid.UUID | None = None) -> list[CrewOut]:
        query = (select(CrewMember, Login, Society.name)
                 .join(Login, Login.id == CrewMember.login_id)
                 .join(Society, Society.id == CrewMember.society_id)
                 .order_by(Society.name, CrewMember.name))
        if society_id is not None:
            query = query.where(CrewMember.society_id == society_id)
        return [self._out(c, lg, s) for c, lg, s in self._db.execute(query)]

    def reset_password(self, crew_id: uuid.UUID) -> CrewPassword:
        """A new password, shown once. The old one stops working at once, every
        signed-in phone is signed out and a lock is lifted (ADM-CRW-18,
        CRW-ACC-11)."""
        crew, login = self._get(crew_id)
        password = generate_password(crew.name)
        now = utcnow()
        login.password_hash = hash_password(password)
        login.password_changed_at = now
        login.failed_attempts = 0
        login.locked = False
        self._db.execute(
            update(AuthSession)
            .where(AuthSession.login_id == login.id, AuthSession.ended_at.is_(None))
            .values(ended_at=now, ended_reason="password_reset"))
        self._db.add(AuthEvent(login_id=login.id, kind="password_reset_by_admin"))
        self._db.commit()
        society = self._db.get(Society, crew.society_id).name
        return CrewPassword(crew=self._out(crew, login, society),
                            login_id=login.login_id, password=password)

    def unlock(self, crew_id: uuid.UUID) -> CrewOut:
        """Lifts a lock after wrong attempts, keeping the same password."""
        crew, login = self._get(crew_id)
        login.locked = False
        login.failed_attempts = 0
        self._db.add(AuthEvent(login_id=login.id, kind="unlocked_by_admin"))
        self._db.commit()
        return self._out(crew, login, self._db.get(Society, crew.society_id).name)

    def profile(self, login_id: uuid.UUID) -> CrewProfile:
        crew = self._db.scalar(select(CrewMember).where(CrewMember.login_id == login_id))
        if crew is None:
            raise ApiError("no_crew_record",
                           "Your details are not set up yet. Contact Priveo.", 404)
        return CrewProfile(
            name=crew.name, mobile=crew.mobile,
            society=self._db.get(Society, crew.society_id).name, role=crew.role,
            working_hours=[DayHours(**h) for h in crew.working_hours])
