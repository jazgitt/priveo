"""Build the dated source-review report. Reads source; never imports app code or runs tests."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/coverage"
DATE = "2026-10-13"
SOURCES = {
    "customer": "docs/reqs/customer-app-functional-requirements.md",
    "admin": "docs/reqs/admin-functional-requirements.md",
    "crew": "docs/reqs/crew-functional-requirements.md",
}

def ref(path, text=None):
    p = ROOT / path
    if not p.is_file():
        raise ValueError(f"Missing evidence file: {path}")
    lines = p.read_text(encoding="utf-8").splitlines()
    matches = [i + 1 for i, value in enumerate(lines) if text and text in value]
    if text and not matches:
        raise ValueError(f"Missing evidence selector: {path}: {text}")
    line = matches[0] if matches else 1
    return {"path": path, "line": line}

def group(code, tests, note):
    return {"code": [ref(p) for p in code], "tests": [ref(p) for p in tests], "note": note}

A = "services/api/app/"
T = "services/api/tests/"
M = "apps/mobile/lib/"
MT = "apps/mobile/test/"
W = "apps/web/src/"
GROUPS = {
    "AUTH": group([A+"identity/service.py", M+"features/auth/presentation/login_screen.dart", M+"core/auth/auth_controller.dart"], [T+"test_first_sign_in.py", T+"test_api.py", MT+"auth/auth_entry_test.dart", MT+"screens_test.dart"], "Welcome/email/password/code/session flow and role routing are present."),
    "ONB": group([A+"customers/service.py", A+"customers/administration.py", M+"features/customer/onboarding/onboarding_review_screen.dart", M+"features/customer/vehicles/add_vehicle_screen.dart"], [T+"test_customer_home.py", T+"test_customer_administration.py", MT+"customer_test.dart", MT+"customer/add_vehicle_test.dart"], "Prefilled review and customer Add Vehicle flow use validated directory/profile/vehicle data."),
    "PAY": group([A+"billing/service.py", M+"features/changes_money/pay_screen.dart", M+"features/customer/onboarding/onboarding_review_screen.dart"], [T+"billing/test_billing.py", MT+"changes_money/changes_money_test.dart", MT+"customer/add_vehicle_test.dart"], "Manual UPI instructions, payment state transitions and onboarding payment entry exist."),
    "HOME": group([A+"customers/service.py", M+"features/customer/home/customer_shell.dart", M+"features/customer/home/home_schedule.dart", M+"features/customer/home/todays_clean_strip.dart"], [T+"test_customer_home.py", MT+"customer/calendar_home_test.dart", MT+"customer/customer_slice_test.dart"], "Home reads selected vehicle, next service and completion/check-in summaries."),
    "CAL": group([A+"customer_reads/calendar_view.py", M+"features/customer/calendar/calendar_screen.dart", M+"features/customer/calendar/day_card.dart"], [T+"customer_reads/test_calendar_projection.py", MT+"customer/calendar_home_test.dart", MT+"customer/customer_slice_test.dart"], "Projected/planned month calendar, markers, assignments and day actions are present."),
    "SVC": group([A+"customer_reads/sql_repository.py", A+"support/service.py", M+"features/customer/visit/visit_details_screen.dart", M+"features/support/feedback_sheet.dart"], [T+"visits/test_proof_reads.py", T+"support/test_support.py", MT+"customer/customer_slice_test.dart", MT+"support/support_test.dart"], "Service Details joins checklist, proof and crew, offers visit rating and linked issue reporting."),
    "HIST": group([A+"customer_reads/service.py", M+"features/customer/history/history_screen.dart"], [T+"visits/test_proof_reads.py", MT+"customer/customer_slice_test.dart"], "History has month navigation, paging, finish/rating fields and member-since metadata."),
    "SKIP": group([A+"changes/service.py", A+"changes/sql_gateway.py", M+"features/changes_money/skip_pause_screen.dart"], [T+"changes/test_changes.py", T+"notifications/test_events.py", MT+"changes_money/changes_money_test.dart"], "Skip/un-skip rules, calendar refresh, notifications hooks and cutoff checks are present."),
    "PAUSE": group([A+"changes/service.py", A+"changes/cycle.py", M+"features/changes_money/skip_pause_screen.dart"], [T+"changes/test_changes.py", MT+"changes_money/changes_money_test.dart"], "Pause range/preview, merge and early-end behavior uses the shared cycle rules."),
    "SCHED": group([A+"changes/rules.py", A+"changes/service.py", M+"features/customer/calendar/day_card.dart", M+"features/changes_money/skip_pause_screen.dart"], [T+"changes/test_changes.py", MT+"customer/calendar_home_test.dart"], "Customer 9 PM rule and disabled controls/support actions are present."),
    "ACC": group([A+"customers/account.py", M+"features/customer/account/account_sections.dart", M+"features/customer/account/profile_screens.dart"], [T+"customers_account/test_account.py", MT+"customer/account_test.dart", MT+"customer/customer_slice_test.dart"], "Profile, per-vehicle cards/menu, email change and logout are implemented."),
    "SET": group([A+"notifications/service.py", M+"features/customer/settings/settings_screen.dart"], [T+"notifications/test_events.py", MT+"notifications/notifications_test.dart"], "Five independent notification switches with enabled defaults and Account entry exist."),
    "NOTIF": group([A+"notifications/emit.py", A+"notifications/service.py", A+"notifications/cron.py", M+"features/customer/notifications/notifications_screen.dart", M+"features/common/push/push_registration.dart"], [T+"notifications/test_events.py", T+"notifications/test_notifications.py", MT+"notifications/notifications_test.dart"], "Inbox, token APIs, preference checks, event hooks and reminder cron definitions exist."),
    "SUB": group([A+"billing/service.py", A+"changes/cycle.py", M+"features/changes_money/subscription_screen.dart", M+"features/customer/calendar/defaults_sheet.dart"], [T+"billing/test_billing.py", T+"customer_reads/test_calendar_projection.py", MT+"changes_money/changes_money_test.dart"], "Per-vehicle plan/cycle/status/history, renewal payment and default-preference controls exist."),
    "VEH": group([A+"customers/account.py", A+"customers/administration.py", M+"features/customer/vehicles/vehicles_screen.dart", M+"features/customer/account/vehicle_account_section.dart", M+"features/customer/vehicles/add_vehicle_screen.dart"], [T+"customers_account/test_account.py", T+"test_customer_administration.py", MT+"customer/account_test.dart", MT+"customer/add_vehicle_test.dart"], "Vehicle reads, photo/parking edits, separate societies and Add Vehicle flow are present."),
    "ADD": group([A+"addons/service.py", A+"scheduling/service.py", A+"visits/operations.py", M+"features/changes_money/addon_screen.dart"], [T+"addons/test_addons.py", T+"scheduling/test_addon_lifecycle.py", T+"scheduling/test_operations.py", MT+"changes_money/changes_money_test.dart"], "Subscriber add-on booking/payment, scheduling/status sync, frozen changes and Missed outcomes exist."),
    "SUP": group([A+"support/router.py", A+"support/faq.py", M+"features/support/help_screen.dart", M+"features/support/faq_screen.dart"], [T+"support/test_wp8.py", MT+"support/support_test.dart", MT+"support/wp8_test.dart"], "Support links, FAQ expansion and feedback entry are implemented."),
    "ISS": group([A+"customers/account.py", A+"support/service.py", M+"features/support/report_issue_screen.dart"], [T+"customers_account/test_account.py", T+"support/test_support.py", MT+"customer/account_test.dart", MT+"support/support_test.dart"], "Complaint form, visit selector, photos, ownership and validation exist."),
    "CMP": group([A+"support/service.py", M+"features/support/complaints_screen.dart"], [T+"support/test_support.py", MT+"support/support_test.dart"], "Complaint summaries, status/progress and latest notes are present."),
    "FDBK": group([A+"support/service.py", M+"features/support/feedback_sheet.dart", M+"features/support/feedback_tab.dart"], [T+"support/test_support.py", MT+"support/support_test.dart", MT+"support/wp8_test.dart"], "Feedback category/rating/comment/consent form, backend options and response gating exist."),
    "CHK": group([A+"support/service.py", A+"support/defaults.py", M+"features/support/checkin_screen.dart", M+"features/customer/home/home_schedule.dart"], [T+"support/test_support.py", T+"support/test_wp8.py", MT+"support/support_test.dart", MT+"customer/calendar_home_test.dart"], "Six editable check-in categories, per-cycle storage and the due Home card exist."),
    "NAV": group([M+"core/routing/router.dart", M+"features/customer/home/customer_shell.dart", M+"features/customer/cust_ui.dart"], [MT+"unit_test.dart", MT+"customer/customer_slice_test.dart"], "Role navigation, top-level tab bodies, detail back buttons and action messages exist."),
}

GROUPS.update({
    "CRW-ACC": group([A+"identity/service.py", A+"crew/service.py", M+"core/routing/router.dart", W+"pages/crew/OnboardDialog.tsx", W+"pages/crew/shared.tsx"], [T+"crew/test_crew.py", T+"test_api.py", T+"scheduling/test_crew_directory.py", W+"pages/crew/crew.test.tsx"], "Crew authentication, generated/one-time password, lock/reset and deactivation/session actions exist."),
    "CRW-PRF": group([A+"visits/service.py", M+"features/crew/profile/crew_profile_screen.dart", A+"media/service.py"], [T+"crew/test_crew.py", T+"visits/test_proof_reads.py", MT+"crew/screens_test.dart"], "Own read-only profile, signed photo read and camera/gallery change are present."),
    "CRW-SCH": group([A+"visits/service.py", A+"scheduling/service.py", M+"features/crew/home/crew_home_screen.dart", M+"features/crew/job/job_card_screen.dart"], [T+"visits/test_crew_jobs.py", T+"scheduling/test_crew_directory.py", T+"notifications/test_events.py", MT+"crew/screens_test.dart"], "Frozen own/paired job cards, vehicle photo, finish-by and crew-only serializers exist."),
    "CRW-MGR": group([A+"visits/manager.py", A+"visits/service.py", M+"features/crew/manager/manager_attendance_screen.dart", M+"features/crew/manager/manager_hours_screen.dart", M+"features/crew/manager/manager_job_screen.dart"], [T+"visits/test_manager.py", T+"visits/test_manager_ops.py", MT+"crew/screens_test.dart"], "Society-scoped schedule/skip/reassign/attendance/hours and change records are present."),
    "CRW-SVC": group([A+"visits/service.py", A+"media/router.py", M+"features/crew/job/perform_service_screen.dart", M+"features/crew/upload/upload_queue.dart"], [T+"visits/test_crew_jobs.py", T+"visits/test_proof_reads.py", T+"media/test_uploads.py", MT+"crew/screens_test.dart", MT+"crew/queue_test.dart"], "Checklist/stage/capture, upload confirmation gating, finish time and persisted queue exist."),
    "CRW-CNC": group([A+"visits/service.py", A+"visits/operations.py", M+"features/crew/job/could_not_complete_screen.dart", A+"customer_reads/calendar_view.py"], [T+"visits/test_crew_jobs.py", T+"scheduling/test_operations.py", T+"customer_reads/test_calendar_projection.py", MT+"crew/screens_test.dart"], "Could not complete, required reasons/optional evidence and admin next-day outcomes exist."),
    "CRW-RAT": group([A+"support/router.py", M+"features/crew/routes.dart"], [T+"test_api.py", MT+"crew/screens_test.dart"], "Crew UI has no ratings; former crew ratings and mock home endpoints are removed."),
    "CRW-NOT": group([A+"notifications/emit.py", A+"notifications/router.py", M+"features/crew/notifications/crew_notifications.dart", M+"features/common/push/push_registration.dart"], [T+"notifications/test_events.py", MT+"notifications/notifications_test.dart"], "Crew inbox, devices, frozen/removed/assigned/reassigned hooks and no preferences exist."),
    "ADM-ACC": group([A+"identity/service.py", A+"webauth/router.py", A+"platform/websession.py", W+"App.tsx", W+"Shell.tsx", M+"features/admin_quick/home/admin_home_screen.dart"], [T+"test_api.py", T+"webauth/test_webauth.py", W+"App.test.tsx", MT+"admin_quick/admin_quick_test.dart"], "Seeded role access, cookie/CSRF portal, shared backend and admin mobile session rules exist."),
    "ADM-CUS": group([A+"customers/administration.py", W+"pages/customers/CustomersPage.tsx", W+"pages/customers/VehicleWizard.tsx", A+"changes/service.py"], [T+"test_customer_administration.py", W+"pages/customers/customers.test.tsx", T+"changes/test_changes.py"], "Portal customer/vehicle create/edit, welcome/reset, sessions, preferences and skip/pause actions exist."),
    "ADM-SUB": group([A+"billing/service.py", W+"pages/subscriptions/SubscriptionsPage.tsx", W+"pages/customers/CustomersPage.tsx"], [T+"billing/test_billing.py", T+"test_customer_administration.py", W+"pages/subscriptions/SubscriptionsPage.test.tsx"], "Activation/inactivation/reactivation controls, cycle anchoring and status events are present."),
    "ADM-CRW": group([A+"crew/service.py", A+"crew/router.py", W+"pages/crew/OnboardDialog.tsx", W+"pages/crew/panels.tsx"], [T+"scheduling/test_crew_directory.py", T+"crew/test_crew.py", W+"pages/crew/crew.test.tsx"], "Crew onboarding, roles/pairing, weekday hours, exceptions and account/session actions exist."),
    "ADM-SVS": group([A+"directory/service.py", A+"directory/defaults.py", A+"scheduling/service.py", W+"pages/reference/SlotsTab.tsx", W+"pages/reference/ServicesTab.tsx"], [T+"directory/test_directory.py", T+"scheduling/test_solver.py", W+"pages/reference/ReferencePage.test.tsx"], "Society-specific independent slots/defaults, validation and configurable service durations exist."),
    "ADM-CAP": group([A+"scheduling/service.py", A+"scheduling/rules.py", W+"pages/capacity/CapacityPage.tsx"], [T+"scheduling/test_scheduling_api.py", T+"scheduling/test_crew_directory.py", W+"pages/schedule/SchedulePage.test.tsx"], "Capacity/demand derive from active society crew, weekday hours, exceptions, skips/pauses and due jobs."),
    "ADM-PAY": group([A+"billing/service.py", W+"pages/payments/PaymentsPage.tsx", M+"features/admin_quick/payments/payments_screens.dart"], [T+"billing/test_billing.py", W+"pages/payments/PaymentsPage.test.tsx", MT+"changes_money/changes_money_test.dart"], "Filtered payment control, offline records, invoice issuance and status/audit events exist."),
    "ADM-SCH": group([A+"scheduling/service.py", A+"scheduling/administration.py", A+"scheduling/solver.py", W+"pages/schedule/SchedulePage.tsx", W+"pages/schedule/ScheduleActions.tsx"], [T+"scheduling/test_scheduling_api.py", T+"scheduling/test_solver.py", T+"scheduling/test_addon_lifecycle.py", W+"pages/schedule/SchedulePage.test.tsx"], "Manual runs/periods, draft/board, fixed manual entries, swaps/suggestions and freeze/change rules exist."),
    "ADM-PRF": group([A+"directory/settings_registry.py", W+"pages/settings/SettingsPage.tsx", A+"scheduling/service.py"], [T+"directory/test_directory.py", W+"pages/reference/ReferencePage.test.tsx"], "Daily/Weekly/Monthly preference and Sunday default week start are stored and consumed."),
    "ADM-CMP": group([A+"support/service.py", W+"pages/complaints/ComplaintsPage.tsx", W+"pages/complaints/ComplaintDetailPage.tsx"], [T+"support/test_support.py", W+"pages/support/support.test.tsx", MT+"admin_quick/admin_quick_test.dart"], "Complaint status/note management, role checks, thread/audit actors and overdue flags exist."),
    "ADM-OPS": group([A+"visits/operations.py", A+"changes/extension.py", W+"pages/operations/OperationsPage.tsx", M+"features/admin_quick/actions/actions_screens.dart"], [T+"scheduling/test_operations.py", W+"pages/operations/OperationsPage.test.tsx", MT+"admin_quick/operations_actions_test.dart"], "Admin visit/job skips, reason/note/history and idempotent exterior-only plan/payment extensions exist."),
    "ADM-CNC": group([A+"visits/operations.py", W+"pages/operations/OperationsPage.tsx", A+"directory/service.py"], [T+"scheduling/test_operations.py", T+"directory/test_directory.py", W+"pages/operations/OperationsPage.test.tsx"], "Managed reasons and filtered Missed queue/evidence with next-day-only retry decisions exist."),
    "ADM-FDB": group([A+"support/service.py", W+"pages/feedback/FeedbackPage.tsx", W+"pages/feedback/OptionsManager.tsx"], [T+"support/test_support.py", T+"support/test_wp8.py", W+"pages/support/support.test.tsx"], "Feedback/ratings/check-in reports, filters, consent indicators and editable active options exist."),
    "ADM-REF": group([A+"directory/service.py", A+"customers/administration.py", W+"pages/reference/ReferencePage.tsx", W+"pages/customers/CustomersPage.tsx"], [T+"directory/test_directory.py", T+"test_customer_administration.py", W+"pages/reference/ReferencePage.test.tsx"], "Society/catalogue CRUD and active guards, cars-serviced counts, car edits and admin RC verification exist."),
    "ADM-SET": group([A+"directory/settings_registry.py", A+"directory/service.py", W+"pages/settings/SettingsPage.tsx", W+"pages/reference/PlansTab.tsx"], [T+"directory/test_directory.py", W+"pages/reference/ReferencePage.test.tsx"], "Plan management and typed payment/support/read-only invoice settings exist; seed defaults are placeholders."),
    "ADM-CHK": group([A+"directory/service.py", A+"directory/lookup.py", A+"customer_reads/sql_repository.py", W+"pages/reference/ChecklistsTab.tsx"], [T+"directory/test_directory.py", T+"visits/test_crew_jobs.py", T+"visits/test_proof_reads.py", W+"pages/reference/ReferencePage.test.tsx"], "Role-protected checklist CRUD/order/activation and proof minimum configuration feed crew/customer views."),
    "ADM-ADD": group([A+"addons/service.py", A+"customers/importer.py", W+"pages/addons/AddonsPage.tsx", W+"pages/reference/AddonsTab.tsx"], [T+"addons/test_addons.py", T+"scheduling/test_addon_lifecycle.py", T+"scheduling/test_operations.py", T+"test_import.py", W+"pages/addons/AddonsPage.test.tsx"], "Catalogue and subscribed booking administration, scheduling/payment links and standalone import/request scaffold exist."),
})

OVERRIDES = {}
def issue(ids, key, note, status="Partial", tests="Partial", extra=()):
    for rid in ids.split():
        OVERRIDES[rid] = {"status": status, "gap": key, "note": note, "test_status": tests,
                          "extra": [ref(p, needle) for p, needle in extra]}

issue("ONB-21", "onboarding-save", "Continue only advances the local draft; names/parking/preferences persist at final confirm, not at each Continue. No resume-after-restart acceptance test.")
issue("ONB-23 ONB-25", "onboarding-steps", "Add Vehicle has a plan-before-preferences step, but first-sign-in review uses 3 + vehicle-count steps, combines parking/preferences/plan and puts the read-only plan after preferences; not the specified seven-step review.")
issue("PAY-04", "onboarding-total", "Initial review renders payment rows and a generic Total label, without computing/showing a clearly labelled total payable today and GST line. Add Vehicle review is more complete.")
issue("PAY-07", "payment-summary", "Submitted page shows payment description/amount/status; no explicit vehicle and selected service-preference summary is supplied/displayed.")
issue("PAY-05 SUP-02 SUP-03 AUTH-15 ADM-SET-02 ADM-SET-03", "business-config", "Functional controls exist, but repository defaults use placeholder UPI/QR/contact values. Live configured values are not established by this source audit. Pre-login support-contact reads environment settings, not the admin database settings.", status="Implemented", tests="Present (related)")
issue("AUTH-03 AUTH-05 AUTH-16 ACC-08 ADM-CUS-04 ADM-CUS-18 ADM-CUS-19", "email-config", "Customer Resend adapter/templates and fail-closed production paths exist. Verified sender/domain and actual delivery remain unverified; tests use fake/mocked delivery.", status="Implemented", tests="Present (mocked)")
issue("AUTH-04", "legal-content", "Consent timestamp and tappable Terms/Privacy links are present; public legal URLs/content are configuration placeholders and not verified.", status="Implemented", tests="Present (mocked)")
issue("HOME-02", "home-vehicle-fields", "Home card shows model/registration/photo/society/parking; it does not render make and variant, although detailed vehicle screens do.")
issue("HOME-05 C-07", "home-rate-destination", "Rate today's clean opens the rating sheet directly; requirement says it opens Service Details. It is conditional in the completion strip, rather than the named Home quick action.")
issue("HOME-08 CHK-08", "checkin-refresh", "Home reads homeCheckInsProvider, but successful CheckInScreen submission invalidates pendingCheckInsProvider only. The Home card may remain until its own provider is refreshed; no completion-to-Home invalidation regression.")
issue("CAL-05", "calendar-summary", "Completed day note remains View service details, rather than finish time and checks completed; the calendar DTO/day card lacks that completion summary.")
issue("SVC-06", "video-inline", "New in-app video screen has duration, seeking/playback/retry; the Service Details tile pushes a separate screen instead of literal play-in-place. New player tests are written but not run.", tests="Written; not run", extra=[(M+"features/customer/visit/proof_video_screen.dart", "class ProofVideoScreen"), (MT+"customer/proof_video_test.dart", "void main")])
issue("SVC-07 SVC-12 SVC-14", "rating-validation", "UI permits rating only on Completed visits, but support.rate_visit and its router do not verify visit existence, customer ownership or Completed state. Existing tests exercise rating/tag mechanics, not these missing guards.", extra=[(A+"support/service.py", "def rate_visit")])
issue("SUB-12", "invoice-save", "PDF view code exists, but file save/native share is missing; current copy/email actions send text. New PDF tests are written/unrun; migration 0024 is unapplied. GST breakdown is separately tracked in entity/technical findings.", tests="Written; not run", extra=[(M+"features/changes_money/invoice_pdf_screen.dart", "class InvoicePdfScreen"), (T+"billing/test_invoice_pdf.py", "test_owner_opens_pdf"), (MT+"changes_money/invoice_pdf_test.dart", "invoice summary opens")])
issue("VEH-03 ADM-REF-05", "rc-display", "Admin verification and backend rc_status=Verified exist, but VehicleAccountSection renders Uploaded only for exact Uploaded and otherwise Not uploaded; verified RCs therefore display incorrectly. No verified-RC widget regression.", extra=[(M+"features/customer/account/vehicle_account_section.dart", "vehicle.rcStatus == 'Uploaded'")])
issue("ADD-14 ADM-ADD-10", "standalone-spa", "Standalone request/import scaffolding exists; payment, scheduled fulfilment and customer follow-up are not a defined complete journey. Owner decision is required.")
issue("ADD-15 ADM-ADD-12", "standalone-spa", "Owner has not specified standalone Deep Spa request/payment/follow-up. Current request-only scaffold is not a completed fulfilment flow.", status="Open", tests="Scaffold only")
issue("SUP-05", "faq-markdown", "Expandable FAQ exists, but text is a Python constant delivered by API, not the required app-bundled Markdown file. Content remains placeholder; one late-payment answer implies self-reactivation contrary to SUB-11.")
issue("FDBK-01", "feedback-overlay", "Draggable side tab wraps CustomerShell only. Detail pages and pushed forms use separate Scaffolds/Navigator routes, so the tab is not present on every post-onboarding customer screen. Component tests cover tab behavior, not all navigation paths.")
issue("NOTIF-01 NOTIF-02 NOTIF-04 NOTIF-05 NOTIF-06 SKIP-05 SKIP-07 CMP-04 CHK-01 CHK-05 ADD-13 CRW-NOT-01 CRW-NOT-02 CRW-NOT-04 CRW-NOT-05 CRW-MGR-02 CRW-MGR-03 CRW-SVC-09 CRW-CNC-04 ADM-OPS-01 ADM-CMP-05 ADM-CNC-04 ADM-PAY-11 ADM-SCH-21 ADM-SCH-24 ADM-SCH-27 ADM-SCH-28", "push", "Backend events/inbox/preference or crew fan-out hooks exist, but sender is LoggingPushSender and default mobile NoPushTokenProvider returns null. Firebase/OS permission/token refresh/logout/foreground-background handling and device delivery remain missing. Related tests mock delivery.", tests="Present (mocked)")
issue("ADM-ACC-07", "admin-mobile-push", "Specified payment/schedule/operations/customer/crew/complaint/report quick screens exist; actual phone push is absent and admin home does not watch pushRegistrationProvider. Unit/widget tests cover a subset of actions.")
issue("ADM-ACC-01 ADM-ACC-09", "admin-alert-delivery", "Portal/quick actions and bell exist; admin alert emails still use LoggingEmailNotifier, not the customer Resend sender. No admin email-alert switch is defined in the settings registry or Settings page. Real push is also absent.", extra=[(A+"support/alerts.py", "def raise_alert"), (A+"support/router.py", "def get_email_notifier")])
issue("ADM-ACC-10 ADM-CUS-10", "cross-client-refresh", "Both clients share server state, but most reads are cached and only local query keys are invalidated. External writes are not pushed/polled on all screens, so an already-open other client does not necessarily show the change at once.")
issue("ADM-ACC-14", "admin-session-audit", "Sign out all devices works and records session end time, but the identity endpoint does not write a shared actor/action audit entry. Existing tests assert invalidation, not the required audit action.")
issue("ADM-CUS-14", "admin-change-notify", "Plan/default-setting edits are silent, but admin-on-behalf skip uses ChangesService.skip, which unconditionally emits customer_skipped. This conflicts with the broader no-notification schedule-settings requirement; owner rules need consistent handling.")
issue("ADM-CUS-15", "plan-change-ui", "Backend defers plan/price correctly; portal Save settings sends the existing interior day even when the chosen pending plan has no interior. API validates that day against pending plan and rejects this payload. Existing API test changes plan only, not that portal combination.")
issue("ADM-CUS-16", "admin-reset-audit", "Most admin changes use shared audit, but customer session logout-all uses the identity endpoint without a customer/admin audit action. Single-session logout is audited; full acceptance coverage is incomplete.")
issue("ADM-SUB-04", "reactivation-payment", "Inactive -> Activating -> Active transitions exist, but reactivation does not create a new Due payment at the new first-service date; activation only reanchors the original first payment when previously_active is absent. No new-cycle/reactivation-payment regression.")
issue("ADM-CRW-21", "crew-session-metadata", "Crew sessions return only ID/channel/signed-in/last-active. Device name/platform/app version exist on AuthSession but are not populated for crew or exposed/rendered by crew session APIs/UI.")
issue("CRW-ACC-12 CRW-SVC-10", "queue-isolation", "SQLite/files retain queued media and retry on app open/connectivity; queue has no login/owner partition and provider is not scoped to auth. A different crew login can attempt the previous user's pending uploads. No account-switch/native persistence scenario.")
issue("CRW-SVC-06 CRW-PRF-04", "media-boundary", "Supported formats and size checks exist, but backend and capture validation use > limit, accepting exactly 10/25 MB although spec says under. Native HEIC handling is unverified; exact-boundary regressions missing.")
issue("CRW-SCH-05 ADM-SVS-10", "standalone-scheduling", "Subscriber Spa bookings with their own duration/finish-by are scheduled; standalone scaffold has no complete assigned-job/paid history journey and awaits owner decision.")
issue("ADM-CMP-01", "complaint-vehicle", "Complaint list shows customer/society/category/visit/status/date but no vehicle. AdminComplaintSummary has no vehicle label field. Current UI tests do not assert the specified vehicle column.")
issue("ADM-CMP-02", "complaint-proof", "API supplies signed photo_urls, but portal type/UI ignores them and displays attachment count only. Linked visit is raw ID text, with no visit/proof detail viewer.")
issue("ADM-CMP-08", "complaint-timer", "Overdue-once rule exists and cron endpoint works in mocked component tests, but committed Vercel config runs complaints-overdue once daily; it cannot deliver an alert promptly after the 4-hour threshold. Live host execution is unverified; email/push adapters remain fake.")
issue("ADM-CMP-07", "complaint-actor-display", "Database updates store author_login_id/time, but UpdateOut/portal thread display only generic Admin/Customer, not which admin made each change. Backend recording is present; visible actor identity is incomplete.", status="Implemented", tests="Present (related)")
issue("ADM-CHK-05", "checklist-history", "Progress stores item key/time only; reads resolve current labels and active items. Renaming changes completed history and newly added items can appear on old completed visits. No immutable issued-visit checklist snapshot.", extra=[(A+"visits/models.py", "class JobChecklistProgress"), (A+"customer_reads/sql_repository.py", "def _checklist")])
issue("ADM-CHK-07", "checklist-content", "External defaults are present; Cleaning-Internal and Deep Spa defaults explicitly remain placeholders until owner supplies lists.", status="Open", tests="Defaults only")
issue("ADM-SET-04 ADM-PAY-08", "gst-invoice", "Seller fields and issued PDF are present, but repository seller defaults are placeholders and invoice models/PDF have inclusive total only, no GST breakdown listed in the entity requirements. Invoice settings are editable in API/portal despite seed/read-only MVP requirement. New PDF tests/migration are unrun; tax/business input must not be guessed.", tests="Partial; PDF tests unrun")
issue("ADM-PAY-06", "pause-payment-shift", "Operations extensions move non-Received future payments, but pause/early-end does not synchronize all unpaid statuses immediately. generate_due_payments shifts only Due candidates later; Initiated/Over due due dates can stay stale. Tests cover a Due payment, not all unpaid states.")
issue("ADM-FDB-07", "option-history", "Deactivation keeps earlier entries, but ratings/check-in names are stored as strings and active validation is current. Historical names remain readable; a renamed option can split aggregate buckets. No identifier/snapshot migration policy is recorded.", status="Implemented", tests="Present (related)")
issue("ADM-PAY-01 ADM-CUS-08", "list-paging", "Server limits payment list to default 100 and customer search to 200; portal exposes no Load more/offset flow. Current tests cover short lists, not records beyond the limit.")
issue("PAY-05", "payment-qr", "Backend supplies an amount-bearing upi_uri, but the app displays only a configured qr_url image and does not encode/use that URI. A QR for the exact payable amount is not generated; live UPI/QR values also remain unverified.")
issue("VEH-04", "parking-options", "Parking API uses configured society basements, but the account edit widget hardcodes B1-B4 rather than the society's allowed list. Add Vehicle uses configured basements. Missing non-default-basement widget regression.")
issue("ONB-10", "registration-uppercase", "Server normalizes registration to uppercase, but Add Vehicle only requests an uppercase keyboard, without an input formatter forcing pasted text to uppercase in the field. No paste/uppercase regression located.")
issue("ADM-ADD-11", "imported-spa-history", "Import creates standalone customers/vehicles and legacy AddonRequest records with dates/payment notes. Current customer history reads Visit rows and add-on lists read AddonBooking, so those imported standalone records are not surfaced as service history. Existing import tests assert stored records, not visible history.", extra=[(A+"customers/importer.py", "def addon_row"), (A+"customer_reads/sql_repository.py", "def history")])

# Additional validation limitations are recorded without changing source implementation verdicts.
VERIFY = {
    "AUTH-06": "Paste uses the hidden text input; no dedicated clipboard/paste assertion located.",
    "ONB-10": "Validation normalizes uppercase, but Add Vehicle field relies on keyboard capitalization rather than a forced uppercase formatter for pasted text.",
    "ONB-12": "RC upload API/client exists; file-selector/native limits lack dedicated RC end-to-end tests.",
    "HIST-02": "Month paging/footer are coded; multiple-page/month navigation acceptance is not fully asserted by the widget tests.",
    "SVC-05": "Photo captions/counter are present; automatic signed-photo refresh while viewer remains open is absent and device HEIC rendering is unverified.",
    "VEH-04": "Parking API respects society basements, but edit widget hardcodes B1-B4 while Add Vehicle uses configured basements.",
    "ADM-SCH-12": "Board provides lanes and list views; mouse/keyboard editing is component-tested, not browser E2E.",
    "ADM-SCH-15": "Preview/apply/stale protection are coded; backend tests assert no-write preview, atomic failure and stale rejection, not a successful chosen-improvement acceptance scenario.",
    "ADM-SCH-25": "freeze-due endpoint/Vercel entry exist; actual authorized live invocation and timezone boundary remain unverified.",
    "ADM-SUB-03": "Automatic inactivity function/cron are coded; deployed timers are not verified.",
    "SUB-11": "Automatic inactivity function/cron are coded; deployed timers are not verified.",
    "CRW-SVC-12": "Closed-job upload guard exists and is directly asserted in test_upload_for_a_closed_job_is_refused.",
}

DIRECT = {
    "AUTH-01": (MT+"auth/auth_entry_test.dart", "the welcome screen has two buttons"),
    "AUTH-02": (MT+"auth/auth_entry_test.dart", "an email with a bad format"),
    "AUTH-07": (T+"test_first_sign_in.py", "test_five_wrong_codes_cancel_the_code"),
    "AUTH-12": (T+"test_first_sign_in.py", "test_a_weak_password_is_refused"),
    "AUTH-13": (T+"test_api.py", "test_five_wrong_passwords_block_a_customer"),
    "AUTH-14": (T+"test_first_sign_in.py", "test_an_email_the_admin_has_not_created"),
    "AUTH-17": (T+"test_first_sign_in.py", "test_the_admin_ends_a_customers_sessions"),
    "CAL-07": (T+"customer_reads/test_calendar_projection.py", "test_a_requested_cutoff_change"),
    "CAL-08": (MT+"customer/calendar_home_test.dart", "change cutoff time picks a time"),
    "CAL-09": (T+"scheduling/test_operations.py", "test_next_day_internal_retry"),
    "CAL-10": (T+"customer_reads/test_calendar_projection.py", "test_assignment_shows_only_for_a_frozen_schedule"),
    "SVC-03": (T+"visits/test_proof_reads.py", "test_customer_sees_proof_checklist_crew_and_finish_time"),
    "SVC-04": (MT+"customer/customer_slice_test.dart", "shows the crew card, checklist and AFTER label"),
    "SKIP-02": (T+"changes/test_changes.py", "test_skip_is_refused_from_9pm"),
    "SKIP-08": (T+"changes/test_changes.py", "test_a_date_inside_a_pause_cannot_be_skipped"),
    "PAUSE-06": (T+"changes/test_changes.py", "test_a_skip_inside_a_pause_is_counted_once"),
    "ACC-06": (MT+"customer/account_test.dart", "edit profile saves names and mobile"),
    "ACC-08": (T+"customers_account/test_account.py", "test_email_change_needs_the_code"),
    "SET-02": (T+"notifications/test_events.py", "test_preferences_default_on_and_change_one_at_a_time"),
    "SET-03": (T+"notifications/test_events.py", "test_preferences_default_on_and_change_one_at_a_time"),
    "NOTIF-03": (T+"notifications/test_events.py", "test_a_switched_off_event_is_not_sent"),
    "SUB-08": (T+"customer_reads/test_calendar_projection.py", "test_preferences_after_9pm_apply_from_the_day_after"),
    "VEH-09": (T+"test_customer_administration.py", "test_plan_change_waits_for_renewal_and_society_is_immutable"),
    "ADD-06": (T+"scheduling/test_addon_lifecycle.py", "test_booking_reaches_scheduler_without_payment"),
    "ADD-10": (T+"scheduling/test_addon_lifecycle.py", "test_frozen_change_is_a_request_and_cancel_removes_spa_only"),
    "ADD-12": (T+"scheduling/test_operations.py", "test_spa_retry_has_one_job"),
    "ISS-02": (T+"customers_account/test_account.py", "test_complaint_photos_and_visit_must_be_the_customers_own"),
    "ISS-04": (MT+"customer/account_test.dart", "report an issue sends the attached photos and the visit"),
    "CHK-03": (T+"support/test_wp8.py", "test_checkin_categories_are_the_six_owner_categories"),
    "CRW-ACC-04": (T+"crew/test_crew.py", "test_password_format"),
    "CRW-ACC-08": (T+"scheduling/test_crew_directory.py", "test_a_deactivated_crew_member_is_not_scheduled"),
    "CRW-SCH-03": (T+"visits/test_proof_reads.py", "test_vehicle_photo_shows_on_the_crew_card"),
    "CRW-SCH-10": (T+"visits/test_crew_jobs.py", "test_a_trainee_sees_and_does_the_paired_members_jobs"),
    "CRW-MGR-04": (T+"visits/test_manager_ops.py", "test_marking_absent_changes_the_list"),
    "CRW-MGR-05": (T+"visits/test_manager_ops.py", "test_hours_are_listed_and_changed"),
    "CRW-SVC-07": (T+"visits/test_crew_jobs.py", "test_a_changed_proof_minimum_is_the_one_required"),
    "CRW-SVC-08": (T+"visits/test_crew_jobs.py", "test_a_job_cannot_complete_until_checklist_and_proof_are_done"),
    "CRW-SVC-12": (T+"visits/test_proof_reads.py", "test_upload_for_a_closed_job_is_refused"),
    "CRW-CNC-05": (T+"scheduling/test_operations.py", "test_completed_and_external_jobs_cannot_be_repeated"),
    "CRW-NOT-03": (T+"notifications/test_events.py", "test_a_crew_member_has_no_switches"),
    "ADM-ACC-12": (T+"webauth/test_webauth.py", "test_a_change_by_cookie_needs_the_csrf_header"),
    "ADM-CUS-03": (T+"test_customer_administration.py", "test_onboard_without_import_and_duplicate_email_opens_existing"),
    "ADM-CUS-07": (W+"pages/customers/customers.test.tsx", "creates a customer with subscription"),
    "ADM-CUS-19": (T+"test_customer_administration.py", "test_email_correction_invalidates_sessions"),
    "ADM-SUB-01": (T+"test_customer_administration.py", "test_activation_anchors_first_payment"),
    "ADM-CRW-19": (T+"scheduling/test_crew_directory.py", "test_pairing_rules"),
    "ADM-SVS-07": (T+"directory/test_directory.py", "test_slots_crud_and_rules"),
    "ADM-PAY-09": (T+"billing/test_billing.py", "test_invoice_number_and_the_customers_copy"),
    "ADM-SCH-14": (T+"scheduling/test_scheduling_api.py", "test_a_manual_change_survives_a_rerun"),
    "ADM-SCH-17": (T+"scheduling/test_scheduling_api.py", "test_freeze_and_unfreeze_with_the_code"),
    "ADM-OPS-03": (T+"scheduling/test_operations.py", "test_skip_extends_once_moves_unreceived_payment"),
    "ADM-CNC-03": (T+"scheduling/test_operations.py", "test_completed_and_external_jobs_cannot_be_repeated"),
    "ADM-REF-06": (T+"directory/test_directory.py", "test_society_with_active_subscriptions_or_crew_cannot_be_deactivated"),
}

def coded(ids, note, code, tests):
    for rid in ids.split():
        OVERRIDES[rid] = {"status": "Implemented", "gap": None, "note": note,
                          "test_status": "Written; not run",
                          "extra": [ref(p, needle) for p, needle in code],
                          "test_refs": [ref(p) for p in tests]}


coded("SVC-07 SVC-12 SVC-14", "P01 coded: service verifies visit existence/ownership/Completed state and canonicalizes UUID before rating insert/update. Authorization/tag/edit regressions are written, not executed.",
      [(A+"support/service.py", "def rate_visit")], [T+"support/test_rating_authorization.py", T+"support/test_support.py"])
coded("ADM-CHK-05", "P02 coded: every ORM-created job snapshots its checklist; crew requirements/ticks and customer history use the issued definition. Migration 0025 backfills explicitly legacy snapshots; original overwritten labels cannot be reconstructed. Issued unfinished jobs also retain their definition. Migration and regression tests are unrun.",
      [(A+"scheduling/models.py", "def snapshot_job_checklist"), (A+"visits/checklists.py", "def items_for_job")], [T+"visits/test_checklist_snapshots.py", T+"visits/test_crew_jobs.py"])
coded("ADM-SUB-04", "P03 coded: reactivation activation requires a new first-service date, creates a new Due cycle with collision/idempotency guards, preserves old receipts and excludes old-epoch pauses/debt from the new cycle. Future first-cycle payments are not moved to renewal by cron. Tests written/unrun.",
      [(A+"billing/service.py", "def set_subscription_status"), (A+"changes/cycle.py", "def shift_days")], [T+"billing/test_gap_billing.py"])
coded("ADM-PAY-06", "P03 coded: pause/cancellation/early-end transactionally shifts affected unpaid plan due/cycle/overdue dates and pending plan boundaries; Received/voided/add-on records are protected. Manual future plan records without a cycle key are supported. Status/idempotency/early-end regressions written/unrun.",
      [(A+"changes/payment_dates.py", "def shift_unpaid_renewals"), (A+"changes/service.py", "def end_pause")], [T+"billing/test_gap_billing.py", T+"billing/test_billing.py"])
coded("ADM-CUS-15", "P03 coded: portal omits the previous interior day when changing to an exterior-only plan, while retaining deferred plan/price activation. Actual portal payload regression is written, not run.",
      [(W+"pages/customers/CustomersPage.tsx", "Save settings")], [W+"pages/customers/customers.test.tsx", T+"test_customer_administration.py"])
coded("CRW-ACC-12 CRW-SVC-10", "P04 coded: queue rows/files are partitioned by stable login UUID, auth changes dispose workers/clients, token retries cannot switch owner, and later stages stop after account switch. SQLite v2 retains unknown legacy rows in quarantine; original-owner uploads remain recoverable. Queue/store/identity regressions written/unrun; native SQLite upgrade/offline/restart still unverified.",
      [(M+"features/crew/upload/sqlite_store.dart", "class SqliteUploadQueueStore"), (M+"features/crew/crew_providers.dart", "crewUploadOwnerProvider")], [MT+"crew/queue_test.dart", MT+"crew/queue_store_test.dart", MT+"auth/refresh_account_switch_test.dart"])
coded("CRW-PRF-04 CRW-SVC-06", "P04 coded: photo/video size validation is strictly below 10/25 MB in capture, request, signed local PUT and confirmation; separate RC documents still permit exactly 5 MB. Boundary tests written/unrun. Native HEIC capture/decoding is still a device-validation requirement.",
      [(A+"media/service.py", "def valid_size"), (M+"features/crew/capture/media_capture.dart", "bytes >=")], [T+"media/test_uploads.py", MT+"crew/models_test.dart"])

coded("ONB-25 ONB-23 ONB-21", "P05 coded: personal/society then vehicle/parking/plan/preferences per car and final review; one vehicle has seven steps. Validated draft edits and position persist on Continue, restore from API, retain read-only fields and do not confirm/create payments. Migration 0026 and API/widget regressions are written/unrun.",
      [(A+"customers/service.py", "def save_draft"), (M+"features/customer/onboarding/onboarding_review_screen.dart", "int get _steps")], [T+"test_customer_home.py", MT+"customer/onboarding_flow_test.dart"])
coded("ONB-10", "P05 coded: Add Vehicle input formatter forces uppercase, including pasted registration; backend normalization retained. Widget assertion written/unrun.",
      [(M+"features/customer/vehicles/add_vehicle_screen.dart", "inputFormatters:")], [MT+"customer/add_vehicle_test.dart"])
coded("PAY-04", "P05 coded: review sums Due/Over due amounts payable today, shows per-vehicle statuses and GST-inclusive wording, and excludes Received/Initiated amounts. Review widget regressions written/unrun.",
      [(M+"features/customer/onboarding/onboarding_review_screen.dart", "final total =")], [MT+"customer/onboarding_flow_test.dart"])
coded("PAY-05 PAY-07", "P05 coded: QR widget encodes backend amount-bearing upi_uri; submitted payment response/view includes vehicle and service preferences. QR dependency resolved and client contract regenerated. API/DTO/widget regressions written/unrun; real UPI scan/payment and business values unverified.",
      [(A+"billing/service.py", "def _detail"), (M+"features/changes_money/pay_screen.dart", "QrImageView")], [T+"billing/test_gap_billing.py", MT+"changes_money/changes_money_test.dart"])
coded("HOME-02 HOME-05 C-07", "P06 coded: Home renders make/model/variant and named Rate today's clean; both Home action and completion strip open owned Service Details. Loading/no-completion/error handling retained. API/related widget/navigation regressions written/unrun.",
      [(A+"customers/service.py", "key=\"rate_today\""), (M+"features/customer/home/customer_shell.dart", "case 'rate_today'")], [T+"test_customer_home.py", MT+"customer_test.dart"])
coded("HOME-08 CHK-08", "P06 coded: successful check-in invalidates homeCheckInsProvider as well as pendingCheckInsProvider; a subscribed-provider regression verifies Home read refresh after submission. Written/unrun.",
      [(M+"features/support/checkin_screen.dart", "// CHK-08: refresh")], [MT+"support/support_test.dart"])
coded("CAL-05", "P06 coded: calendar projection/DTO includes finish time and checklist done/total; completed day card displays the summary. API projection and widget assertions written/unrun.",
      [(A+"customer_reads/calendar_view.py", "checklist_total=sum"), (M+"features/customer/calendar/day_card.dart", "checks done")], [T+"visits/test_checklist_snapshots.py", MT+"customer/screen_parity_test.dart"])
coded("VEH-03 ADM-REF-05 VEH-04", "P06 coded: Verified RC remains Verified; vehicle read DTO supplies society basement choices and parking sheet uses them. Old-response fallback retains B1-B4. API validation remains authoritative; widget/related API regressions written/unrun.",
      [(M+"features/customer/account/vehicle_account_section.dart", "vehicle.rcStatus == 'Verified'"), (A+"customer_reads/service.py", "parking_basements=")], [MT+"customer/screen_parity_test.dart", T+"customers_account/test_account.py"])
coded("FDBK-01", "P06 coded: one root feedback overlay covers confirmed customer routes and pushed detail/forms, using the root navigator for its sheet. Before onboarding/other roles excluded; old shell-only duplicate removed. Navigation/widget regression written/unrun.",
      [(M+"app.dart", "return FeedbackSideTab")], [MT+"customer_test.dart", MT+"support/support_test.dart"])
coded("SUP-05", "P06 coded: FAQ is app-bundled assets/content/faq.md parsed into expanders, with admin-only reactivation wording. Older API FAQ answer corrected. Parser/navigation regressions written/unrun.",
      [(M+"features/support/faq_screen.dart", "parseFaqMarkdown"), ("apps/mobile/assets/content/faq.md", "## What happens")], [MT+"customer/screen_parity_test.dart", MT+"customer_test.dart"])
coded("ADM-CRW-21", "P07 coded: crew registers current session metadata even without a push token; session API and portal show device/platform/app version with unknown-value fallback. Ownership/role and portal assertions written/unrun.",
      [(A+"crew/router.py", "def session_device"), (W+"pages/crew/panels.tsx", "Unknown device")], [T+"crew/test_crew.py", W+"pages/crew/crew.test.tsx"])
coded("ADM-CUS-08 ADM-PAY-01", "P07 coded: stable API limit/offset paging and portal Previous/Next controls, reset on search/filter changes. Payment society filtering is applied before paging. Tests cross old limits and identical sort values; exact-full last page may have an empty next page. Written/unrun.",
      [(A+"customers/administration.py", "offset: int = Query"), (W+"pages/payments/api.ts", "q.set(\"offset\"")], [T+"test_gap_admin_reads.py", T+"billing/test_gap_billing.py", W+"pages/customers/customers.test.tsx", W+"pages/payments/PaymentsPage.test.tsx"])
coded("ADM-CMP-01 ADM-CMP-02", "P07 coded: complaint summaries include linked vehicle; detail renders signed photos and protected linked visit/checklist/crew/proof view with retry. No-visit complaints honestly show no vehicle linkage. API role and portal display regressions written/unrun; real URL expiry/playback unverified.",
      [(A+"support/router.py", "def admin_complaint_visit"), (W+"pages/complaints/ComplaintDetailPage.tsx", "Complaint photo")], [T+"support/test_support.py", W+"pages/support/support.test.tsx"])
coded("ADM-ADD-11", "P07 coded: imported source records appear in customer service history and admin customer details with original dates/payment/notes. Unknown date/vehicle/completion/proof stay unknown; no synthetic completed visit/payment/subscription. Source IDs remain idempotent; imported records are a separate all-dates section. API privacy/unknowns and portal display regressions written/unrun.",
      [(A+"customers/history.py", "def imported_history"), (M+"features/customer/history/history_screen.dart", "Imported service history")], [T+"test_gap_admin_reads.py", T+"test_import.py", W+"pages/customers/customers.test.tsx"])

coded("ADM-ACC-14 ADM-CUS-16", "P08 coded: logout-all revocation and shared actor/target/reason/count/time audit commit together. Failure-to-insert regression asserts rollback preserves sessions; API role/session regressions written/unrun.",
      [(A+"identity/service.py", "actor_id: uuid.UUID"), (A+"identity/service.py", 'action="logout_all"')], [T+"test_gap_session_audit.py", T+"test_api.py", T+"test_first_sign_in.py"])
coded("ADM-CUS-14", "P08 policy encoded: admin plan/default-preferences edits are silent; explicit admin/customer skips and operations outcomes retain skip notifications under their separate requirements. Admin skips identify Priveo as actor. Source/API event regressions written/unrun.",
      [(A+"customers/administration.py", "admin plan and default preferences edits are silent"), (A+"notifications/emit.py", 'actor: str = "customer"')], [T+"test_customer_administration.py", T+"notifications/test_events.py"])
issue("ADM-ACC-10 ADM-CUS-10", "cross-client-refresh", "P08 adds foreground 30-second refresh plus app resume/browser focus/reconnect refresh; active customer/admin reads observe last committed writes, and draft fields are retained. Literal at-once propagation still needs a real-time transport. Refresh/API/component regressions written/unrun.", tests="Written; not run", extra=[(M+"core/network/read_refresh.dart", "readRefreshProvider"), (W+"api/queryDefaults.ts", "sharedReadOptions"), (T+"test_gap_session_audit.py", "test_admin_and_customer_reads")])
issue("ADM-ACC-01 ADM-ACC-09", "admin-alert-delivery", "P11 adds own-admin persisted alert email address/switch, portal control, durable recipient queue and configured Resend delivery with bounded retries/stable provider key. Email opt-out preserves inbox/push; missing key leaves pending delivery. Real phone push still awaits P10. Migration 0027 and API/portal regressions written/unrun; actual host/provider delivery unverified.", tests="Written; not run", extra=[(A+"support/email_delivery.py", "def deliver_pending"), (W+"pages/settings/AlertEmailSettings.tsx", "AlertEmailSettings"), (T+"support/test_alert_email_delivery.py", "test_disabled_email_preserves")])
coded("ADM-CMP-08", "P11 coded: cron configuration runs every five minutes; four-hour Raised threshold marker and inbox/email queue commit atomically under row locks. Dispatch failures retain inbox and bounded email retries. Boundary/repeat/rollback/provider tests written/unrun. Live host cadence and email delivery unverified; phone push remains P10.",
      [(A+"support/service.py", "commit=False"), ("services/api/vercel.json", '"schedule": "*/5 * * * *"')], [T+"support/test_alert_email_delivery.py", T+"support/test_support.py", T+"notifications/test_events.py"])

coded("ADD-14 ADD-15 ADM-ADD-10 ADM-ADD-12 ADM-SVS-10 CRW-SCH-05", "P12 coded after owner decision: admin creates a customer/vehicle without a plan or plan payment. Owned standalone Spa uses the subscriber catalogue/date/finish-by/cutoff/UPI/admin-confirmation/cancellation rules, payment-independent 120-minute scheduling, outcomes and visit proof/history. Portal and mobile expose it. Legacy unlinked requests stay honest; no synthetic subscription or historical rewrite. API/portal/mobile regressions written/unrun.",
      [(A+"customers/administration.py", "return v, None, None"), (A+"addons/service.py", "P12: identical Spa"), (W+"pages/customers/VehicleWizard.tsx", "Create a subscription"), (M+"features/changes_money/addon_screen.dart", "widget.standalone")],
      [T+"test_customer_administration.py", T+"addons/test_standalone_rules.py", T+"addons/test_addons.py", T+"scheduling/test_addon_lifecycle.py", W+"pages/customers/customers.test.tsx", MT+"changes_money/changes_money_test.dart"])
coded("ADM-CHK-07", "Owner authorized editable five-step Internal/Spa samples, portal editing and admin mobile read access. Defaults and migration 0028 update only untouched old samples; edited catalogue and issued snapshots survive. Seed/API/mobile regression sources written/unrun; migration unapplied.",
      [(A+"directory/defaults.py", "touchpoints"), (M+"features/admin_quick/actions/checklists_screen.dart", "AdminChecklistsScreen")], [T+"directory/test_directory.py", MT+"customer/admin_checklists_test.dart"])
coded("ADM-PAY-08 ADM-SET-04", "Owner specified 18% GST and environment mocks. New invoices snapshot exact paise taxable/GST/CGST/SGST/IGST amounts and supplier details; PDF/native summary expose them. Historical tax remains unrecorded. Seller fields are seeded/read-only; mock configuration produces development preview and is blocked outside dev. Mode is a mock split requiring offline configuration. Migration 0028 and regressions written/unrun; no live/legal delivery asserted.",
      [(A+"billing/tax.py", "def included_gst"), (A+"billing/service.py", "tax_details=self._tax_details"), (A+"directory/service.py", "Invoice seller values are seeded")], [T+"billing/test_gst_snapshot.py", T+"billing/test_invoice_pdf.py", T+"directory/test_directory.py"])
coded("ADM-FDB-07", "Owner decision preserves earlier category/tag/check-in names and historical buckets after renames; no historical rewrite or unified bucket migration is desired. Existing string snapshots retain them. Rename/earlier-feedback regression source written/unrun.",
      [(A+"support/models.py", "class Feedback"), (A+"support/service.py", "def patch_option")], [T+"support/test_support.py"])

DECISIONS = {"C-01": "ONB", "C-02": "ONB", "C-03": "PAY", "C-04": "SUB", "C-05": "NAV", "C-07": "HOME", "C-08": "SVC"}

def key_for(rid):
    return DECISIONS.get(rid) or ("-".join(rid.split("-")[:2]) if rid.startswith(("ADM-", "CRW-")) else rid.split("-")[0])

def read_rows(role, path):
    found = []
    for line, text in enumerate((ROOT/path).read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"^\| ((?:[A-Z]+-)?[A-Z]+-\d{2}) \| (.*?) \| (.*?) \|$", text)
        if not match:
            continue
        rid, requirement, definition = match.groups()
        g = GROUPS[key_for(rid)]
        change = OVERRIDES.get(rid, {})
        evidence = []
        for p in g["code"]:
            content = (ROOT/p["path"]).read_text(encoding="utf-8").splitlines()
            # Prefer the exact requirement marker where the implementation has one.
            line = next((i+1 for i, value in enumerate(content) if re.search(r"(?<![A-Z0-9-])"+re.escape(rid)+r"(?![A-Z0-9-])", value)), p["line"])
            evidence.append({"path": p["path"], "line": line})
        evidence += change.get("extra", [])
        tests = change.get("test_refs") or ([ref(*DIRECT[rid])] if rid in DIRECT else g["tests"])
        test_state = change.get("test_status", "Targeted regression present" if rid in DIRECT else "Related tests present")
        functional = "No dedicated live/device journey script located. In-process API/widget scenarios are in the test evidence."
        if rid.startswith("AUTH-") or rid in ("CRW-ACC-01", "CRW-ACC-02", "CRW-ACC-09", "ADM-ACC-04", "ADM-ACC-06"):
            functional = "Only narrow login/home smoke scripts exist; full scenario absent. API smoke has removed crew-home call; mobile integration has stale greeting. Not ready unchanged."
        found.append({"role": role, "id": rid, "requirement": requirement, "definition_status": definition,
                      "source": {"path": path, "line": line}, "implementation": change.get("status", "Implemented"),
                      "code": evidence, "note": change.get("note", g["note"]), "gap": change.get("gap"),
                      "tests": tests, "test_status": test_state, "test_limit": VERIFY.get(rid, "Evidence is source assertions, not measured exhaustive coverage. No tests rerun in this audit."),
                      "functional": functional})
    return found

def link(value):
    # Relative repository links keep the report usable on GitHub and in the workspace.
    rel = "../../" + value["path"]
    return f"[{value['path']}:{value['line']}]({rel}#L{value['line']})"

def safe(value):
    return value.replace("|", "&#124;").replace("\n", " ")

all_rows = []
for role, path in SOURCES.items():
    rows = read_rows(role, path)
    expected = {"customer": 195, "admin": 172, "crew": 59}[role]
    if len(rows) != expected:
        raise ValueError(f"Source census changed: {role}: {len(rows)} != {expected}")
    all_rows.extend(rows)
    counts = Counter(r["implementation"] for r in rows)
    header = f"# {role.title()} requirements: current row-by-row audit\n\n"
    header += f"Source review: {DATE}. Checkout `integration/complete-build`, base commit `d5aaad3` plus uncommitted 5.1/5.3 and packages 1-7 plus P08/P11/P12, GST, samples and optional planning code. All **{len(rows)} source rows** below are individually represented, including customer decision rows. This replaces the historical table and grouped overlays.\n\n"
    header += "**Implemented** means a matching API/client code path was located; it is not a runtime pass. **Partial** means the note identifies an unmet criterion. **Open** requires an owner decision/content. Unit/component evidence names actual files or targeted assertions; related tests do not prove every subcriterion. No tests, builds, migrations or coverage measurements were run. Existing baseline results and functional-script readiness are explained in [the full report](requirements-audit.md).\n\n"
    header += "Counts: " + ", ".join(f"{k}: **{v}**" for k, v in sorted(counts.items())) + ". These are source-review counts, not test coverage percentages.\n\n"
    header += "| ID and source | Requirement | Implementation and evidence | Unit/component tests | Functional script readiness |\n|---|---|---|---|---|\n"
    lines = []
    for r in rows:
        code = "<br>".join(link(p) for p in r["code"])
        tests = "<br>".join(link(p) for p in r["tests"])
        lines.append(f"| <a id=\"{r['id'].lower()}\"></a>**{r['id']}**<br>{link(r['source'])} | {safe(r['requirement'])} | **{r['implementation']}**. {safe(r['note'])}<br>{code} | **{r['test_status']}**.<br>{tests}<br>{safe(r['test_limit'])} | {r['functional']} |")
    (OUT/f"{role}.md").write_text(header + "\n".join(lines) + "\n", encoding="utf-8")

actual_ids = {r["id"] for r in all_rows}
unknown = set(OVERRIDES) - actual_ids
if unknown:
    raise ValueError(f"Unknown override IDs: {sorted(unknown)}")
(OUT/"requirements-audit.json").write_text(json.dumps({"date": DATE, "base_commit": "d5aaad3", "runtime_tests_run": False, "rows": all_rows}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

# Index every available regression declaration without executing or importing it.
inventory = []
for base in ["services/api/tests", "apps/mobile/test", "apps/mobile/integration_test", "apps/web/src"]:
    for p in (ROOT/base).rglob("*"):
        if not p.is_file() or not (p.name.startswith("test_") and p.suffix == ".py" or p.name.endswith("_test.dart") or p.name.endswith(".test.tsx") or p.name.endswith(".test.ts")):
            continue
        text = p.read_text(encoding="utf-8")
        pattern = r"(?m)^(?:async )?def (test_\w+)" if p.suffix == ".py" else r"\b(?:testWidgets|test|it)\(\s*['\"]([^'\"]+)"
        for match in re.finditer(pattern, text):
            inventory.append({"path": p.relative_to(ROOT).as_posix(), "line": text[:match.start()].count("\n")+1, "name": match.group(1)})
inv = "# Test source inventory\n\nStatic declaration index; no tests executed. Names may be the first literal segment of a concatenated Dart title. A listed file is not evidence of complete requirement coverage.\n\n| Test declaration | Source |\n|---|---|\n"
inv += "\n".join(f"| {safe(i['name'])} | {link(i)} |" for i in inventory) + "\n"
(OUT/"test-inventory.md").write_text(inv, encoding="utf-8")
print(json.dumps({"rows": len(all_rows), "roles": {role: dict(Counter(r['implementation'] for r in all_rows if r['role']==role)) for role in SOURCES}, "test_declarations_indexed": len(inventory)}, indent=2))

# Numbered rules are requirements too; link each one to the implementation review.
RULE_IDS = {
    "customer": ["ADM-SVS-01", "ADD-15 ADM-OPS-03", "SKIP-02 SKIP-05", "PAUSE-06 ADM-PAY-06", "ONB-16", "ONB-11", "ADM-SUB-01", "SVC-03 SVC-06", "SVC-07 CRW-RAT-01", "ADM-CMP-08", "VEH-04 VEH-09", "PAY-04 ADM-PAY-08", "VEH-09", "PAY-05 ADM-PAY-06", "NOTIF-02", "NAV-01", "CRW-SVC-06 ONB-22", "SUB-11 ADM-SUB-04", "VEH-09", "FDBK-06", "FDBK-04", "NOTIF-05", "CHK-01 CHK-03 CHK-08", "FDBK-03", "ADM-OPS-03", "PAUSE-06 ADM-PAY-06", "CAL-09 ADM-CNC-03", "NAV-01", "AUTH-03 AUTH-16", "AUTH-14", "ADD-15 ADM-SVS-10"],
    "admin": ["ADM-CRW-05", "ADM-CRW-19", "ADM-SVS-01", "ADM-SVS-07", "ADM-SVS-10", "ADM-SCH-01", "ADM-SCH-14 ADM-SCH-17", "CAL-10 CRW-SCH-01", "ADM-SCH-21", "ADM-CUS-10", "ADM-PAY-02", "ADM-CUS-16", "ADM-ACC-07", "ADM-ACC-01", "ADM-OPS-03", "ADM-CUS-11", "ADM-CRW-01", "ADM-CHK-05", "CRW-CNC-05", "ADM-SCH-25 ADM-SCH-27", "ADM-SUB-04 ADM-PAY-06", "ADM-CUS-03", "ADM-PAY-08", "ADM-ACC-10", "ADM-ADD-12"],
    "crew": ["CRW-ACC-01", "CRW-ACC-02", "CRW-SCH-01", "CRW-SCH-13", "ADM-CHK-05", "CRW-SVC-08", "CRW-SVC-06", "CRW-CNC-01", "CRW-SVC-12", "CRW-ACC-08", "CRW-SCH-01"],
}
by_id = {r["id"]: r for r in all_rows}
rules = []
for role, path in SOURCES.items():
    active = False
    for n, line in enumerate((ROOT/path).read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"## \d+\. Business rules", line):
            active = True
            continue
        if active and line.startswith("## "):
            break
        m = re.match(r"(\d+)\. (.*)", line) if active else None
        if not m:
            continue
        number, requirement = m.groups()
        ids = RULE_IDS[role][int(number)-1].split()
        records = [by_id[rid] for rid in ids]
        state = "Partial" if any(r["implementation"] == "Partial" for r in records) else "Open" if any(r["implementation"] == "Open" for r in records) else "Implemented"
        note = " ".join(dict.fromkeys(r["note"] for r in records))
        if (role, int(number)) in [("customer", 28), ("admin", 24), ("crew", 11)]:
            state, note = "Partial", "Shared dd-Mon-yy helpers exist, but admin audit/session views still use browser locale formatting; crew timestamps use device local time rather than guaranteed IST. No all-screen formatting regression."
        if role == "customer" and int(number) == 10:
            note += " The software records/escalates overdue complaints; a human reply within four hours is an operational SLA, not guaranteed by code."
        if role == "admin" and int(number) == 6:
            note += " Manual scheduling matches this rule. Later user-requested automatic day/week planning is a supplementary change, now coded/default-disabled with unrun regressions."
        if role == "customer" and int(number) == 12:
            state, note = "Implemented", "Owner specified 18% inclusive GST and mocks. Issued paise breakdown snapshots and review/PDF/native wording are coded; migration/regressions unrun, live supplier/mode configuration deferred."
        rules.append({"role": role, "number": int(number), "requirement": requirement, "source": {"path": path, "line": n}, "ids": ids, "implementation": state, "note": note})
assert len(rules) == 67, len(rules)

def matrix_ids(ids):
    return ", ".join(f"[{rid}]({by_id[rid]['role']}.md#{rid.lower()})" for rid in ids)

rules_text = "# Business-rule audit\n\nAll 67 numbered rules, including complete original wording. Source review only. Implementation/test evidence is linked through the corresponding refreshed matrix rows; no runtime pass is claimed. A related test is not proof that every sentence is asserted. Live/device journey coverage remains missing except the narrow scripts described in the full report.\n\n| Rule/source | Complete rule | Implementation | Code and unit/component evidence | Functional script |\n|---|---|---|---|---|\n"
for r in rules:
    rules_text += f"| {r['role'].title()} BR-{r['number']:02}<br>{link(r['source'])} | {safe(r['requirement'])} | **{r['implementation']}**. {safe(r['note'])} | {matrix_ids(r['ids'])} — follow each row's code and test links; unit completeness not established by related tests. | No dedicated live journey located; deployed timers/device behavior not verified. |\n"
(OUT/"business-rules.md").write_text(rules_text, encoding="utf-8")

# Every entity sentence gets a source row, including overlapping entities across roles.
ENTITY_GROUP = {
    "Customer": "ONB", "Verification code": "AUTH", "Add-on": "ADD", "Add-on request": "ADD", "Society": "ADM-REF", "Vehicle": "VEH", "Parking": "VEH", "Subscription": "SUB", "Slot assignment": "ADM-SCH", "Cutoff override": "CAL", "Service visit": "SVC", "Checklist item": "ADM-CHK", "Media": "CRW-SVC", "Skip / Pause": "PAUSE", "Complaint": "CMP", "Plan": "ADM-SET", "Invoice": "ADM-PAY", "Payment": "PAY", "Crew member": "CRW-PRF", "Notification preference": "SET", "Device token": "NOTIF", "Feedback": "FDBK", "Feedback category": "ADM-FDB", "Positive rating tag": "ADM-FDB", "Visit rating": "SVC", "Check-in": "CHK", "Check-in category": "ADM-FDB", "User login": "AUTH", "Admin user": "ADM-ACC", "Customer login": "AUTH", "Admin preferences": "ADM-PRF", "Cutoff request": "ADM-SCH", "Working hours": "ADM-CRW", "Exception": "ADM-CRW", "Service": "ADM-SVS", "Working slot": "ADM-SVS", "Capacity": "ADM-CAP", "Schedule": "ADM-SCH", "Scheduled visit": "ADM-SCH", "Scheduler suggestion": "ADM-SCH", "Secret code": "ADM-SCH", "Audit entry": "ADM-CUS", "Feedback category, positive rating tag, check-in category": "ADM-FDB", "Vehicle catalogue": "ADM-REF", "Crew login": "CRW-ACC", "Session": "ADM-CRW", "Checklist": "ADM-CHK", "Could-not-complete reason": "ADM-CNC", "Could-not-complete record": "CRW-CNC", "Invoice settings": "ADM-SET", "Needs scheduling entry": "ADM-SCH", "Add-on / Add-on request": "ADD", "Payment settings": "ADM-SET", "Support settings": "ADM-SET", "Job card": "CRW-SCH", "Checklist progress": "CRW-SVC",
}
ENTITY_GAPS = {
    "Invoice": ("Representation present; unvalidated", "Supplier and 18% GST paise snapshots are coded for new issues; old tax remains unrecorded. Mock mode/supplier are environment configuration. Migration 0028 and regressions unrun."),
    "Invoice settings": ("Representation present; unvalidated", "Supplier values are environment seeded/read-only in portal/API. Explicit seed replaces mocks only. Real values are deferred by owner; tests/migrations unrun."),
    "Session": ("Representation present; unvalidated", "P07 adds crew metadata registration/API/UI. P08 adds atomic actor/target/reason/count/time logout-all audit; metadata/audit regressions are unrun."),
    "Checklist item": ("Representation present; unvalidated", "P02 adds issued key/label/order snapshots alongside original ticks; migration 0025 and regressions are written/unrun. Historical overwritten labels use an explicit legacy fallback."),
    "Checklist": ("Representation present; unvalidated", "Issued history snapshots and owner-approved editable five-step samples are coded; migration 0028 preserves admin-edited samples. Migrations/tests unrun."),
    "Visit rating": ("Representation present; unvalidated", "P01 adds service existence/ownership/completion checks with authorization regressions written/unrun."),
    "Add-on request": ("Representation present; unvalidated", "Subscriber and owner-specified standalone booking/payment/scheduling/outcome/proof paths are coded. Unknown legacy records remain unknown; tests unrun."),
    "Add-on / Add-on request": ("Representation present; unvalidated", "Standalone uses subscriber rules without creating a subscription; owned vehicle required. API/client/regression sources written/unrun."),
    "Secret code": ("Partial (technical)", "Backend checks configured code, but stores/compares plaintext settings rather than hashed configuration required by tech-stack; settings allow changing the fixed MVP word."),
    "Device token": ("Partial", "Token/device model and registration APIs exist; default mobile provider returns null and real FCM delivery is missing."),
}
entities = []
for role, path in SOURCES.items():
    active = False
    for n, line in enumerate((ROOT/path).read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"## \d+\. Data entities", line):
            active = True
            continue
        if active and line.startswith("## "):
            break
        m = re.match(r"- \*\*(.*)\*\*: (.*)", line) if active else None
        if m:
            name, description = m.groups()
            g = GROUPS[ENTITY_GROUP[name]]
            state, note = ENTITY_GAPS.get(name, ("Representation present", "Matching model/read/service representation located. Field-by-field runtime persistence and exhaustive assertions are not established; see related feature rows."))
            entities.append({"role": role, "name": name, "requirement": description, "source": {"path": path, "line": n}, "implementation": state, "note": note, "code": g["code"], "tests": g["tests"]})
ent_text = "# Data-entity requirement audit\n\nEvery entity bullet is represented, including duplicates between roles. These are screen-derived data requirements, not a demand for a separate table per noun. Source representations and known omissions are separated from runtime validation.\n\n| Entity/source | Full required fields | Representation and limitations | Code | Unit/component evidence | Functional script |\n|---|---|---|---|---|---|\n"
for e in entities:
    ent_text += f"| {e['role']}: **{e['name']}**<br>{link(e['source'])} | {safe(e['requirement'])} | **{e['implementation']}**. {safe(e['note'])} | {'<br>'.join(link(p) for p in e['code'])} | Related only; exhaustive field coverage not established.<br>{'<br>'.join(link(p) for p in e['tests'])} | No complete live persistence journey located. |\n"
(OUT/"data-entities.md").write_text(ent_text, encoding="utf-8")

counts = Counter(r["implementation"] for r in all_rows)
test_counts = Counter(r["test_status"] for r in all_rows)
gaps = {}
for r in all_rows:
    if r["gap"]:
        gaps.setdefault(r["gap"], []).append(r)

report = f"""# Full requirements implementation audit — {DATE}

