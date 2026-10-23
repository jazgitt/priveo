"""Every feature the admin can switch on or off (the code decides which exist;
the database only stores whether each is on). A flag with no stored row takes
its `default` (on unless the definition says otherwise), so a new flag never
removes anything until the admin turns it off. A stored row always wins.

Keep keys in step with the app's `FeatureKeys` (apps/mobile/lib/core/features).
Do not add flags for sign-in, the home screen or the core job flow: turning
those off would break data, not just hide a screen.
"""
from dataclasses import dataclass

CUSTOMER = "customer"
CREW = "crew"
BOTH = "both"


@dataclass(frozen=True)
class FlagDef:
    key: str
    label: str
    description: str
    group: str
    audience: str  # customer | crew | both
    default: bool = True  # value while no row is stored


FLAGS: tuple[FlagDef, ...] = (
    # ---- customer ----
    FlagDef("customer.deep_spa", "Deep Spa", "Book a Deep Spa (add-on or standalone).",
            "Customer: services", CUSTOMER),
    FlagDef("customer.addons", "Add-ons", "Browse and buy add-ons.",
            "Customer: services", CUSTOMER),
    FlagDef("customer.skip_pause", "Skip and pause", "Skip a day or pause the subscription.",
            "Customer: services", CUSTOMER),
    FlagDef("customer.history", "History", "Past visits and imported records.",
            "Customer: services", CUSTOMER),
    FlagDef("customer.add_vehicle", "Add vehicle", "Add another vehicle.",
            "Customer: account", CUSTOMER),
    FlagDef("customer.subscription", "Subscription screen",
            "View and manage the subscription.", "Customer: account", CUSTOMER),
    FlagDef("customer.billing_history", "Billing history", "Past payments.",
            "Customer: account", CUSTOMER),
    FlagDef("customer.upi_pay", "Pay by UPI", "The pay screen.", "Customer: account", CUSTOMER),
    FlagDef("customer.help", "Help and FAQ", "Help centre and FAQ.",
            "Customer: support", CUSTOMER),
    FlagDef("customer.report_issue", "Report an issue", "Report an issue with a visit.",
            "Customer: support", CUSTOMER),
    FlagDef("customer.complaints", "Complaints", "Raise and follow complaints.",
            "Customer: support", CUSTOMER),
    FlagDef("customer.checkin", "Check-in", "Check-in requests.", "Customer: support", CUSTOMER),
    FlagDef("customer.feedback", "Feedback tab", "The feedback side tab.",
            "Customer: support", CUSTOMER),
    # ---- crew ----
    FlagDef("crew.manager_screens", "Manager screens",
            "Schedule, attendance and hours for crew managers.", "Crew", CREW),
    # D-02: starts OFF; the admin switches it on to let managers skip a job.
    FlagDef("crew.manager_skip", "Allow crew manager to skip",
            "A crew manager may skip a missed job from the app. The admin can always skip.",
            "Crew", CREW, default=False),
    # D-02: a manager may send a missed Interior job to the next day.
    FlagDef("crew.manager_reschedule", "Allow crew manager to reschedule",
            "A crew manager may move a missed Interior job to the next day.",
            "Crew", CREW),
    FlagDef("crew.sequential_queue", "Sequential queue",
            "Crew must finish jobs in queue order; later jobs stay locked (S-13, C-01).",
            "Crew", CREW),
    FlagDef("crew.notifications", "Crew notifications", "The notifications screen.",
            "Crew", CREW),
    # ---- both ----
    FlagDef("common.push", "Push registration", "Register the device for push.",
            "Both", BOTH),
)

BY_KEY = {f.key: f for f in FLAGS}


def for_audience(audience: str) -> list[FlagDef]:
    return [f for f in FLAGS if f.audience in (audience, BOTH)]
