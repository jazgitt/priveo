# Standalone Spa, samples, GST and optional planning: prepared scenarios

Owner decisions are recorded in [the requirements](../reqs/owner-decisions-2026-10-13.md). Code and regression sources are written; no tests, builds or migrations executed. Migrations 0024-0028 remain unapplied. Provider credentials, mock business values and host execution are deferred to later integration.

## Standalone Spa (P12)

Create a customer in the portal with a confirmed vehicle photo, immutable society/catalogue and valid parking. Uncheck Create a subscription. Review must say no plan/payment; there must be no subscription row or plan payment. Welcome/verification/onboarding use the existing customer flow without public signup. Home offers Deep Spa for a no-subscription vehicle, with no subscription/skip action. Admin Add-ons offers these vehicles too, alongside Active subscriber vehicles.

Book a date/finish-by using the catalogue's Spa price. Confirm opens the amount-bearing UPI payment. A retry with the same key must return one booking/payment. Missing/foreign vehicles, a subscribed vehicle on the standalone route, invalid finish-by and a booking after the configured cutoff must fail without a payment. Scheduling must work while its Add-on payment is Due, create a separate 120-minute Spa visit, and expose crew assignment, outcome and proof/history to the owning customer.

Exercise change/cancel before and at the deadline, frozen-change review and cancellation of Due/Initiated/Received payments. Unpaid cancellation voids the payment; received refund remains manual outside the app. Completed and Missed Spa outcomes use the existing subscriber rules. Existing unlinked legacy requests are not retroactively assigned a price, payment, completion or proof. Date/time inputs and device/provider journeys remain unexecuted.

Sources: API test_customer_administration.py, addons/test_standalone_rules.py, addons/test_addons.py, scheduling/test_addon_lifecycle.py; portal customers.test.tsx; mobile changes_money_test.dart. Existing scheduling/visit proof/outcome regressions are related evidence, not complete measured acceptance coverage.

## Sample checklist and history

Seed a new database: each service has five active steps. Internal and Spa samples are editable/reorderable/deactivatable in the portal and read-only on admin mobile. Complete a job, edit its catalogue and reopen the issued visit: snapshot labels/order/ticks remain unchanged. Migration 0028 changes only exact, untouched old sample sets, after 0025 snapshots existing jobs; admin-edited catalogue entries are preserved. Old issued work and historical feedback/rating/check-in names must not be rewritten. Rename a category and verify earlier results keep the original name and reporting bucket.

Sources: directory/test_directory.py, visits/test_checklist_snapshots.py, support/test_support.py, mobile admin_checklists_test.dart. Migration and device execution pending.

## GST snapshot and mock configuration

For a Received payment, issue an invoice at 18% GST included in the total. INR 118 must produce INR 100 taxable plus INR 18 GST: mock CGST_SGST mode gives INR 9 + INR 9; IGST mode gives INR 18. For uneven paise amounts, components must sum exactly to total. Changing environment rate/mode/supplier after issuance must not change the issued snapshot. Old invoices without tax snapshots explicitly retain an unrecorded breakdown.

PDF and native invoice summary show the breakdown. Portal seller fields are read-only; API writes are rejected. Environment/seed configuration supplies seller identity; explicit seeding can replace mock supplier values without rewriting real stored settings or issued snapshots. MONEY_GST_CONFIGURATION_MOCK=true marks mock tax configuration: development preview remains possible, while PDF delivery is blocked outside development. Replace supplier/GSTIN/mode values offline and set the flag false when real configuration is ready.

Sources: billing/test_gst_snapshot.py, billing/test_invoice_pdf.py and directory/test_directory.py. No invoice was issued against a live database, no PDF validation or legal/provider integration ran.

## Automatic planning

Initially disabled. Only admin can change the switch/time. Enabling without a valid HH:MM IST time fails atomically. Save a time and a configured Daily/Weekly/Monthly period/week start. The protected automatic-planning cron checks every minute, starts at or after the selected time and creates the next period as a Draft for active societies. It does not freeze the result or rerun existing manual/frozen schedules. An already-created automatic target is not duplicated on repeated invocations.

Inject a planning failure: keep the owned draft/run ledger, alert admin and retry that future target after five minutes. Successful retry uses the same draft; a worker interrupted mid-run can recover after its 30-minute lease. A target that has already started requires manual review rather than inventing retrospective work. Exercise month/year/leap/week boundaries, disabled/inactive societies, overlapping schedules, unavailable crew and configuration changes. Schedule the job before the desired freeze time; existing freeze cron behavior is retained. Errors remain in the admin inbox; email follows preferences/configuration and real phone push still awaits P10.

Host calls /v1/internal/cron/automatic-planning with CRON_SECRET. A minute-capable host plan is required. The configuration file is written but no host deployment occurred. Cron authorization is shared with the existing protected jobs.

Sources: scheduling/test_automatic_planning.py and portal AutomaticPlanningSettings.test.tsx. PostgreSQL concurrent-worker locking, migration parity, host cadence and device/live delivery are unexecuted.

## Environment and policies

Missing mock keys were added to .env.example, .env and .env.local without replacing existing values. Local files remain ignored by Git. Firebase/APNs/S3 placeholders document later integration inputs and do not select a real adapter. Existing Resend/UPI/support keys remain authoritative. Legal links now read environment-configured public API values; pre-login support shares the directory settings with signed-in support.

Billing cycle, deadlines and unfreeze settings remain configurable as authorized; original values are defaults. Invoice supplier identity remains seeded/read-only. Production S3/FCM, PDF save/share, inline playback, real-time cross-client transport and date-format parity remain separate pending coding targets.