## Result and scope

Reviewed the repository Markdown requirements and current source on `integration/complete-build`, committed baseline `d5aaad3` plus the uncommitted invoice/video, package and owner-decision changes. This is a **static implementation and test-source audit**, not a successful execution report. At the owner's instruction **no unit tests, functional tests, builds, lint, migration checks or coverage measurements were run**.

Packages 1-7 plus P08/P11/P12 and owner-approved changes now address **45 previously Partial rows**, with targeted regressions written/unrun. P05–P07 address 24 more rows. The original [79-row implementation plan](gap-implementation-plan.md) retains its baseline mapping; current pending counts below reflect the changes. Prepared [P01–P04 scenarios](packages-1-4-functional-scenarios.md), [P05–P07 scenarios](packages-5-7-functional-scenarios.md) and the handoff describe validation and legacy-data limits. P08 audit/policy and P11 escalation address four additional rows; 30-second refresh still falls short of at-once propagation and full alert delivery awaits P10 push. P12, checklist samples and GST were specified by the owner and coded. Optional planning is coded/default-disabled; environment mocks are added and historical category names preserved. Prepared [P08/P11 scenarios](packages-8-11-functional-scenarios.md) document those limits. See [the owner decisions](../reqs/owner-decisions-2026-10-13.md) and [prepared scenarios](standalone-planning-gst-functional-scenarios.md). Migrations 0024-0028 are written but unapplied.

