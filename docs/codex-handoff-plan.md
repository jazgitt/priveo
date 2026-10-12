# Claude handoff and remaining implementation plan

## Resume checkpoint

Step 4 is implemented and validated on `integration/complete-build` after `a296d3a`. The next implementation milestone is Step 5. No merge to main or deployment has been performed. Pushing this branch does not apply the backend changes or migration `0023` to the hosted API.

- Steps 1–3 are complete and pushed as commit `a296d3a` on `integration/complete-build`; local and remote matched after the push. No merge to main or deployment was performed.
- Step 4 is implemented: operations outcomes/history, explicit next-day retry links, idempotent billing extensions and mobile admin customer/crew/add-on/check-in actions. See its implementation record below.
- Next implementation task is **Step 5: customer presentation and external services**. Re-audit invoice PDF/save/share, video playback, media and notification destinations; inspect existing email/FCM/S3/UPI/timer configuration before connecting adapters. Keep real credentials out of the repository.
- Step 6 follows Step 5: complete device/database journeys, release checks and deployment.
- Standalone Deep Spa payment/fulfilment remains an owner decision (`ADD-15` / `ADM-ADD-12`); preserve the request-only behavior until specified. Do not assume external service credentials or release accounts are missing without inspecting the existing setup.
- Final checks including Step 4: 409 SQLite API tests; 129 affected-module PostgreSQL tests; 68 portal tests; 191 mobile tests, 11 platform/live skips; lint, analysis, web build and generated outputs passed. Migration head is `0023`.

The implementation records below describe the state before the commit; this checkpoint supersedes their statements that the work was uncommitted.

Initially inspected 12 October 2026; updated after implementing Steps 1–4 below. This is a repository-based assessment, not confirmation of the current GitHub PR, CI or deployed environment state.

## Step 4: operations and admin quick actions

- Added the Operations portal and admin APIs: missed-job queue, scheduled work, resolution history, society/date/failure-reason filters, reason/note/evidence, skip-job/skip-remaining-visit actions and next-day-only Interior/Spa retries. Completed jobs cannot be repeated; expired next-day retry dates are rejected. Resolved jobs leave the missed queue and stay in history.
- Original missed jobs, timings, failure notes and proof remain intact. Each retry has a unique `source_job_id` and its own visit; reruns preserve it without creating a duplicate Spa job. Frozen schedules retain existing placements; retries use spare capacity or stay in Needs scheduling. If no period covers the retry date, a one-day draft is created for review/freeze.
- Customer calendar messages use explicit retry links. Exterior coverage refers to the next day's regular Exterior service; Spa does not cover an Exterior failure. Missed continues to alert admins without a customer Missed push. Operations skips follow the customer's notification preference and remove crew cards.
- Reused the manager's idempotent plan extension for Exterior skips. Unreceived future plan payments move with the extension; Received payments remain unchanged. Interior/Spa skips never extend the plan. Spa refund/rebooking remains a manual admin process.
- Mobile quick actions now include operations outcomes, customer search/view with vehicle skip/un-skip/pause/end-pause, crew list/exception creation, read-only add-on requests and monthly check-in results. Existing payment, complaint, feedback, capacity and read-only day/needs-scheduling screens remain; the day screen links to its Operations work.
- Extended the shared audit for operations, scheduling, payment status, subscription status and crew actions; added actor/date filters to the portal audit. Migration `0023` adds decisions/retry links and backfills existing manager skip history. Downgrade refuses to discard recorded operations decisions.

Validated: API Ruff; **409 tests passed on SQLite**; **129 affected-module tests passed on disposable PostgreSQL**, including operations, crew scheduling, customer messages, billing, audit and migration/model parity. The earlier full PostgreSQL run passed 406 tests and exposed two overlong crew audit actions; both failures were corrected and passed in the final rerun. Flutter analysis is clean; **191 mobile tests passed, 11 skipped**. Web lint, **68 portal tests** and the production build passed. There is one migration head (`0023`); OpenAPI matches the live schema, Dart/localization generation is stable, and `git diff --check` passes. Linux goldens, live services, real devices and deployed migrations are later verification milestones. No coverage threshold is claimed.

## Steps 2 and 3 implemented: 12 October 2026

All changes are in the working tree, alongside Step 1, without commits, pushes or deployments.

