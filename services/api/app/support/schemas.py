import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class SupportContact(BaseModel):
    helpline: str
    whatsapp: str
    hours: str
    # Complaints not yet Resolved, for the Support screen (SUP-01).
    complaints_in_progress: int


class OptionOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str = ""


class OptionAdmin(OptionOut):
    kind: str
    sort_order: int
    active: bool


class SupportOptionsOut(BaseModel):
    issue_categories: list[str]
    feedback_categories: list[OptionOut]
    positive_tags: list[OptionOut]
    checkin_categories: list[OptionOut]


class OptionCreate(BaseModel):
    kind: str
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=300)


class OptionPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    active: bool | None = None
    sort_order: int | None = None


class ComplaintCreate(BaseModel):
    category: str
    description: str = Field(min_length=1, max_length=2000)
    visit_id: str | None = Field(default=None, max_length=64)
    photo_keys: list[str] = Field(default_factory=list, max_length=10)


class MessageCreate(BaseModel):
    note: str = Field(min_length=1, max_length=1000)


class StatusChange(BaseModel):
    status: str
    note: str = Field(default="", max_length=1000)


class UpdateOut(BaseModel):
    id: uuid.UUID
    author_role: str
    note: str
    status: str | None
    created_at: datetime


class ComplaintSummary(BaseModel):
    id: uuid.UUID
    number: int
    # "#C-0007" (ISS-06).
    display_id: str
    category: str
    description: str
    status: str
    visit_id: str | None
    created_at: datetime
    updated_at: datetime
    latest_note: str | None


class ComplaintDetail(ComplaintSummary):
    # Upload IDs of the photos (ISS-04), and signed read URLs in the same order.
    photo_keys: list[str]
    photo_urls: list[str] = []
    updates: list[UpdateOut]


class AdminComplaintSummary(ComplaintSummary):
    vehicle: str = ""
    customer_name: str
    society: str
    flat: str
    # Raised for more than 4 hours (ADM-CMP-06).
    overdue: bool


class AdminComplaintDetail(AdminComplaintSummary):
    photo_keys: list[str]
    photo_urls: list[str] = []
    updates: list[UpdateOut]


class FeedbackCreate(BaseModel):
    category: str | None = Field(default=None, max_length=80)
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str = Field(default="", max_length=1000)
    testimonial_permission: bool = False


class FeedbackOut(BaseModel):
    id: uuid.UUID
    created_at: datetime


class FeedbackAdmin(BaseModel):
    id: uuid.UUID
    category: str | None
    rating: int | None
    comment: str
    testimonial_permission: bool
    customer_name: str
    society: str
    created_at: datetime


class RatingCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list, max_length=12)
    comment: str = Field(default="", max_length=1000)
    testimonial_permission: bool = False


class RatingOut(BaseModel):
    visit_id: str
    rating: int
    tags: list[str]
    comment: str
    testimonial_permission: bool
    created_at: datetime


class RatingAdmin(RatingOut):
    society: str


class RatingsReport(BaseModel):
    count: int
    average: float | None
    tag_counts: dict[str, int]
    items: list[RatingAdmin]


class CrewRatings(BaseModel):
    """General ratings of visits, with no names, tags or comments (CRW-RAT-01)."""

    period_days: int
    count: int
    average: float | None
    stars: dict[str, int]


class PendingCheckIn(BaseModel):
    subscription_id: uuid.UUID
    vehicle_id: uuid.UUID
    vehicle_label: str
    cycle_start: date
    renewal_date: date


class CheckInAnswer(BaseModel):
    category: str
    rating: int = Field(ge=1, le=5)


class CheckInCreate(BaseModel):
    subscription_id: uuid.UUID
    answers: list[CheckInAnswer] = Field(min_length=1, max_length=20)
    comment: str = Field(default="", max_length=1000)


class CheckInOut(BaseModel):
    id: uuid.UUID
    cycle_start: date


class CheckInAdmin(BaseModel):
    id: uuid.UUID
    customer_name: str
    society: str
    vehicle_label: str
    cycle_start: date
    answers: list[CheckInAnswer]
    comment: str
    created_at: datetime


class CheckInsReport(BaseModel):
    category_averages: dict[str, float]
    items: list[CheckInAdmin]


class AlertOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    ref_type: str | None
    ref_id: str | None
    created_at: datetime
    read: bool


class AlertList(BaseModel):
    unread_count: int
    items: list[AlertOut]