The previous coverage tables and grouped overlays are replaced. The review includes **426 ID rows**, **67 numbered business rules**, and **{len(entities)} data-entity bullets**. Complete source wording, source locations, code links, test evidence and functional-script verdicts are retained in the detailed files. Repeated entity/rule requirements are intentionally counted where they occur; these counts are not unique features or coverage percentages.

| Document | Implemented source path | Partial | Open | Total |
|---|---:|---:|---:|---:|
"""
for role in SOURCES:
    c = Counter(r["implementation"] for r in all_rows if r["role"] == role)
    report += f"| [{role.title()}]({role}.md) | {c['Implemented']} | {c['Partial']} | {c['Open']} | {sum(c.values())} |\n"
report += f"""| Total | {counts['Implemented']} | {counts['Partial']} | {counts['Open']} | 426 |

**Implemented means a corresponding code path was located**, with no known source-level gap recorded for that row. It does not certify every acceptance criterion or runtime behavior. Partial identifies a concrete unmet criterion; Open means required owner input is unresolved. Provider/configuration dependencies can remain on rows whose UI/API logic is implemented. The test column separately identifies targeted assertions versus related-module evidence; **related tests are not a finding that unit coverage is complete**.

Detailed deliverables:

- [Customer matrix](customer.md), [admin matrix](admin.md), [crew matrix](crew.md): every numbered requirement, including the seven customer decision rows.
- [Business rules](business-rules.md): all 31 customer, 25 admin and 11 crew rules.
- [Data entities](data-entities.md): every entity bullet and known missing data fields.
- [Test declaration inventory](test-inventory.md): {len(inventory)} statically indexed declarations across API, app, app integration and portal. Parametrization, skips and generated/concatenated titles mean this is not a runnable test-case count.
- [Machine-readable evidence](requirements-audit.json): requirement text, verdict, source/code/test locations and remaining limitations.