- Customer administration: searchable customer list, creation without spreadsheet import, details/profile edits, vehicle/parking/catalogue changes, required vehicle photo, optional RC upload/verification, first-payment status, welcome resend, email correction, password reset, individual/all-session revocation, device metadata, notification controls, subscription status and skip/pause actions. Changes record actor/time in the audit.
- Mobile Add vehicle: society and catalogue selection, photo, optional RC document, parking, plan inclusions/list price/badge, conditional interior-care preferences, review and payment. Vehicles can belong to different immutable societies (`VEH-09`); scheduling, customer reads, counts, payments and complaint ownership use the vehicle society with a legacy fallback. Initial onboarding review now presents plan and payment details.
- Plan changes take effect at renewal. The next payment uses the new plan price, and the timer applies the new plan and interior inclusion. First activation anchors the onboarding payment cycle to the actual first-service date while preserving its payment status.
- Scheduling consumes actual `AddonBooking` rows and their finish-by limits, independently of payment. Each Spa booking has a separate visit; completion, cancellation and changes synchronize with its job. Unplaced/unplanned bookings are visible. Frozen date/time changes become reviewable requests; cancellation removes only Spa work. Late assignment preserves existing frozen placements.
- Configured service slots, daily/weekly/monthly periods and week starts now affect scheduling. Portal actions provide atomic job swaps, preview/apply suggestions with stale-preview rejection, and cutoff-request resolution. Add-on management includes customer requests, assignment/payment details, filters, pending changes and cancellation.
- Migration `0022` follows `0021`. It backfills vehicle societies and separates legacy Spa jobs into independent visits while preserving job IDs and proof references. Downgrade refuses to collapse duplicate service visits rather than discard data. OpenAPI, Dart API and localization outputs are regenerated.

Validated: API Ruff; **402 API tests passed on SQLite**; **147 affected-module regressions passed on disposable PostgreSQL**, including the legacy-data migration. The earlier complete PostgreSQL run passed 398 tests and exposed one incorrect calendar fixture expectation; that test and all affected modules passed on the final rerun. Migration upgrade/model parity/downgrade and one Alembic head (`0022`) were checked. Flutter analysis is clean; **185 mobile tests passed, 11 skipped**. Web lint, **65 portal tests** and the production build passed. The generated OpenAPI matches the live schema; repeated Dart/localization generation is stable, and `git diff --check` passes.

Standalone Deep Spa remains request-only: its payment/fulfilment behavior still requires the owner decision `ADD-15` / `ADM-ADD-12`. Real email/push/storage integration, Linux goldens, real devices and deployed migrations remain Step 5/6 validation work. No coverage threshold is claimed.

## Step 1 implemented: 12 October 2026

The saved `slice/signin-email` and `slice/crew-manager` changes are applied to the working tree of `integration/complete-build`. No commits, pushes, PR merges or deployments were performed. Branch ancestry is unchanged until this work is committed.

- Recovered Resend delivery, welcome-email helper, sign-in welcome/validation/support links and admin customer session revocation. The welcome helper will be called by customer creation in Step 2; it does not introduce a customer-create flow here.
- Recovered manager attendance and working-hours screens/endpoints, reassignment availability checks and idempotent external-cleaning plan extensions. Migration `0021` follows `0019`, with one Alembic head; models and routes are registered.
- Made account email-change delivery fail closed without a production provider and roll back when sending fails, retaining an earlier pending code. Added its own email template and regression tests. Tests suppress real provider credentials inherited from local configuration.
- Fixed payment receipt timestamps to use the injected billing clock in UTC, preserving the fixed-date billing regression test.
- Merged the auth/manager ARB fragments and regenerated localization, OpenAPI and Dart API output. Fixed generated method-name collisions among supported endpoints without renaming existing auth methods for endpoints the generator omits.
- Updated sign-out and device integration tests for the welcome screen. Added an isolated PostgreSQL test launcher and refreshed the repository/coverage documentation.

Validated: API Ruff; **389 API tests on SQLite and 389 on disposable PostgreSQL**; migration upgrade/model-column parity/downgrade; one migration head (`0021`); Flutter analysis; **183 mobile tests passed, 11 skipped**; web lint, **61 web tests**, production build; contract matches the live schema. The generated outputs are current.

