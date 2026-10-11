"""Crew responses never carry a customer name or mobile number (CRW-SCH-13)."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class VehicleInfo(BaseModel):
    id: str
    registration: str
    make: str
    model: str
    category: str


class CrewRef(BaseModel):
    id: str
    name: str


class CrewJobCard(BaseModel):
    id: str
    visit_id: str
    visit_status: str
    date: date
    service: str
    status: str
    vehicle: VehicleInfo
    society: str
    # For example "B2-14". Empty when it is not on file.
    parking: str
    # "HH:MM", the assigned slot (CRW-SCH-02).
    start_time: str | None
    # "HH:MM", the time the job must be finished by (CRW-SCH-04).
    finish_by: str | None
    checklist_total: int
    checklist_done: int
    # Who the job is on. Shown to a Manager.
    assigned_to: CrewRef | None


class VisitList(BaseModel):
    date: date | None
    society: str
    total: int
    done: int
    left: int
    jobs: list[CrewJobCard]


class ChecklistItem(BaseModel):
    id: str
    label: str
    checked_at: datetime | None


class UploadInfo(BaseModel):
    id: str
    kind: str
    stage: str | None
    status: str


class Requirements(BaseModel):
    photos_required: int
    videos_required: int
    photos_confirmed: int
    videos_confirmed: int
    # Uploads asked for and not yet confirmed.
    pending_uploads: int


class Outcome(BaseModel):
    kind: str
    reason_key: str | None
    note: str
    at: datetime


class JobDetail(BaseModel):
    job: CrewJobCard
    checklist: list[ChecklistItem]
    requirements: Requirements
    uploads: list[UploadInfo]
    # What stops "Mark complete", in words for the screen.
    missing: list[str]
    can_complete: bool
    outcome: Outcome | None
    started_at: datetime | None
    finished_at: datetime | None


class Reason(BaseModel):
    key: str
    label: str


class ChecklistTick(BaseModel):
    checked: bool


class CouldNotComplete(BaseModel):
    reason_key: str
    note: str = Field(default="", max_length=500)
    # A confirmed photo uploaded with purpose "reason" (optional).
    upload_id: str | None = None


class Reassign(BaseModel):
    crew_id: str


class ProfilePhoto(BaseModel):
    upload_id: str


class PhotoState(BaseModel):
    upload_id: str | None


class TeamMember(BaseModel):
    id: str
    name: str
    role: str
    jobs: list[CrewJobCard]


class ManagerSchedule(BaseModel):
    date: date
    society: str
    crew: list[TeamMember]
    # Jobs not yet on anyone.
    unassigned: list[CrewJobCard]
