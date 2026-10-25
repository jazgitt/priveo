"""The notification events and who they are for.

Customer events can each be switched off in Settings (NOTIF-03, SET-02) and
are the only events a customer ever gets (NOTIF-02). Crew events cannot be
switched off (CRW-NOT-03). Admin alerts are saved by `app.support.alerts` and
only their push goes through here (ADM-ACC-09: the bell and the push cannot be
switched off)."""

CUSTOMER_EVENTS = (
    "service_completed",
    "service_skipped",
    "complaint_update",
    "renewal_reminder",
    "monthly_check_in",
)

CREW_EVENTS = (
    "crew_schedule_frozen",   # CRW-NOT-01
    "crew_job_removed",       # CRW-NOT-02
    "crew_job_assigned",      # CRW-NOT-04
    "crew_job_reassigned",    # CRW-NOT-05
    "crew_queue_changed",     # B-06: the admin reordered or unlocked the queue
)

EVENTS = CUSTOMER_EVENTS + CREW_EVENTS

# What the Settings screen shows for each switch: (name, one line).
LABELS: dict[str, tuple[str, str]] = {
    "service_completed": ("Service completed",
                          "When your car's service is done, or only partly done, with the proof."),
    "service_skipped": ("Service skipped",
                        "When a visit is skipped, by you or by Priveo."),
    "complaint_update": ("Complaint update",
                         "When a complaint changes status or gets a new note."),
    "renewal_reminder": ("Renewal reminder",
                         "Reminders to pay for the next month."),
    "monthly_check_in": ("Monthly check-in",
                         "A short check-in four days before your renewal."),
}


def switchable(event: str) -> bool:
    return event in CUSTOMER_EVENTS
