import datetime as dt

from pydantic import BaseModel


class AddonOffer(BaseModel):
    # The catalogue ID (ADN-0001); empty for the built-in Deep Spa fallback.
    code: str = ""
    service: str
    name: str
    description: str
    price_rupees: int
    list_price_rupees: int | None
    duration_minutes: int


class AddonRequestIn(BaseModel):
    service: str = "Deep Spa"
    # The add-on bought, by its catalogue ID. When given it decides the service.
    addon: str = ""
    date: dt.date
    # HH:MM in 30-minute steps (ADD-04).
    finish_by: str


class AddonChangeIn(BaseModel):
    date: dt.date | None = None
    finish_by: str | None = None


class StandaloneIn(BaseModel):
    """Owner decision: an owned no-subscription vehicle uses the Spa rules."""

    service: str = "Deep Spa"
    addon: str = ""
    vehicle_id: str
    date: dt.date
    finish_by: str
    contact_mobile: str = ""
    notes: str = ""


class AddonOut(BaseModel):
    id: str
    service: str
    addon_name: str = ""
    vehicle_id: str | None
    standalone: bool
    date: dt.date
    finish_by: str
    status: str
    price_rupees: int | None
    payment_id: str | None
    payment_status: str | None
    can_change: bool
    created_at: dt.datetime
    requested_date: dt.date | None = None
    requested_finish_by: str | None = None
    change_requested: bool = False
    crew_name: str | None = None
    start_time: str | None = None
    visit_id: str | None = None


class AddonsOut(BaseModel):
    offers: list[AddonOffer]
    requests: list[AddonOut]


class AdminAddonOut(AddonOut):
    customer_name: str
    flat: str
    society: str
    vehicle: str
    contact_mobile: str
    notes: str


class AdminAddonIn(BaseModel):
    status: str | None = None
    date: dt.date | None = None
    finish_by: str | None = None
    resolve_change: bool = False
    reject_change: bool = False


class AdminAddonCreate(AddonRequestIn):
    vehicle_id: str