## Consolidated pending functionality and deviations

This is the full consolidated list of **identified source gaps and completion dependencies**, rather than another summary of the old Step 5 plan. Each entry links to the requirement rows. Implemented-but-unverified dependencies are included so they do not disappear from the remaining work.

| Finding | Affected requirements | What remains | Classification |
|---|---|---|---|
"""
for gap, records in gaps.items():
    notes = " ".join(dict.fromkeys(r["note"] for r in records))
    classification = "Owner decision/content" if any(r["implementation"] == "Open" for r in records) else "Code/UI gap" if any(r["implementation"] == "Partial" for r in records) else "Configuration/verification or recorded limitation"
    report += f"| {gap} | {matrix_ids([r['id'] for r in records])} | {safe(notes)} | {classification} |\n"
report += """
Additional cross-cutting items outside a single numbered row:

1. **5.4 notification destinations:** customer inbox already routes visits, payment, complaint and check-in. Crew inbox drops reference ID and taps only mark read. Admin alert navigation handles only a subset of reference types. Finish the missing destinations, authorization checks and signed-out/cold-start replay; do not rebuild the destinations already present.
2. **5.6 production storage:** `app/media/store.py` returns only `LocalObjectStore`. The protocol/signing/upload-confirmation and ownership tests exist; no S3 implementation is selected. Add configured private S3 storage, verified byte/content checks, expired/incomplete-upload cleanup and production URL handling. Do not count a local store as a deployed S3 integration.
3. **5.8 automatic next-period planning:** coded, disabled by default. Admin must supply an IST time to enable it. Minute-check cron creates the next configured Daily/Weekly/Monthly draft for active societies, preserves existing schedules, tracks target/lease/retries and raises error alerts. Migration 0028, concurrent-worker checks, host cadence and regressions are unrun. No deployment was performed; manual planning remains available.
4. **Date/time consistency:** shared formatters exist, but portal audit/session timestamps still use browser locale; crew timestamps use device local time. Finish the all-role dd-Mon-yy/IST policy.
5. **Proof photo expiry:** video retry refreshes signed proof URLs; the photo viewer has no equivalent automatic refresh while open. Native HEIC/photo rendering still needs device validation. Step 5.3 is coded, not proven on devices; the player is a separate screen rather than literal inline playback.
6. **Option rename history:** owner explicitly keeps earlier names/data and separate historical buckets. No rename migration is desired; preservation regression source is written/unrun.
7. **Live business values:** UPI/QR, support contacts, legal document URLs, seller identity/GSTIN and sender domain are development defaults or unverified. This audit does not claim that external accounts/credentials do not exist. Pre-login support values come from environment settings while signed-in support comes from directory settings; reconcile the two sources.
8. **MVP rule configuration:** owner authorized configurable cycle/deadline/unfreeze policies; prescribed values remain defaults. First onboarding cycle now uses the configured length. The unfreeze code remains plaintext, contrary to the stack's hashed-config target; this technical hardening remains pending.