Remaining verification limits: the 11 mobile skips cover Linux-only goldens and live-API tests. Linux golden comparisons/regeneration, emulator/real-device testing, actual Resend delivery and hosted CI/deployment were not run. Follow `mobile-goldens.yml` when validating screenshots on Linux. Feature tracker stages were not promoted to “Unit Tested >95%” because this work did not measure coverage at that threshold.

## Where Claude stopped

- Current checkout: `integration/complete-build`, commit `a2461df`, merge of PR #50 (customer account), dated 11 October at 20:37 IST. Local `main` and its cached remote reference are at `e3f91b7`; the integration branch contains 59 additional commits.
- The root checkout and all registered Claude worktrees had no uncommitted changes when inspected.
- Two slice branches contain commits not in integration: `slice/signin-email` (latest `48a93b7`, 20:53 IST) and `slice/crew-manager` (latest `a7a7382`, 20:56 IST). These are saved implementations to review and integrate, not work to recreate.
- The email slice adds Resend, code delivery, welcome email helpers, support contact and sign-in entry screens. The manager slice adds attendance, hours, reassignment checks and plan extensions. Neither is verified by this assessment.
- Several commits explicitly say “WIP: stopped by the session limit, not verified.” Some received later follow-up commits, so the WIP label alone does not describe the latest branch state.
- README, CLAUDE.md, build-plan.md, overnight-build-report.md and the three coverage audits lag behind the implementation. Treat the requirement documents as the target, but recheck each audit verdict against current code before using its counts.

## What already exists on integration

FastAPI identity, customer review/account, crew directory connected to scheduling, OR-Tools scheduling, job execution and proof uploads/reads, customer home/calendar/history, skips and pauses, manual UPI payments, support and feedback, notification events/preferences/inboxes and protected cron endpoints.

The React portal has sign-in and cookie sessions, dashboard, alerts, crew, schedules, capacity, payments, subscriptions, complaints, feedback, reference data, settings and a directory audit page. Flutter includes the corresponding customer and crew flows and a subset of admin quick actions. Existing screens still need requirement-level verification.

## Initial inspection results (superseded by the Step 1 results above)

- API Ruff: passed.
- Web lint: passed.
- Web tests: 61 passed across 9 files.
- Web production build: passed.
- OpenAPI comparison: stale committed contract; the code exposes 185 paths versus 179 committed paths.
- API tests in the sandbox: 298 passed, 1 failed, 68 setup errors. The failure is `tests/billing/test_billing.py::test_a_payment_runs_from_due_to_received`, which expects `received_on=2026-10-11` but receives `2026-10-12`. Diagnose clock injection before changing the expectation.
- API setup errors included Windows temporary-directory/cache permission errors. A scoped customer-account rerun outside the sandbox passed all 8 tests; the whole suite still needs a clean-environment rerun before declaring the baseline green.
- Flutter analyze/test attempt did not complete; no mobile pass is claimed. PostgreSQL tests, real devices, migrations on deployed databases and release/deployment checks were not performed.

## Implementation order

### 1. Recover the saved work and establish a green baseline

**Implemented in the working tree.** Results and platform limits are recorded above.

Review the latest email and manager branch diffs; integrate email first, then manager work. Resolve email adapter compatibility with the new account email-change flow. Chain the manager migration into the current Alembic head and register its models/routes. Merge localization fragments, regenerate the contract, Dart client and localization output, and check route wiring.

Fix the payment clock failure and investigate the remaining API failures in a working temporary directory. Run API lint/tests on SQLite and disposable PostgreSQL, migration/model parity, one Alembic head, generated artifact checks, Flutter analyze/tests and web lint/tests/build. Update the handoff/coverage status using the results. Completion: one integrated branch with passing required checks and no stale generated outputs.

### 2. Build customer administration and additional vehicles

**Implemented in the working tree.** See the Steps 2/3 record above. The following paragraphs preserve the original scope.

The `/customers` portal route is a placeholder. Implement admin customer search/list/detail and onboarding creation, vehicles/subscriptions, welcome resend, email correction, password reset, session revocation and notification controls. Reuse the existing directory and upload modules. Include first-payment status, photo and RC handling, audit events and admin skip/pause controls.

