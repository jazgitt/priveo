"""One list of codes for unassigned reasons and report findings.

The code string is stable and is what stored rows and reports carry. The text is
the human wording shown today; codes without a text yet have `text` of None.
"""

from enum import StrEnum


class ReasonCode(StrEnum):
    NO_CLEANER = "no_cleaner"
    SHIFT_TOO_SHORT = "shift_too_short"
    WEEKLY_OFF = "weekly_off"
    CUSTOMER_CUTOFF = "customer_cutoff"
    CAPACITY_SHORT = "capacity_short"
    BREAK_KEPT = "break_kept"
    BEFORE_INTERIOR_EARLIEST = "before_interior_earliest"
    ENTITLEMENT_USED = "entitlement_used"
    HOME_ZONE_FULL = "home_zone_full"
    CROSS_ZONE = "cross_zone"
    # Solver outcomes that already have text today and fit none of the above.
    NO_SLOT = "no_slot"
    NO_PLAN = "no_plan"

    @property
    def text(self) -> str | None:
        return REASON_TEXT.get(self)


REASON_TEXT: dict[ReasonCode, str] = {
    ReasonCode.NO_CLEANER: "No crew member works that day.",
    ReasonCode.NO_SLOT: "No working slot allows this service that day.",
    ReasonCode.SHIFT_TOO_SHORT: "No crew member's hours are long enough for this job.",
    ReasonCode.NO_PLAN: "The scheduler found no plan.",
    ReasonCode.CAPACITY_SHORT: "Capacity is short for that day.",
}