The existing operations skip extensions, next-day retries, media closed-job guard, manager attendance/hours, vehicle job-card photos, admin reference CRUD and removal of crew rating access are present. Old matrix statements saying these are wholly unbuilt are superseded.

## Unit and component coverage assessment

There are existing service/solver tests, API TestClient scenarios with test databases, Flutter widget/repository tests with fakes, and portal React Testing Library tests with mocked HTTP. These are meaningful source evidence but are different levels of testing. API router/database scenarios are component/in-process functional tests; calling every one a pure unit test would be inaccurate.

The per-row test-evidence distribution is:

| Evidence classification | Requirement rows |
|---|---:|
"""
for state, number in sorted(test_counts.items()):
    report += f"| {state} | {number} |\n"
report += """
Rows with only related tests **do not have established complete acceptance coverage**. This report explicitly leaves that unproven instead of upgrading them to “Unit Tested >95%”. The declaration inventory enables inspection of actual assertion sources. New invoice PDF/video and P01-P07 tests are written but unexecuted; migrations `0024` through `0028` remain unapplied.

Packages 1–7 now have written API/component regressions for rating authorization, checklist snapshots, billing corrections, queue isolation/media boundaries, onboarding drafts/order/totals, uppercase paste, payment QR/context, Verified RC/configured parking, calendar timing/counts, check-in refresh, global feedback, FAQ parsing, crew metadata, customer/payment paging, complaint proof and imported history. These are unexecuted. P08/P11 add audit rollback, actor/count, last-committed reads, refresh lifecycle, email suppression/retry/address changes and escalation boundary/rollback sources, also unrun. Remaining regression gaps include native queue restart/SQLite upgrade on devices; notification destination authorization/cold start; all-role date formatting; save/share PDF lifecycle. Written scenarios do not establish runtime acceptance or measured coverage.

