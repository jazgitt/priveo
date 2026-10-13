"""The system settings: which keys exist, their type and their rules.

Values are stored as text in `system_settings`. `parse` checks a value and
returns the text to store; `typed` turns stored text into the Python value.
A key with no stored row falls back to `default_for`, which reads the older
environment configuration (SUPPORT_*, MONEY_*) so nothing changes until the
admin saves a value.
"""
import re
from dataclasses import dataclass
from typing import Any

PHONE_RE = re.compile(r"^\+?\d{10,15}$")
UPI_RE = re.compile(r"^[A-Za-z0-9._-]{2,}@[A-Za-z][A-Za-z0-9.-]{1,}$")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@dataclass(frozen=True)
class SettingDef:
    key: str
    kind: str  # text | phone | upi | url | gstin | int | time | code
    label: str
    group: str
    default: Any = ""
    minimum: int = 0
    maximum: int = 10_000_000
    max_length: int = 200
    required: bool = True


DEFINITIONS: tuple[SettingDef, ...] = (
    SettingDef("schedule.auto_enabled", "int", "Automatic planning enabled (0/1)", "automation", 0, minimum=0, maximum=1),
    SettingDef("schedule.auto_time", "time", "Automatic planning time (IST)", "automation", "", required=False),
    # ADM-SET-03
    SettingDef("support.helpline", "phone", "Helpline number", "support", "+910000000000"),
    SettingDef("support.whatsapp", "phone", "WhatsApp number", "support", "+910000000000"),
    SettingDef("support.hours", "text", "Support hours", "support", "6 AM to 10 PM",
               max_length=80),
    # ADM-SET-02
    SettingDef("payment.upi_id", "upi", "UPI ID", "payment", "priveo-placeholder@upi"),
    SettingDef("payment.upi_payee_name", "text", "UPI payee name", "payment",
               "Priveo (placeholder)", max_length=80),
    SettingDef("payment.upi_qr_url", "url", "UPI QR code image address", "payment", "",
               required=False),
    # ADM-SET-04
    SettingDef("invoice.seller_name", "text", "Seller legal name", "invoice",
               "Priveo (placeholder seller)", max_length=120),
    SettingDef("invoice.seller_address", "text", "Seller address", "invoice",
               "Placeholder address", max_length=300),
    SettingDef("invoice.seller_gstin", "gstin", "Seller GSTIN", "invoice", "00PLACEHOLDER0Z0"),
    # ADM-SCH-18, ADM-SCH-25, SCHED-01, ONB-16
    SettingDef("schedule.period", "text", "Scheduling period", "schedule", "Weekly"),
    SettingDef("schedule.week_start", "int", "Week start (Monday 0, Sunday 6)", "schedule", 6,
               minimum=0, maximum=6),
    SettingDef("schedule.unfreeze_code", "code", "Secret code that unfreezes a schedule",
               "schedule", "unfreeze", max_length=40),
    SettingDef("schedule.freeze_hour", "int", "Freeze hour the day before (24-hour)",
               "schedule", 20, minimum=0, maximum=23),
    SettingDef("schedule.customer_change_hour", "int",
               "Hour the day before after which customers cannot change (24-hour)",
               "schedule", 21, minimum=0, maximum=23),
    SettingDef("schedule.default_cutoff_time", "time", "Default service cutoff time",
               "schedule", "09:00"),
    SettingDef("schedule.cutoff_step_minutes", "int", "Cutoff time step in minutes",
               "schedule", 30, minimum=5, maximum=120),
    # Billing: SUB-09, SUB-11, rule 26.
    SettingDef("billing.cycle_days", "int", "Billing cycle in days", "billing", 30,
               minimum=1, maximum=366),
    SettingDef("billing.pay_ahead_days", "int", "Days before renewal a payment is created",
               "billing", 7, minimum=0, maximum=60),
    SettingDef("billing.inactive_after_days", "int",
               "Days a plan payment is Over due before the subscription is Inactive",
               "billing", 7, minimum=0, maximum=90),
    # CHK-01
    SettingDef("support.checkin_days_before", "int",
               "Days before the cycle ends that the check-in is due", "support", 4,
               minimum=0, maximum=30),
)

BY_KEY: dict[str, SettingDef] = {d.key: d for d in DEFINITIONS}

# Settings whose older home is environment configuration.
_ENV_ATTRS = {
    "support.helpline": ("support", "support_helpline"),
    "support.whatsapp": ("support", "support_whatsapp"),
    "support.hours": ("support", "support_hours"),
    "payment.upi_id": ("money", "upi_id"),
    "payment.upi_payee_name": ("money", "upi_payee_name"),
    "payment.upi_qr_url": ("money", "upi_qr_url"),
    "invoice.seller_name": ("money", "seller_name"),
    "invoice.seller_address": ("money", "seller_address"),
    "invoice.seller_gstin": ("money", "seller_gstin"),
}


def default_for(key: str) -> str:
    """The text a key has when nothing is stored: the environment value for
    the keys that used to be configuration, else the registry default."""
    definition = BY_KEY[key]
    if key in _ENV_ATTRS:
        which, attr = _ENV_ATTRS[key]
        if which == "support":
            from app.support.config import get_support_settings
            return str(getattr(get_support_settings(), attr))
        from app.billing.config import get_money_settings
        return str(getattr(get_money_settings(), attr))
    return str(definition.default)


def parse(definition: SettingDef, raw: Any) -> str:
    """Check a value and return the text to store. Raises ValueError with a
    message for the admin."""
    if isinstance(raw, bool) or raw is None:
        raise ValueError("Enter a value.")
    if definition.kind == "int":
        if isinstance(raw, str):
            if not re.fullmatch(r"-?\d+", raw.strip()):
                raise ValueError("Enter a whole number.")
            raw = int(raw.strip())
        if not isinstance(raw, int):
            raise ValueError("Enter a whole number.")
        if not definition.minimum <= raw <= definition.maximum:
            raise ValueError(
                f"Enter a number from {definition.minimum} to {definition.maximum}.")
        return str(raw)
    if not isinstance(raw, str):
        raise ValueError("Enter text.")
    text = raw.strip()
    if definition.key == "schedule.period" and text not in ("Daily", "Weekly", "Monthly"):
        raise ValueError("Choose Daily, Weekly or Monthly.")
    if not text:
        if definition.required:
            raise ValueError("This cannot be empty.")
        return ""
    if len(text) > definition.max_length:
        raise ValueError(f"Use at most {definition.max_length} characters.")
    if definition.kind == "phone":
        compact = re.sub(r"[\s-]", "", text)
        if not PHONE_RE.match(compact):
            raise ValueError("Enter a phone number with 10 to 15 digits.")
        return compact
    if definition.kind == "upi":
        if not UPI_RE.match(text):
            raise ValueError("Enter a UPI ID such as name@bank.")
        return text
    if definition.kind == "url":
        if not re.match(r"^https?://\S+$", text):
            raise ValueError("Enter an address that starts with http:// or https://.")
        return text
    if definition.kind == "gstin":
        text = text.upper()
        if not GSTIN_RE.match(text):
            raise ValueError("Enter a 15-character GSTIN.")
        return text
    if definition.kind == "time":
        if not TIME_RE.match(text):
            raise ValueError("Enter a time as HH:MM.")
        return text
    return text


def typed(definition: SettingDef, stored: str) -> Any:
    if definition.kind == "int":
        return int(stored)
    return stored
