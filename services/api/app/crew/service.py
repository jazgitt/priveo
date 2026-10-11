"""Crew accounts: onboarding, password reset and unlock (ADM-CRW-17,
ADM-CRW-18), role, pairing, working hours, exceptions, deactivation and
sessions (ADM-CRW-03 to ADM-CRW-21), and what a crew member sees of
themselves (CRW-PRF-01).

A crew member is two rows kept in step here: `CrewMember` (the directory) and
`SchedulingCrew` (what the scheduler and the crew's job lists read). Every
change goes through `_sync` in the same transaction."""
import re
import secrets
import uuid
from datetime import date, datetime, time, timedelta

from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.crew.models import CREW_ROLES, CrewMember
from app.customers.models import WEEKDAYS
from app.directory.models import Society
from app.identity.models import AuthEvent, AuthSession, Login
from app.identity.service import hash_password
from app.platform.clock import today_ist
from app.platform.db import utcnow
from app.platform.errors import ApiError
from app.scheduling import service as scheduling
from app.scheduling.models import (
    Job,
    Schedule,
    SchedulingCrew,
    SchedulingCrewException,
    Visit,
)

_MOBILE = re.compile(r"\d{10}")
_TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d")

EXCEPTION_KINDS = ("Sick", "Leave", "Late start")  # ADM-CRW-08
MAX_RANGE_DAYS = 62


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
    # A Trainee is onboarded with the Member they are paired with (ADM-CRW-19).
    paired_member_id: uuid.UUID | None = None


class CrewExceptionOut(BaseModel):
    id: str
    date: date
    kind: str
    # "HH:MM" for a Late start, empty otherwise.
    start: str = ""


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
    # A Trainee's Member: the Member's crew ID and name (ADM-CRW-19).
    paired_member_id: str | None = None
    paired_member: str = ""
    # From today on, soonest first (ADM-CRW-07).
    exceptions: list[CrewExceptionOut] = []


class CrewEdit(BaseModel):
    name: str | None = None
    mobile: str | None = None


class CrewRoleChange(BaseModel):
    role: str
    # Required when the new role is Trainee.
    paired_member_id: uuid.UUID | None = None


class CrewHoursChange(BaseModel):
    working_hours: list[DayHours]


class CrewPairChange(BaseModel):
    paired_member_id: uuid.UUID


class CrewDeactivate(BaseModel):
    # Open jobs are sent to Needs scheduling only when the admin says so.
    release_jobs: bool = False


class CrewExceptionNew(BaseModel):
    kind: str
    from_date: date
    to_date: date | None = None
    # Late start only: "HH:MM", the time the crew member can begin.
    start: str = ""


class CrewExceptionEdit(BaseModel):
    kind: str | None = None
    start: str | None = None


class CrewReleasedJob(BaseModel):
    job_id: str
    date: date
    service: str
    vehicle_id: str
    registration: str


class CrewChange(BaseModel):
    """A crew member after a change, with the jobs the change put on the
    Needs scheduling list (ADM-CRW-12)."""

    crew: CrewOut
    released_jobs: list[CrewReleasedJob] = []


class CrewExceptionResult(BaseModel):
    crew: CrewOut
    exceptions: list[CrewExceptionOut]
    released_jobs: list[CrewReleasedJob] = []


class CrewSessionOut(BaseModel):
    id: str
    channel: str
    signed_in_at: datetime
    last_active_at: datetime


class CrewSessionsEnded(BaseModel):
    ended: int


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


def _minutes(text: str) -> int:
    t = time.fromisoformat(text)
    return t.hour * 60 + t.minute


def _hhmm(minute: int | None) -> str:
    return "" if minute is None else f"{minute // 60:02d}:{minute % 60:02d}"


def _summary(hours: list[dict]) -> tuple[int, int]:
    """The earliest start and the latest end of the working days. No working
    day gives an empty window."""
    working = [h for h in hours if h["working"]]
    if not working:
        return 0, 0
    return min(_minutes(h["start"]) for h in working), max(_minutes(h["end"]) for h in working)