Historical Step 4 results in the handoff: 409 SQLite API tests, 129 affected-module PostgreSQL tests, 68 portal tests, 191 mobile tests with 11 skips. These are recorded prior results, **not a new run and not evidence for the latest invoice/video code**. No current line/branch coverage measurement or above-95% result is available in this audit. Feature-status stages are not promoted.

## Functional scripts: what is ready

| Existing artifact | Scope | Source readiness and remaining work |
|---|---|---|
| `services/api/scripts/smoke_test.py` | Health, bad-password path, three role logins/homes | **Stale, not ready unchanged:** requests `/v1/crew/home`, which has been removed. Requires credentials/seeded records. Repair this before using it as a deploy gate. It does not cover MVP business journeys. |
| `apps/mobile/integration_test/logins_test.dart` | Role sign-in/home/sign-out on device/emulator | **Stale, not ready unchanged:** expects old `Hello,` greeting while current customer greeting changes by time. Seed/onboarding assumptions need alignment. It does not cover operations/payment/proof journeys. |
| `apps/mobile/test/live_api_test.dart` | Narrow live API auth/home/privacy | **Conditional:** skips without live defines; needs the intended seeded API. It is not a full device functional suite. |
| API test scenarios under `services/api/tests/` | Scheduling, lifecycle, billing, support, role boundaries against a test DB | **Present as in-process scripts:** isolated database/fakes, not live-provider/device journeys. New PDF dependency/migration checks remain pending; tests not run in this audit. |
| Flutter widget and portal RTL files | Screen interactions with injected/mocked repositories/HTTP | **Present as component scripts:** do not establish native permissions, media decoding, real QR payments, real email/push or browser end-to-end behavior. |
| `apps/mobile/tool/push_apk.ps1` | Builds current checkout's dev APK, copies to phone Downloads | **Build/distribution helper only:** contains no functional assertions. It does not constitute functional test coverage. |
| Playwright/Cypress admin browser suite | Main portal journeys | **No suite located.** Vitest/RTL tests exist; Playwright remains a stack/testing target. |

