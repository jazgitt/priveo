import datetime as dt

from pydantic import BaseModel


class AddonOffer(BaseModel):
    service: str
    name: str
    description: str
    price_rupees: int
    list_price_rupees: int | None
    duration_minutes: int


class AddonRequestIn(BaseModel):
    service: str = "Deep Spa"
    date: dt.date
    # HH:MM in 30-minute steps (ADD-04).
    finish_by: str


class AddonChangeIn(BaseModel):
    date: dt.date | None = None
    finish_by: str | None = None


class StandaloneIn(BaseModel):
    """DERIVED / OPEN (ADD-15): a standalone Deep Spa is only a request with
    contact details. Priveo calls to agree the date, the price and the payment."""

    service: str = "Deep Spa"
    vehicle_id: str | None = None
    date: dt.date
    finish_by: str
    contact_mobile: str = ""
    notes: str = ""


class AddonOut(BaseModel):
    id: str
    service: str
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