Add the customer Add vehicle flow using the existing society, catalogue and plan reads, plus photo, parking, preferences, review and payment. Finish plan inclusions/list-price and first-payment presentation. Review the requirement for vehicles in different societies before changing the current customer-level society model; update all scheduling/crew/support ownership queries together if that migration is required.

Completion: admin creates a customer without a spreadsheet import; the customer signs in, reviews details, pays and adds a second vehicle through the app.

### 3. Correct Deep Spa and scheduling integration

**Implemented in the working tree.** See the Steps 2/3 record above. The following paragraphs preserve the original scope.

Confirmed mismatch: `app/scheduling/service.py::build_demand` reads legacy `AddonRequest`, while `app/addons/service.py` writes `AddonBooking` with `finish_by`. Jobs currently reference the legacy table. Migrate the association and make active bookings reach scheduling with their actual finish-by time. Synchronize request/job statuses and cancellation/date changes; show unplaced bookings in Needs scheduling.

Make the scheduler honor configured service working slots and period/week-start settings; weekday crew hours and customer skips/pauses are already implemented and should be retained. Finish swap/suggestions, cutoff-request handling and assignment/removal after freeze, with alerts and crew notifications. Add portal add-on request management; catalogue editing already exists under Reference data.

Completion: request Deep Spa in the app, schedule it, display it to crew, complete it and display its proof/status to the customer. Regression scenarios cover skip/pause, cancellation, crew absence, reactivation and post-freeze changes.

### 4. Complete operations and admin quick actions

The `/operations` portal route is a placeholder. Build the Missed-job queue and outcomes (reschedule or skip), operations skip reasons, customer “Rescheduled”/“Covered” messages, notification and external-cleaning subscription/payment extensions. Reuse the manager slice's extension logic and prevent duplicate extensions. Extend the audit beyond directory changes to customer, crew, payment, subscription, schedule and operations actions; verify reporting filters and histories.

Finish the remaining mobile admin actions: customer search/view and changes, operations outcomes, crew exceptions and add-on requests. Existing payment, complaint and read-only schedule actions should be verified rather than rebuilt.

Completion: operations can resolve a missed service with the correct audit, customer message and billing consequences.

### 5. Finish customer presentation and connect external services

Re-audit the remaining customer requirements: genuine invoice PDF/save/share, in-app video playback, notification tap destinations, media display and plan/payment presentation. Current invoice actions copy/email text; they do not produce a PDF.

Connect the recovered Resend adapter and verified sending domain. Replace `LoggingPushSender` and `NoPushTokenProvider` with FCM, permissions, token refresh and tap routing. Replace `LocalObjectStore` with durable S3 signed uploads/downloads and verify offline retry. Supply real UPI/QR, invoice seller/GST details and support contacts. Verify cron authorization, repeat-run safety and deployment activation; cron routes/configuration already exist.

Completion: real email arrives, real pushes route correctly, media survives deploys and timers update scheduling/billing/support as specified.

### 6. Harden and release

Run complete user journeys on Android and PostgreSQL: admin onboarding, first sign-in, payment confirmation, schedule freeze, crew proof upload offline/online, customer proof/rating, skips/pauses, complaint resolution and renewal/inactivation. Check role/society/vehicle authorization, sessions, signed media expiry, CSRF and upload validation. Validate migrations against a disposable copy of the existing schema, data preservation and deployment recovery.

Refresh operational docs and feature status. Review and merge the integrated work only after required checks; deployment workflows run from main. Validate the actual dev environment, then configure AWS production and Play internal testing. Finish iOS signing/TestFlight once its accounts are available. Verify store assets, privacy/terms links and release credentials.

## Owner inputs that remain relevant

- Standalone Deep Spa behavior/payment: `ADD-15` / `ADM-ADD-12` is still an owner decision. The existing request-only implementation does not settle it.
- Starting internal-cleaning and Deep Spa checklists, plan/catalogue content and final business contact/invoice/UPI details.
- Access/configuration for Resend, Firebase, AWS/S3 and Play; Apple accounts for the later iOS release. Inspect existing setup before assuming any account is missing.

These inputs can be collected while implementation and regression work proceeds. Steps 1–3 are pushed and Step 4 is implemented locally; customer presentation and external services (Step 5) are next.