Complete cross-role functional scripts still needed:

1. Admin creates customer → real email first-sign-in/reset → customer review/pay → admin receipt/activation → second vehicle in another society.
2. Crew roles/hours/exceptions/pairing → manual plan/rerun/swap/suggestion → freeze → crew/customer assignment → skip/pause/cutoff and late work after freeze.
3. Crew checklist + compressed photos/video → loss of connection/restart/account switch → upload confirmation → completion → owned customer proof/history/rating.
4. Missed Exterior/Internal/Spa → valid next-day retry or operations skip → no duplicate jobs/extensions → correct customer calendar and unpaid payment dates.
5. Renewal/Over due/seven-day inactivity/reactivation → check-in/reminder preferences → deployed authorized cron → correct notifications, routing and no duplicates.
6. Complaint with vehicle/visit/photos → admin status/note/actor → four-hour escalation → customer notification; feedback/tag/category edits and consent/history.
7. Received payment → issued invoice snapshot/GST → PDF view/save/share; expired URLs, failure/retry, roles/ownership and native behavior.
8. Portal cookie/CSRF/inactivity/logout-all; phone admin inactivity; all-role privacy, formatting and large-list behavior.

These are **missing functional coverage**, not claims that the underlying functionality is all missing. Functional execution stays deferred until requested.

