"""What a Manager sends and gets for attendance, working hours and the
reassign checks (CRW-MGR-03 to CRW-MGR-05). Nothing here has a customer's name
or mobile number, and no crew mobile number either."""
from datetime import date

from pydantic import BaseModel

from app.crew.service import DayHours


class CrewManagerAttendanceEntry(BaseModel):
    crew_id: str
    name: str
    role: str
    # Whether the weekday's hours make this a working day, and the hours.
    working: bool
    # "HH:MM", empty on a day off.
    start: str = ""
    end: str = ""
    # present | Sick | Leave | Late start
    status: str
    # "HH:MM" for a Late start, empty otherwise.
    late_start: str = ""
    # Jobs still Scheduled for this crew member on the day.
    open_jobs: int = 0


class CrewManagerAttendance(BaseModel):
    date: date
    society: str
    crew: list[CrewManagerAttendanceEntry]


class CrewManagerAttendanceSet(BaseModel):
    # present removes the exception. Sick, Leave and Late start add or replace it.
    status: str
    from_date: date
    to_date: date | None = None
    # Late start only: "HH:MM".
    start: str = ""


class CrewManagerReleasedJob(BaseModel):
    job_id: str
    date: date
    service: str
    registration: str
    # True when the scheduler found another crew member at once. False means
    # the job is on the Needs scheduling list.
    reassigned: bool = False


class CrewManagerAttendanceResult(BaseModel):
    attendance: CrewManagerAttendance
    released_jobs: list[CrewManagerReleasedJob] = []


class CrewManagerHours(BaseModel):
    crew_id: str
    name: str
    role: str
    working_hours: list[DayHours]


class CrewManagerHoursSet(BaseModel):
    working_hours: list[DayHours]


class CrewManagerHoursResult(BaseModel):
    hours: CrewManagerHours
    released_jobs: list[CrewManagerReleasedJob] = []


class CrewManagerReassignOption(BaseModel):
    crew_id: str
    name: str
    role: str
    can_assign: bool
    # Empty when the job can go to this person. Otherwise a code such as
    # crew_not_working, outside_hours, overlap or no_slot, and the words.
    problem_code: str = ""
    problem: str = ""
