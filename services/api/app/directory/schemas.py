import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ---- societies -------------------------------------------------------------------

class DirectorySocietyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sector: str = Field(default="", max_length=80)
    city: str = Field(default="", max_length=80)
    # Empty takes B1 to B4 (ONB-13).
    parking_basements: list[str] | None = None


class DirectorySocietyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    sector: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=80)
    parking_basements: list[str] | None = None


class DirectorySocietyOut(BaseModel):
    id: uuid.UUID
    name: str
    sector: str
    city: str
    active: bool
    parking_basements: list[str]
    # Active vehicles in the society (ADM-REF-02).
    cars_serviced: int
    # What blocks a deactivation (ADM-REF-06).
    active_subscriptions: int
    active_crew: int


class DirectoryCustomerSocietyOut(BaseModel):
    id: uuid.UUID
    name: str
    sector: str
    city: str
    cars_serviced: int
    parking_basements: list[str]


# ---- plans -----------------------------------------------------------------------

class DirectoryPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    monthly_price_rupees: int = Field(gt=0, le=1_000_000)
    list_price_rupees: int | None = Field(default=None, gt=0, le=1_000_000)
    includes_interior: bool = False
    inclusions: list[str] = Field(default_factory=list, max_length=20)
    badge: str = Field(default="", max_length=40)
    sort_order: int = Field(default=0, ge=0, le=1000)


class DirectoryPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    monthly_price_rupees: int | None = Field(default=None, gt=0, le=1_000_000)
    list_price_rupees: int | None = Field(default=None, gt=0, le=1_000_000)
    # Send true to remove the struck-through price.
    clear_list_price: bool = False
    includes_interior: bool | None = None
    inclusions: list[str] | None = Field(default=None, max_length=20)
    badge: str | None = Field(default=None, max_length=40)
    sort_order: int | None = Field(default=None, ge=0, le=1000)


class DirectoryPlanOut(BaseModel):
    id: uuid.UUID
    # The plan ID shown to admins, like PLN-0001.
    code: str
    name: str
    monthly_price_rupees: int
    list_price_rupees: int | None
    includes_interior: bool
    inclusions: list[str]
    badge: str
    sort_order: int
    active: bool
    # Subscriptions on this plan that are not Inactive.
    active_subscriptions: int


class DirectoryCustomerPlanOut(BaseModel):
    id: uuid.UUID
    name: str
    monthly_price_rupees: int
    list_price_rupees: int | None
    includes_interior: bool
    inclusions: list[str]
    badge: str


# ---- vehicle catalogue -----------------------------------------------------------

class DirectoryVehicleCreate(BaseModel):
    make: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=80)
    variant: str = Field(default="", max_length=80)
    category: str = Field(min_length=1, max_length=40)


class DirectoryVehicleUpdate(BaseModel):
    make: str | None = Field(default=None, min_length=1, max_length=60)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    variant: str | None = Field(default=None, max_length=80)
    category: str | None = Field(default=None, min_length=1, max_length=40)


class DirectoryVehicleOut(BaseModel):
    id: uuid.UUID
    make: str
    model: str
    variant: str
    category: str
    active: bool


class DirectoryCustomerVehicleOut(BaseModel):
    id: uuid.UUID
    make: str
    model: str
    variant: str
    category: str


# ---- services and checklists -----------------------------------------------------

class DirectoryServiceOut(BaseModel):
    name: str
    duration_minutes: int
    min_photos: int
    min_videos: int


class DirectoryServiceUpdate(BaseModel):
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    min_photos: int | None = Field(default=None, ge=0, le=20)
    min_videos: int | None = Field(default=None, ge=0, le=10)


class DirectoryChecklistItemOut(BaseModel):
    id: uuid.UUID
    service: str
    key: str
    label: str
    sort_order: int
    active: bool


class DirectoryChecklistOut(BaseModel):
    service: str
    min_photos: int
    min_videos: int
    items: list[DirectoryChecklistItemOut]


class DirectoryChecklistItemCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)


class DirectoryChecklistItemUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=120)


class DirectoryChecklistItemRenamed(BaseModel):
    """A rename keeps the old item (deactivated, readable on past visits) and
    adds a new one with the new label (ADM-CHK-05)."""
    item: DirectoryChecklistItemOut
    replaced_id: uuid.UUID | None = None


class DirectoryOrder(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1)


# ---- working slots ---------------------------------------------------------------

class DirectorySlotCreate(BaseModel):
    service: str
    start: str = Field(description="HH:MM")
    end: str = Field(description="HH:MM, or 24:00 for midnight")
    days: list[str] = Field(min_length=1, description="Monday to Sunday")


class DirectorySlotUpdate(BaseModel):
    start: str | None = None
    end: str | None = None
    days: list[str] | None = Field(default=None, min_length=1)


class DirectorySlotOut(BaseModel):
    id: uuid.UUID
    society_id: uuid.UUID
    service: str
    start: str
    end: str
    days: list[str]


# ---- reasons ---------------------------------------------------------------------

class DirectoryReasonCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)


class DirectoryReasonUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=120)


class DirectoryReasonOut(BaseModel):
    id: uuid.UUID
    key: str
    label: str
    sort_order: int
    active: bool


# ---- settings --------------------------------------------------------------------

class DirectorySettingOut(BaseModel):
    key: str
    label: str
    group: str
    kind: str
    # A whole number for kind "int", else text.
    value: Any
    is_default: bool
    updated_at: datetime | None
    updated_by: uuid.UUID | None


class DirectorySettingPut(BaseModel):
    value: Any


class DirectorySettingsPatch(BaseModel):
    values: dict[str, Any] = Field(min_length=1)


# ---- add-on catalogue ------------------------------------------------------------

class DirectoryAddonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    service: str = "Deep Spa"
    price_rupees: int = Field(ge=0, le=1_000_000)
    list_price_rupees: int | None = Field(default=None, ge=0, le=1_000_000)
    # Empty takes the service's duration.
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    sort_order: int = Field(default=0, ge=0, le=1000)


class DirectoryAddonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    price_rupees: int | None = Field(default=None, ge=0, le=1_000_000)
    list_price_rupees: int | None = Field(default=None, ge=0, le=1_000_000)
    clear_list_price: bool = False
    duration_minutes: int | None = Field(default=None, ge=5, le=480)
    sort_order: int | None = Field(default=None, ge=0, le=1000)


class DirectoryAddonOut(BaseModel):
    id: uuid.UUID
    # The add-on ID shown to admins, like ADN-0001.
    code: str
    name: str
    description: str
    service: str
    price_rupees: int
    list_price_rupees: int | None
    duration_minutes: int
    sort_order: int
    active: bool


class DirectoryCustomerAddonOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    service: str
    price_rupees: int
    list_price_rupees: int | None
    duration_minutes: int


# ---- audit -----------------------------------------------------------------------

class DirectoryAuditOut(BaseModel):
    id: uuid.UUID
    at: datetime
    admin_login_id: uuid.UUID | None
    entity: str
    entity_id: str
    action: str
    detail: dict