## Technical Markdown targets and actual code

Architecture is marked draft; stack choices are decided. Later documented owner decisions take precedence: customer four tabs and no crew ratings override the old architecture shells; the 10-Oct fixed per-role appearance documented in build-and-release supersedes earlier theme-switch proposals. V2 items (public signup, gateways/AutoPay, crew self-password/leave/swaps, two-factor auth and society transfers) are not counted as MVP missing code.

| Source target | Code/source evidence | Assessment | Unit/functional evidence |
|---|---|---|---|
| Flutter/Riverpod/go_router/Dio/secure tokens | `apps/mobile/pubspec.yaml`, `lib/core/auth`, `lib/core/routing` | Present; no native security-storage verification this audit | Auth/widget tests; live/device journey incomplete |
| FastAPI/Pydantic/SQLAlchemy/Alembic/Postgres/Argon2/OR-Tools | API project/config, identity and scheduling modules; migrations | Present; migrations 0024-0028 not checked/applied | Service/router/solver tests; historical Postgres results only |
| Three audience OpenAPI schemas (architecture decision 2) | `packages/api-contract/openapi.json`, export generator, generated Dart API | One combined schema instead of three; role guards still present | Role/schema tests are not audience-contract separation |
| In-process background solver (architecture decision 3) | `app/scheduling/router.py::run` calls service directly | Synchronous request execution; no durable job/progress/retry worker. Separate from automatic planning gap | Solver/scenario tests exist; load/recovery functional script missing |
| Drift cached reads/checklists and offline writes | `pubspec.yaml`, crew queue/checklist repositories | sqflite media queue exists; Drift/cached last-good reads/local checklist and missed writes are absent | Queue fakes exist; offline shift/device journey missing |
| Workmanager background uploads, resume-on-open | Mobile queue and pubspec | Resume-on-open/connectivity exists; no Workmanager worker while app closed | Native background/restart assertions missing |
| Camera/image_picker/video compression/HEIC | capture modules, API media validation | Capture/compression exists; exact bounds/native HEIC need work/validation | Upload/router/widget tests; native decoding pending |
| Firebase FCM/APNs/local foreground notifications | LoggingPushSender/NoPushTokenProvider; no Firebase deps | Missing real adapter/SDK/native integration | Mocked event tests only |
| Resend email and retry | `platform/email.py`, identity/account/customer flows, support notifier | Customer code/welcome and P11 admin alert Resend adapters are coded; persisted recipient preferences and bounded durable retries are written/unrun. Live delivery/bounces/provider behavior unverified | Mocked delivery/failure tests; live script missing |
| Private S3/CloudFront, upload cleanup, image derivatives | `media/store.py` only local store | S3 integration/retention cleanup/resize derivatives absent | Local signed URL and ownership tests only |
| ReportLab invoice/PDF in S3 | `billing/pdf.py`, issued snapshots, PDF endpoints | ReportLab code written; no S3-stored PDF or GST breakdown/save/share | New tests unrun; native/browser journey missing |
| Web React/Vite/Query/router, generated typed client | `apps/web/package.json`, API client and app/pages | Core present; verify generated schema use separately from handwritten feature DTOs | Vitest/RTL; no browser E2E |
| TanStack Table, React Hook Form/Zod, Tailwind/shadcn, dnd-kit, Recharts | Web package dependencies, custom tables/forms/Board/components | Decided libraries are absent; custom controls provide parts of behavior. Record a stack deviation; paging/functionality gaps remain separately | Component tests do not prove library/design parity |
| Bell polling, shared admin services, cookie/CSRF/session expiry | AlertBell, webauth/platform/websession, shared routes | Present; email/push/cross-client immediate refresh/audit gaps above | Auth/CSRF/component tests; live session journey missing |
| Force-update/minimum version gate | Public config endpoint, mobile startup/router | Version config exists; enforced app update gate not located | Native old-version scenario missing |
| Crashlytics/Sentry/CloudWatch structured alarms | Mobile dependencies, API middleware, deployment workflow | Request IDs present; crash SDK/production alarms not established | No crash/alarm functional verification |
| Brand tokens/fonts/native splash/icon | Token generators, theme, bundled fonts/assets | Present with documented fixed role themes/temporary raster mark. Master vectors await owner | Golden source exists; visual/130% text-scale/contrast pass pending |
| `/v1` versioning/contract checks/standard errors | API routers/errors/export and CI | Present; detailed backward compatibility and all-route errors require later validation | Contract/auth/validation tests; not rerun |
| Single module service boundaries/event coupling | Cross-module SQL reads in billing/scheduling/customer_reads | Architecture boundary ideal is not fully followed; functional implementation exists | Refactor target, not automatically an MVP feature omission |
| Environments/AWS ECS/RDS/Secrets/S3/EventBridge/portal hosting | `api-deploy.yml`, Vercel config; documented AWS switch; no infra provisioning tree | Workflow branch exists, not proof of production/staging resources. Dev Vercel/Neon is an explicit later choice | External setup/live configuration not audited |
| Android CI/signing/Play pipeline | `.github/workflows/mobile-*.yml`, fastlane/android | Pipeline source exists; repo secrets/accounts/release delivery not established. PR native-build coverage target still needs review | Login integration stale; no release executed |
| iOS/macOS signing/TestFlight pipeline | iOS scaffold, workflow inventory | iOS scaffold exists; no iOS release workflow located | Native iOS/permissions/media/push testing pending |
| >95% rule coverage, goldens, load/security/restore checks | CI/tests and historical reports | Tests exist; no current >95% measurement, full E2E, realistic scheduler load, accessibility or restore evidence | Validation/release work pending; not executed here |

## Production network/access checkpoints

N1–N14 are **release targets**, not certifications inferable from application source. No cloud credentials, secrets, DNS, current CI runs or deployed configuration were inspected. The development exception (Vercel/Neon over public TLS) is documented; it must not be called a compliant private production deployment.

| Checkpoint | Static evidence / current limitation | Verdict |
|---|---|---|
"""
security_notes = [
    "Deploy workflow can use AWS, but no live load balancer/DNS/TLS/public endpoint inventory was checked.",
    "No verified private ECS subnet/security-group configuration in this audit.",
    "No verified private RDS public flag/security-group configuration; dev Neon is documented exception.",
    "Database TLS/configuration does not prove encryption/backups or a successful restore.",
    "Dev deploy directly runs migration/seed from CI. Production ECS one-off migration/break-glass policy is unverified.",
    "AWS deploy workflow uses role assumption/OIDC path; actual IAM trust/least privilege unverified.",
    "Application reads environment secrets; deployed Secrets Manager injection and log/image/repository secret audit unverified. No secret values read.",
    "NAT/S3 gateway endpoint/egress security configuration unverified.",
    "Public authorized cron routes and Vercel entries exist. No private EventBridge task configuration verified; automatic planner coded/default-disabled; host deployment unverified.",
    "Local signed-media ownership/expiry checks exist; private S3 bucket/public-access policy and exact byte bounds incomplete/unverified.",
    "API lockout/code limits exist; WAF deployment/rate rules unverified.",
    "Environment flags and Android dev/prod exist; actual separate prod/staging databases/buckets/secrets unverified.",
    "RequestIdMiddleware exists; CloudWatch infrastructure/security-change alarms and delivery unverified.",
    "Swagger/ReDoc disabled in create_app, but default /openapi.json is still enabled. Production needs disabling/protection; mock code is production-gated in identity configuration.",
]
for i, note in enumerate(security_notes, 1):
    report += f"| [N{i}](../../docs/architecture.md#71-network-and-access-checkpoints) | {note} | {'Partial code; deployment unverified' if i in (6,7,9,10,11,14) else 'Deployment verification pending'} |\n"
report += """
## Document reconciliation and audit manifest

Latest functional specs take precedence over historical component/build snapshots. Requirements are not renumbered. Owner decisions of 13 Oct resolve standalone/checklist content, GST mocks, configurable policies and optional planning; the decision record supersedes older undecided wording. `docs/system-component-diagram.md` describes Phase 0 and falsely suggests the current portal/database/scheduler are absent; treat it as historical. The overnight/build/release documents retain historical milestone descriptions. README previously advertised older requirement versions; versions are corrected with this audit. The handoff's Step 5 list remains useful sequencing, but is no longer a complete list of missing functionality.

All repository-authored Markdown files found outside dependency/build/cache directories were included in document review. The line counts below are source inventory counts, not a claim that every prose line is an independent feature. Requirement tables/rules/entities are transcribed into audit rows; technical/delivery decisions are assessed above; instructions/how-to/historical claims and V2 exclusions are reconciled rather than silently counted as MVP gaps. The iOS launch-image README is template customization guidance, not a product requirement. New generated audit artifacts are deliverables, not new input requirements.

| Markdown input | Lines | Treatment |
|---|---:|---|
"""
inputs = ["README.md", "CLAUDE.md", "docs/architecture.md", "docs/build-plan.md", "docs/build-and-release.md", "docs/codex-handoff-plan.md", "docs/overnight-build-report.md", "docs/system-component-diagram.md", "docs/tech-stack.md", *SOURCES.values(), "docs/reqs/owner-decisions-2026-10-13.md", "docs/coverage/customer.md", "docs/coverage/admin.md", "docs/coverage/crew.md", "apps/mobile/README.md", "apps/web/README.md", "apps/mobile/ios/Runner/Assets.xcassets/LaunchImage.imageset/README.md"]
for path in inputs:
    content = (ROOT/path).read_text(encoding="utf-8")
    treatment = "Complete per-ID/rule/entity audit" if path in SOURCES.values() else "Historical coverage fully replaced by current per-row matrix" if path.startswith("docs/coverage/") else "Technical/release target reconciliation" if path in ("docs/architecture.md", "docs/tech-stack.md", "docs/build-plan.md", "docs/build-and-release.md") else "Historical/status/instruction review; not independent feature counts"
    report += f"| {link(ref(path))} | {len(content.splitlines())} | {treatment} |\n"
report += """
## Implementation ordering after this audit

1. Packages 1–7 code and targeted tests are now written; validation remains deferred. P08/P11 coding is recorded with remaining real-time/push dependencies. P12 and the owner-approved job/samples/GST changes are coded; remaining targets are PDF save/share, inline video, real-time refresh, P10 push, S3 and date/security/release work.
2. Continue remaining packages for audit/shared-state parity, invoice save/share and tax/settings, notifications/email/planning, decision-dependent standalone Spa and shared date formatting. Validate P05–P07 UI and legacy-data scenarios when testing is authorized.
3. Finish Step 5 integrations: PDF save/share and tax/settings parity, push/navigation, S3, admin alert email preference/delivery, business configuration, automatic planning and host timers. Owner checklist/standalone decisions are resolved; live configuration is deferred.
4. Add targeted regressions for the listed acceptance gaps and repair/extend live/device/browser scripts. Tests can be written under the user's coding-only instruction, but execution still requires the user's later request.
5. When requested, validate the latest changes/migrations in isolated databases and run component/unit suites, then real provider/device/browser journeys. Complete production infrastructure/checkpoints, load/restore/accessibility/signing/store release work before release.

The report does not claim that passing a unit suite proves live services, or that an unverified deployment is absent. The original audit changed documentation only; the subsequent owner-authorized packages 1–7 changed application code and regression sources, without executing validation.
"""
(OUT/"requirements-audit.md").write_text(report, encoding="utf-8")
data = json.loads((OUT/"requirements-audit.json").read_text(encoding="utf-8"))
data.update({"business_rules": rules, "data_entities": entities, "test_evidence_counts": dict(test_counts)})
(OUT/"requirements-audit.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({"business_rules": len(rules), "entity_bullets": len(entities), "consolidated_findings": len(gaps), "test_evidence_counts": dict(test_counts)}, indent=2))
