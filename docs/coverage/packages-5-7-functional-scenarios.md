# Packages 5–7: prepared functional scenarios

Code and regression sources are written; **no tests, app builds or migrations executed**. Migration 0026 follows unapplied 0024/0025. The API and mobile client must use the updated contract before validating these journeys. Dependency resolution and API/client generation were coding operations, not passing validation results.

## P05 — First-sign-in review and payment

Use an admin-created customer with two vehicles, one plan with interior care and one without. Verify personal/society steps followed by vehicle, parking, plan and preferences for each vehicle, then final review (seven steps for one vehicle). Admin-selected society, catalogue and plan remain read-only. Plan price/list price/badge/inclusions appear before preferences. Vehicle photo is required; configured basements and conditional interior care must match each vehicle.

Edit names/mobile and parking/preferences, press Continue, close/reopen the app and verify the saved values and position. Back retains edits. A failed save must keep the current step and show an error. Draft saves must not confirm onboarding, create a payment or permit Home to open. Attempts to submit read-only fields, other customers' vehicles or invalid positions must fail without partial writes. Only final confirmation opens Home. Already-confirmed reviews reject further draft edits.

Review shows each payment status, computed payable-today total and GST-inclusive wording. Received/Initiated payments are excluded from that total. Due/Over due confirmation opens the first pending payment; already submitted/received first payments go to Home. The displayed QR must encode the same amount and payee as the backend UPI URI. After “I've paid”, show Initiated, vehicle, service cutoff and applicable interior day. Add Vehicle must force pasted registration text to uppercase.

Sources: test_customer_home.py; billing/test_gap_billing.py; mobile onboarding_flow_test.dart, add_vehicle_test.dart and changes_money_test.dart. QR scan, restart and actual UPI transfer remain manual/device validation. Do not use development placeholder payment details for a real transfer.

## P06 — Customer screens and navigation

Check Home make/model/variant and the named Rate today's clean action. It opens the selected vehicle's completed Service Details; loading/error/no-completed-work paths must be clear. The completion banner's rating action uses the same destination. Completed calendar cards show finish time and checked/total counts.

Submit a due monthly check-in and return Home: its card disappears without restarting the app. Verify RC Uploaded/Verified/Not uploaded rendering, then edit parking in a society whose basement list differs from B1–B4. The form must offer the configured choices and preserve backend validation.

Navigate Home, Account, calendar, FAQ and pushed customer detail/forms. Exactly one draggable feedback tab remains available after onboarding; it is absent before confirmation and for crew/admin. Tapping it from a detail route opens the feedback sheet using the root navigator.

FAQ comes from bundled assets/content/faq.md and works without a FAQ API call. Its late-payment answer requires Priveo/admin reactivation. Sources: screen_parity_test.dart, customer_test.dart, support_test.dart, and backend customer/calendar assertions. Native navigation/layout and all-screen text scaling are unexecuted.

## P07 — Admin lists, sessions, complaints and imported history

Create more than 200 test customers and more than 100 payments. Page through all results, including identical sort names/dates, with no repeated/missing IDs. Search/filter changes reset the page; payment society filtering applies at the API before paging. At an exact full last page the next page may be empty, with Previous available; total-count reporting is not added.

Sign in as crew on a phone, register metadata and view it in admin sessions: device/platform/app version must correspond to that session. Customer requests to the crew endpoint must be rejected. Empty metadata on older sessions displays Unknown values without inventing a device identity.

Raise a complaint linked to a visit and attach photos. Admin list/detail displays vehicle information and actual signed photos. Linked visit view displays checklist, crew and proof via the owned customer read projection; non-admin access is rejected, and failed reads can be retried. A complaint with no visit honestly shows no vehicle linkage. Real signed URL expiry/playback checks are still pending.

Import dated and undated standalone Spa records, with matched and unmatched vehicles. Customer service history and admin customer details show the imported records once, retain notes/payment information and leave completion/proof unknown. No artificial completed visit/subscription/payment is created. Foreign-customer records remain invisible. Imported records are explicitly shown as a separate all-dates section; normal visit history retains its month navigation. Repeat imports preserve existing source-record IDs.

Sources: test_gap_admin_reads.py; crew/test_crew.py; support/test_support.py; existing import idempotency tests; portal customers.test.tsx, crew.test.tsx, support.test.tsx and PaymentsPage.test.tsx. Live cookie/browser/device/provider journeys remain unexecuted.