def _released(rows: list[dict]) -> list[CrewReleasedJob]:
    return [CrewReleasedJob(job_id=str(r["job_id"]), date=r["date"], service=r["service"],
                            vehicle_id=str(r["vehicle_id"]), registration=r["registration"])
            for r in rows]


def _ex_out(ex: SchedulingCrewException) -> CrewExceptionOut:
    return CrewExceptionOut(id=str(ex.id), date=ex.on_date, kind=ex.kind,
                            start=_hhmm(ex.from_minute))


class CrewService:
    def __init__(self, db: Session):
        self._db = db

    # ---- reads ------------------------------------------------------------

    def _outs(self, rows: list[tuple[CrewMember, Login, str]]) -> list[CrewOut]:
        """Builds the replies for many crew members with a few queries."""
        if not rows:
            return []
        logins = [lg.id for _c, lg, _s in rows]
        sc_by_login = {sc.login_id: sc for sc in self._db.scalars(
            select(SchedulingCrew).where(SchedulingCrew.login_id.in_(logins)))}
        pair_ids = {sc.paired_member_id for sc in sc_by_login.values() if sc.paired_member_id}
        mates: dict[uuid.UUID, CrewMember] = {}
        if pair_ids:
            for sc_id, member in self._db.execute(
                select(SchedulingCrew.id, CrewMember)
                .join(CrewMember, CrewMember.login_id == SchedulingCrew.login_id)
                .where(SchedulingCrew.id.in_(pair_ids))
            ):
                mates[sc_id] = member
        exceptions: dict[uuid.UUID, list[CrewExceptionOut]] = {}
        if sc_by_login:
            for ex in self._db.scalars(
                select(SchedulingCrewException)
                .where(SchedulingCrewException.crew_id.in_([s.id for s in sc_by_login.values()]),
                       SchedulingCrewException.on_date >= today_ist())
                .order_by(SchedulingCrewException.on_date)
            ):
                exceptions.setdefault(ex.crew_id, []).append(_ex_out(ex))
        out = []
        for crew, login, society in rows:
            sc = sc_by_login.get(login.id)
            mate = mates.get(sc.paired_member_id) if sc and sc.paired_member_id else None
            out.append(CrewOut(
                id=str(crew.id), name=crew.name, mobile=crew.mobile,
                society_id=str(crew.society_id), society=society, role=crew.role,
                active=login.active, locked=login.locked,
                working_hours=[DayHours(**h) for h in crew.working_hours],
                paired_member_id=str(mate.id) if mate else None,
                paired_member=mate.name if mate else "",
                exceptions=exceptions.get(sc.id, []) if sc else []))
        return out

    def _out(self, crew: CrewMember, login: Login, society: str) -> CrewOut:
        return self._outs([(crew, login, society)])[0]

    def _out_of(self, crew: CrewMember, login: Login) -> CrewOut:
        return self._out(crew, login, self._db.get(Society, crew.society_id).name)

    def _get(self, crew_id: uuid.UUID) -> tuple[CrewMember, Login]:
        crew = self._db.get(CrewMember, crew_id)
        login = self._db.get(Login, crew.login_id) if crew else None
        if crew is None or login is None:
            raise ApiError("not_found", "This crew member was not found.", 404)
        return crew, login

    def get(self, crew_id: uuid.UUID) -> CrewOut:
        crew, login = self._get(crew_id)
        return self._out_of(crew, login)

    def list(self, society_id: uuid.UUID | None = None) -> list[CrewOut]:
        query = (select(CrewMember, Login, Society.name)
                 .join(Login, Login.id == CrewMember.login_id)
                 .join(Society, Society.id == CrewMember.society_id)
                 .order_by(Society.name, CrewMember.name))
        if society_id is not None:
            query = query.where(CrewMember.society_id == society_id)
        return self._outs([(c, lg, s) for c, lg, s in self._db.execute(query)])

    # ---- the scheduler's record -------------------------------------------

    def _sync(self, crew: CrewMember, login: Login) -> SchedulingCrew:
        """Creates or updates the scheduler's record of this crew member from
        the directory. The pairing is set by the callers."""
        sc = self._db.scalar(select(SchedulingCrew).where(SchedulingCrew.login_id == login.id))
        if sc is None:
            sc = SchedulingCrew(login_id=login.id, society_id=crew.society_id)
            self._db.add(sc)
        start, end = _summary(crew.working_hours)
        sc.society_id = crew.society_id
        sc.role = crew.role
        sc.active = login.active
        sc.working_hours = crew.working_hours
        sc.start_minute, sc.end_minute = start, end
        self._db.flush()
        return sc

    def _member_to_pair(self, member_id: uuid.UUID,
                        society_id: uuid.UUID) -> SchedulingCrew:
        member = self._db.get(CrewMember, member_id)
        if member is None or member.role != "Member" or member.society_id != society_id:
            raise _problem("Choose a Member of the same society.",
                           paired_member_id="Choose a Member of the same society.")
        login = self._db.get(Login, member.login_id)
        if login is None or not login.active:
            raise _problem("Choose a Member who is active.",
                           paired_member_id="This Member is not active.")
        return self._sync(member, login)

    def _trainees_of(self, sc: SchedulingCrew) -> "list[SchedulingCrew]":
        return list(self._db.scalars(
            select(SchedulingCrew).where(SchedulingCrew.paired_member_id == sc.id,
                                         SchedulingCrew.role == "Trainee",
                                         SchedulingCrew.active.is_(True))))

    def _end_sessions(self, login_id: uuid.UUID, reason: str) -> int:
        result = self._db.execute(
            update(AuthSession)
            .where(AuthSession.login_id == login_id, AuthSession.ended_at.is_(None))
            .values(ended_at=utcnow(), ended_reason=reason))
        return result.rowcount or 0

    # ---- onboarding and details -------------------------------------------

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
        mate_sc = None
        if body.role == "Trainee":
            if body.paired_member_id is None:
                raise _problem("Choose the Member this Trainee is paired with.",
                               paired_member_id="Choose a Member.")
            mate_sc = self._member_to_pair(body.paired_member_id, society.id)
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
        self._db.flush()
        # The scheduler's record is made in the same transaction, so a crew
        # member who can sign in can also be given jobs (CRW-SCH-01).
        sc = self._sync(crew, login)
        if mate_sc is not None:
            sc.paired_member_id = mate_sc.id
        self._db.add(AuthEvent(login_id=login.id, kind="crew_created"))
        self._db.commit()
        return CrewPassword(crew=self._out(crew, login, society.name),
                            login_id=mobile, password=password)

    def edit(self, crew_id: uuid.UUID, body: CrewEdit) -> CrewOut:
        """Name and mobile number (ADM-CRW-02). The mobile number is the login
        ID, so a new one signs the crew member out everywhere. The society
        does not change (ADM-CRW-13)."""
        crew, login = self._get(crew_id)
        if body.name is not None:
            name = " ".join(body.name.split())
            if not name or not any(ch.isalpha() for ch in name) or len(name) > 80:
                raise _problem("Enter the crew member's name.", name="Enter a name.")
            crew.name = login.display_name = name
        if body.mobile is not None and body.mobile.strip() != crew.mobile:
            mobile = body.mobile.strip()
            if not _MOBILE.fullmatch(mobile):
                raise _problem("The mobile number must have 10 digits.",
                               mobile="Use a 10-digit mobile number.")
            if self._db.scalar(select(Login.id).where(Login.login_id == mobile)) is not None:
                raise ApiError("mobile_in_use",
                               "This mobile number already belongs to a login.", 409,
                               {"mobile": "Already in use."})
            crew.mobile = login.login_id = mobile
            self._end_sessions(login.id, "login_changed")
            self._db.add(AuthEvent(login_id=login.id, kind="login_id_changed_by_admin"))
        self._db.commit()
        return self._out_of(crew, login)

    def change_role(self, crew_id: uuid.UUID, body: CrewRoleChange) -> CrewChange:
        """Manager, Member or Trainee at any time (ADM-CRW-03, ADM-CRW-16). A
        Member whose Trainees are still paired, or a Trainee with no Member to
        pair with, is refused (ADM-CRW-19)."""
        if body.role not in CREW_ROLES:
            raise _problem("Choose Manager, Member or Trainee.", role="Choose a role.")
        crew, login = self._get(crew_id)
        sc = self._sync(crew, login)
        released: list[dict] = []
        if body.role != crew.role:
            if crew.role == "Member" and self._trainees_of(sc):
                raise ApiError(
                    "trainees_paired",
                    "Pair this Member's Trainees with another Member first.", 409,
                    {"role": "Trainees are paired with this Member."})
            mate_sc = None
            if body.role == "Trainee":
                if body.paired_member_id is None:
                    raise _problem("Choose the Member this Trainee is paired with.",
                                   paired_member_id="Choose a Member.")
                mate_sc = self._member_to_pair(body.paired_member_id, crew.society_id)
            crew.role = body.role
            self._sync(crew, login)
            sc.paired_member_id = mate_sc.id if mate_sc is not None else None
            if body.role == "Trainee":
                # A Trainee is never assigned directly (ADM-CRW-14).
                released = scheduling.release_unfit(self._db, sc, today_ist())
            self._db.add(AuthEvent(login_id=login.id, kind="crew_role_changed"))
        self._db.commit()
        return CrewChange(crew=self._out_of(crew, login), released_jobs=_released(released))

    def pair(self, crew_id: uuid.UUID, body: CrewPairChange) -> CrewOut:
        """Pairs a Trainee with a Member of the same society, or changes the
        Member (ADM-CRW-19)."""
        crew, login = self._get(crew_id)
        if crew.role != "Trainee":
            raise ApiError("not_a_trainee", "Only a Trainee is paired with a Member.", 409)
        mate_sc = self._member_to_pair(body.paired_member_id, crew.society_id)
        sc = self._sync(crew, login)
        sc.paired_member_id = mate_sc.id
        self._db.add(AuthEvent(login_id=login.id, kind="crew_paired"))
        self._db.commit()
        return self._out_of(crew, login)

    def set_hours(self, crew_id: uuid.UUID, body: CrewHoursChange) -> CrewChange:
        """New working hours, applied from today on (ADM-CRW-05). Open jobs
        that no longer fit go to the Needs scheduling list (ADM-CRW-12)."""
        hours = check_hours(body.working_hours)
        crew, login = self._get(crew_id)
        crew.working_hours = hours
        sc = self._sync(crew, login)
        released = scheduling.release_unfit(self._db, sc, today_ist())
        self._db.commit()
        return CrewChange(crew=self._out_of(crew, login), released_jobs=_released(released))

    # ---- exceptions -------------------------------------------------------

    def _check_kind(self, kind: str, start: str) -> int | None:
        if kind not in EXCEPTION_KINDS:
            raise _problem("Choose Sick, Leave or Late start.", kind="Choose a type.")
        if kind != "Late start":
            return None
        if not _TIME.fullmatch(start):
            raise _problem("Give the time the crew member can start.", start="Use HH:MM.")
        return _minutes(start)

    def _upcoming(self, sc: SchedulingCrew, from_date: date) -> "list[CrewExceptionOut]":
        rows = self._db.scalars(
            select(SchedulingCrewException)
            .where(SchedulingCrewException.crew_id == sc.id,
                   SchedulingCrewException.on_date >= from_date)
            .order_by(SchedulingCrewException.on_date))
        return [_ex_out(e) for e in rows]

    def list_exceptions(self, crew_id: uuid.UUID,
                        from_date: date | None) -> "list[CrewExceptionOut]":
        crew, login = self._get(crew_id)
        sc = self._sync(crew, login)
        self._db.commit()
        return self._upcoming(sc, from_date or today_ist())

    def _exception_of(self, sc: SchedulingCrew,
                      exception_id: uuid.UUID) -> SchedulingCrewException:
        ex = self._db.get(SchedulingCrewException, exception_id)
        if ex is None or ex.crew_id != sc.id:
            raise ApiError("not_found", "This exception was not found.", 404)
        return ex

    def _result(self, crew: CrewMember, login: Login, sc: SchedulingCrew,
                released: "list[dict]") -> CrewExceptionResult:
        return CrewExceptionResult(
            crew=self._out_of(crew, login), exceptions=self._upcoming(sc, today_ist()),
            released_jobs=_released(released))

    def add_exceptions(self, crew_id: uuid.UUID, body: CrewExceptionNew) -> CrewExceptionResult:
        """One date or a date range (ADM-CRW-08). Capacity reads the rows, so
        it is current at once (ADM-CRW-11)."""
        from_minute = self._check_kind(body.kind, body.start)
        to_date = body.to_date or body.from_date
        if to_date < body.from_date:
            raise _problem("The last date is before the first date.",
                           to_date="Choose a date on or after the first date.")
        if body.from_date < today_ist():
            raise _problem("Choose today or a later date.",
                           from_date="Choose today or a later date.")
        if (to_date - body.from_date).days >= MAX_RANGE_DAYS:
            raise _problem(f"A range can be at most {MAX_RANGE_DAYS} days.",
                           to_date="The range is too long.")
        crew, login = self._get(crew_id)
        sc = self._sync(crew, login)
        days = [body.from_date + timedelta(days=i)
                for i in range((to_date - body.from_date).days + 1)]
        taken = self._db.scalars(
            select(SchedulingCrewException.on_date)
            .where(SchedulingCrewException.crew_id == sc.id,
                   SchedulingCrewException.on_date.in_(days))).all()
        if taken:
            raise ApiError(
                "exception_exists",
                "There is already an exception on "
                + ", ".join(d.isoformat() for d in sorted(taken))
                + ". Edit or remove it first.", 409, {"from_date": "Dates are taken."})
        for day in days:
            self._db.add(SchedulingCrewException(
                crew_id=sc.id, on_date=day, kind=body.kind, from_minute=from_minute))
        self._db.flush()
        released = scheduling.release_unfit(self._db, sc, today_ist())
        self._db.commit()
        return self._result(crew, login, sc, released)

    def edit_exception(self, crew_id: uuid.UUID, exception_id: uuid.UUID,
                       body: CrewExceptionEdit) -> CrewExceptionResult:
        crew, login = self._get(crew_id)
        sc = self._sync(crew, login)
        ex = self._exception_of(sc, exception_id)
        kind = body.kind if body.kind is not None else ex.kind
        start = body.start if body.start is not None else _hhmm(ex.from_minute)
        ex.from_minute = self._check_kind(kind, start)
        ex.kind = kind
        self._db.flush()
        released = scheduling.release_unfit(self._db, sc, today_ist())
        self._db.commit()
        return self._result(crew, login, sc, released)

    def remove_exception(self, crew_id: uuid.UUID,
                         exception_id: uuid.UUID) -> CrewExceptionResult:
        crew, login = self._get(crew_id)
        sc = self._sync(crew, login)
        self._db.delete(self._exception_of(sc, exception_id))
        self._db.commit()
        return self._result(crew, login, sc, [])

    # ---- deactivate and reactivate ----------------------------------------

    def deactivate(self, crew_id: uuid.UUID, body: CrewDeactivate) -> CrewChange:
        """A crew member who has left: no capacity, no new jobs, no sign-in
        (ADM-CRW-15, CRW-ACC-08). Records stay. Open jobs from today on go to
        Needs scheduling, but only when the admin asked for it, and a job in
        progress stops the change."""
        crew, login = self._get(crew_id)
        sc = self._sync(crew, login)
        if not login.active:
            return CrewChange(crew=self._out_of(crew, login))
        if self._trainees_of(sc):
            raise ApiError("trainees_paired",
                           "Pair this Member's Trainees with another Member first.", 409)
        today = today_ist()
        in_progress = self._db.scalar(
            select(func.count()).select_from(Job)
            .where(Job.crew_id == sc.id, Job.status == "In progress"))
        if in_progress:
            raise ApiError("job_in_progress",
                           "This crew member has a job in progress. Wait until it is done.",
                           409)
        frozen_open = self._db.scalar(
            select(func.count()).select_from(Job)
            .join(Visit, Job.visit_id == Visit.id)
            .join(Schedule, Visit.schedule_id == Schedule.id)
            .where(Job.crew_id == sc.id, Job.status == "Scheduled",
                   Visit.date >= today, Schedule.status == "Frozen"))
        if frozen_open and not body.release_jobs:
            raise ApiError(
                "has_open_jobs",
                f"This crew member holds {frozen_open} frozen "
                f"job{'s' if frozen_open != 1 else ''}. Send "
                f"{'them' if frozen_open != 1 else 'it'} to Needs scheduling to continue.",
                409, {"release_jobs": "Open jobs need to be released."})
        login.active = False
        sc = self._sync(crew, login)
        released = scheduling.release_unfit(self._db, sc, today)
        self._end_sessions(login.id, "deactivated")
        self._db.add(AuthEvent(login_id=login.id, kind="crew_deactivated"))
        self._db.commit()
        return CrewChange(crew=self._out_of(crew, login), released_jobs=_released(released))

    def reactivate(self, crew_id: uuid.UUID) -> CrewOut:
        crew, login = self._get(crew_id)
        login.active = True
        self._sync(crew, login)
        self._db.add(AuthEvent(login_id=login.id, kind="crew_reactivated"))
        self._db.commit()
        return self._out_of(crew, login)

    # ---- sessions (ADM-CRW-21) ---------------------------------------------

    def sessions(self, crew_id: uuid.UUID) -> "list[CrewSessionOut]":
        _crew, login = self._get(crew_id)
        rows = self._db.scalars(
            select(AuthSession)
            .where(AuthSession.login_id == login.id, AuthSession.ended_at.is_(None))
            .order_by(AuthSession.last_used_at.desc()))
        return [CrewSessionOut(id=str(s.id), channel=s.channel, signed_in_at=s.created_at,
                               last_active_at=s.last_used_at) for s in rows]

    def end_session(self, crew_id: uuid.UUID, session_id: uuid.UUID) -> CrewSessionsEnded:
        _crew, login = self._get(crew_id)
        session = self._db.get(AuthSession, session_id)
        if session is None or session.login_id != login.id or session.ended_at is not None:
            raise ApiError("not_found", "This session was not found.", 404)
        session.ended_at, session.ended_reason = utcnow(), "admin_signed_out"
        self._db.add(AuthEvent(login_id=login.id, kind="signed_out_by_admin"))
        self._db.commit()
        return CrewSessionsEnded(ended=1)

    def end_all_sessions(self, crew_id: uuid.UUID) -> CrewSessionsEnded:
        _crew, login = self._get(crew_id)
        ended = self._end_sessions(login.id, "admin_signed_out")
        self._db.add(AuthEvent(login_id=login.id, kind="signed_out_by_admin"))
        self._db.commit()
        return CrewSessionsEnded(ended=ended)

    # ---- password and lock ------------------------------------------------

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
        self._end_sessions(login.id, "password_reset")
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
        return self._out_of(crew, login)

    def profile(self, login_id: uuid.UUID) -> CrewProfile:
        crew = self._db.scalar(select(CrewMember).where(CrewMember.login_id == login_id))
        if crew is None:
            raise ApiError("no_crew_record",
                           "Your details are not set up yet. Contact Priveo.", 404)
        return CrewProfile(
            name=crew.name, mobile=crew.mobile,
            society=self._db.get(Society, crew.society_id).name, role=crew.role,
            working_hours=[DayHours(**h) for h in crew.working_hours])
