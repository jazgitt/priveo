# Claude handoff and remaining implementation plan

## Resume checkpoint

**Latest test-data work:** [39-family scenario catalogue and manual/E2E plan](testing/test-data-plan.md), dedicated SQLite seed with full fresh-start and selected-scenario refresh, local API launcher, manifest-based API smoke suite, and installed `$priveo-test-data` skill. Customer cases C01-C16 retain the owner's list; C17-C29/R01-R06/A01-A04 add plan/onboarding/history/legacy/multi-society/inbox and Crew/Admin variations. One Admin login is preserved. The sample database and account sheet are ignored local files; existing application databases are untouched. Fixture integrity and API compatibility are tested on disposable databases; phone/browser UI E2E, sample proof media and additional action/boundary cases are planned, not completed. See the test-data plan for exact commands and reset scope.

The [79-row plan](coverage/gap-implementation-plan.md) has P01-P07, P08/P11 and owner-approved P12/GST/sample/optional-planning sources coded. Current audit: 392 Implemented source paths, 34 Partial and 0 Open; 45 original code gaps addressed and the three Open decisions resolved. See [owner decisions](reqs/owner-decisions-2026-10-13.md). Implementation is committed/pushed as `2c3ba73`; tests and coverage were subsequently authorized and executed. Migrations 0024-0028 are still unapplied to application databases. Real-time cross-client transport, PDF save/share/inline proof, P10 push, S3/date/security/release work remain pending; no live integration/deployment occurred.

Latest validation (13 Oct 2026): **494 backend tests passed** on SQLite; **1,433 mobile tests passed, 11 skipped**; **99 portal tests passed**; Flutter analysis and the portal TypeScript/production build passed. Fresh line coverage: Customer 90.22%, Crew 90.09%, Admin Mobile 91.17%, Admin Web 90.52%, shared backend 92.89%, shared mobile 92.85%. The test-data suite adds 13 passing targeted tests. See [the report](coverage/unit-test-coverage.md) for source denominators, lower branch/function metrics and limits. `tools/coverage/run.ps1` and `tools/coverage/report.py` enforce 90% per area, including unimported production source; generated mobile code is also measured separately. Coverage and test-data work are committed in `ccf0daa`. No real device, live integration or production migration/deployment validation occurred.

Coverage work fixed the missing Home message import, preserved backend messages in direct Dio money-flow failures and added an injectable SQLite factory for schema/upgrade regression tests. It corrected unrun test fixtures/timer lifecycle issues and added API adapters, OpenAPI wire contracts, localization, validation/recovery, account navigation, admin actions, native capture and account-safe queue coverage.

The package notes below describe the earlier implementation checkpoint; references to tests being written/unrun are historical. The measured report above is the current execution status.

Package implementation record:

- P01: service-level rating existence/ownership/Completed checks and canonical UUID updates. Tests now use a real owned Completed visit instead of a fake visit ID; new authorization/state/role tests are written.
- P02: every ORM-created job snapshots checklist keys/labels/order, including draft/operations retry paths. Issued unfinished work keeps that definition; newly created jobs use new catalogue items. Crew validation/counts and customer/history reads use snapshots. Migration `0025` follows `0024`; legacy backfill is tagged `legacy=true` and cannot restore labels already overwritten before the migration. Downgrade refuses to discard snapshots. Migration and backfill/parity regressions are unrun.
- P03: activation after reactivation requires a first-service date and creates one new Due cycle, rejects an existing cycle before mutation, preserves receipts, excludes historical pause/debt effects from the new billing epoch, and protects the future first-cycle payment from cron reanchoring. Pause/cancel/early-end shifts affected unpaid payment dates in the same transaction, including manual plan records, preserves Received/voided/add-on payments, updates pending plan dates and guards collisions. Portal omits an old interior day for an exterior-only pending plan.
- P04: SQLite v2 adds owner partitioning; unidentified legacy queue rows are quarantined, not assigned to the first login. New files are stored in owner folders. Queues and dedicated upload clients are disposed on auth changes, stop between stages, and cannot refresh/retry under a different login. Late auth-refresh responses cannot overwrite a newer login. Photos/videos use strict below-10/25-MB checks at capture/request/local PUT/confirmation, while RC documents keep the inclusive 5-MB rule.
- P05: seven-step single-vehicle review (four vehicle steps repeated for each car), validated resumable drafts, uppercase registration paste, payable-today totals, amount-bearing UPI QR and submitted vehicle/preferences summary. Migration `0026` stores draft position without confirming onboarding or creating payments.
- P06: Home vehicle catalogue labels and Rate today action through Service Details; completed calendar timing/check counts; Home check-in refresh; Verified RC and configured parking; one app-level customer feedback tab; bundled Markdown FAQ.
- P07: own-session crew device metadata; stable customer/payment paging with server-side society filtering; complaint vehicle/photos and owned linked visit proof; separate imported history preserving unknown dates/completion/proof and unmatched vehicles. Exact-full last pages can lead to an empty next page.
- P08: atomic admin/customer logout-all audit, explicit silent plan/default preferences versus notified skip policy; foreground 30-second reads plus focus/resume refresh. Real-time propagation remains pending; native manual history refresh returns to its first page.
- P11: own-admin persisted email address/switch with portal control; durable per-recipient Resend queue, stable idempotency keys, backoff/max-five attempts; opt-out/address changes stop old pending messages. Inbox and push are independent of email failure. Complaint escalation marker/alert/outbox commit together under row locks, with five-minute configured cron. Migration `0027` follows `0026`. Missing key leaves emails pending; actual delivery, host cadence and PostgreSQL locking are unverified.
- P12: admin portal/API creates no-subscription customer/vehicle without a plan payment; mobile and admin use subscriber Spa price/date/finish-by/UPI/cutoff/cancel/scheduling/outcome/proof rules. New bookings require an owned no-subscription vehicle. No public signup or synthetic subscription. Legacy unlinked requests retain unknown data. Regression sources updated/written, unrun.
- Owner-approved additions: five-step samples plus read-only admin mobile checklist route; 18% inclusive paise GST snapshots in PDF/native invoice, seller fields read-only/seeded, mock tax/supplier preview blocked outside dev; immutable historical category names; configurable cycle/deadline/unfreeze defaults. First onboarding cycle respects configured days.
- Optional planning: default-disabled, admin switch/required IST time, minute cron, next configured Daily/Weekly/Monthly draft per active society, preserve existing/frozen schedules, durable target ledger with 30-minute recovery lease and five-minute error retries/admin alerts. No host deployment; use minute-capable host and schedule before desired freeze cutoff. Migration 0028 follows 0027 and updates only untouched old samples.
- Missing environment keys added to .env.example/.env/.env.local without replacing existing values; local files remain Git-ignored. FCM/APNs/S3 placeholders do not select live adapters. Legal links read public environment-configured endpoint; pre-login support shares directory values.
- Unit/component and API scenario sources are written. [Prepared functional scenarios](coverage/packages-1-4-functional-scenarios.md) document native restart/SQLite upgrade/HEIC and database journeys still requiring execution. **No tests, lint, analysis, builds, migration execution, commits, pushes or deployment were performed for these packages.** Migrations `0024` through `0028` are unapplied. [Standalone/planning/GST scenarios](coverage/standalone-planning-gst-functional-scenarios.md) are prepared. [P08/P11 scenarios](coverage/packages-8-11-functional-scenarios.md) are prepared. OpenAPI/Dart generation and QR dependency resolution completed as coding operations; no tests or app builds ran. [P05-P07 functional scenarios](coverage/packages-5-7-functional-scenarios.md) are prepared for later execution. Earlier historical passes do not validate the latest code.

**Current remaining-work inventory:** [full row-by-row requirements audit](coverage/requirements-audit.md), dated 13 Oct 2026. It replaces the previous coverage summaries and identifies additional billing, ownership, historical-data and UI gaps beyond the original Step 5 list. The three coverage matrices now represent all 426 source rows; business rules and entity bullets have separate tables. Code/test presence is distinguished from runtime validation. No tests were executed for the audit. Use its consolidated findings and implementation ordering for future work; the historical implementation records below do not prove complete requirement coverage.

Steps 1–4 are committed and pushed on `integration/complete-build`, most recently as `d5aaad3`. Step 5.1 and 5.3 code and regression tests are now implemented locally, uncommitted. At the owner's request, no tests, coverage measurement, lint, analysis, builds or migration checks have been run for these changes. No merge to main or deployment has been performed.

- Steps 1–3 are complete and pushed as commit `a296d3a` on `integration/complete-build`; local and remote matched after the push. No merge to main or deployment was performed.
- Step 4 is implemented: operations outcomes/history, explicit next-day retry links, idempotent billing extensions and mobile admin customer/crew/add-on/check-in actions. See its implementation record below.
- Original 5.1/5.3 are coded and unvalidated. The later owner-approved automatic planner (5.8) is now coded/default-disabled; host execution remains pending. PDF save/share, push/navigation/S3/live configuration and other release work remain pending as listed in the current audit.
- Step 6 follows Step 5: complete device/database journeys, release checks and deployment.
- Standalone Deep Spa payment/fulfilment remains an owner decision (`ADD-15` / `ADM-ADD-12`); preserve the request-only behavior until specified. Do not assume external service credentials or release accounts are missing without inspecting the existing setup.
- Historical checks through Step 4: 409 SQLite API tests; 129 affected-module PostgreSQL tests; 68 portal tests; 191 mobile tests, 11 platform/live skips; lint, analysis, web build and generated outputs passed. These results do not cover Step 5.1/5.3. New migration `0024` is written but has not been applied or checked.

The implementation records below describe the state before the commit; this checkpoint supersedes their statements that the work was uncommitted.

Initially inspected 12 October 2026; updated 13 October after coding Step 5.1/5.3. This is a repository-based assessment, not confirmation of the current GitHub PR, CI or deployed environment state.

## Step 5.1 and 5.3: code written; testing deferred

- **5.1 Invoice PDF:** Added authenticated customer/admin PDF endpoints for existing issued invoices, ownership/role checks, inline/no-store responses, escaped and wrapping text with an embedded licensed font, and Flutter PDF viewing plus a portal PDF link. New invoices snapshot supplier details via migration `0024`; legacy PDFs label current-settings fallback. Incomplete supplier/GST settings allow a labelled development preview and block PDF delivery outside development. No business values or tax breakdown are invented. Native PDF save/share remains **5.2 pending**.
- **5.3 Proof video/media:** Service Details opens an in-app video player with loading, timeout, failure/retry, play/pause/replay, seeking, background pause and disposal. Retry refreshes the owned visit's signed URL and finds the same proof ID even when items reorder; missing proof displays an error. Existing photo display is retained; photo rendering and expiry behavior still require later validation. Video requests do not receive the API bearer token.
- Added backend PDF regression tests, Flutter PDF repository/viewer and video lifecycle/retry tests, and portal PDF-link assertions. Tests are written, **not executed**; no coverage percentage or passing result is claimed. API contract, Dart API and localization sources were regenerated, and Flutter dependencies resolved as coding operations.
- Before testing when authorized: install the added API runtime/dev dependencies (`reportlab`, `pypdf`), then use disposable databases for migration `0024` and backend regressions. Native PDF/video device checks belong to later validation. Do not apply this migration to a hosted database as part of coding.
- **Pending:** 5.2 save/share; 5.4 notification destinations; 5.5 FCM; 5.6 S3; 5.7 live email/business settings; 5.8 automatic next-period planning and host timers. The automatic planning job is now coded/default-disabled; its host execution and migration validation remain pending. Step 6 remains pending.

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

Invoice PDF viewing and in-app proof video playback are coded in 5.1/5.3, with validation deferred. PDF save/share (5.2), notification destinations, durable media and external provider setup remain pending. Existing text copy/email invoice actions remain until 5.2.

Connect the recovered Resend adapter and verified sending domain. Replace `LoggingPushSender` and `NoPushTokenProvider` with FCM, permissions, token refresh and tap routing. Replace `LocalObjectStore` with durable S3 signed uploads/downloads and verify offline retry. Supply real UPI/QR, invoice seller/GST details and support contacts. Verify cron authorization, repeat-run safety and deployment activation; cron routes/configuration already exist.

Completion: real email arrives, real pushes route correctly, media survives deploys and timers update scheduling/billing/support as specified.

#### Step 5 delivery plan: small, independently testable tasks

Current owner instruction: continue the authorized packages and owner decisions, writing code and regression sources only; do not execute tests/builds/migrations until asked. Original 5.1/5.3 and the later optional planning job are coded locally, with validation pending; other integration/release work remains in the audit. The sizes below describe relative implementation effort, not quota percentages. Inspect existing code/configuration before changing adapters or requesting account access. Step 4 is pushed as `d5aaad3`; the new PDF snapshot migration `0024` is not applied or deployed.

| Task | Scope | Size | Completion check / dependency |
|---|---|---|---|
| 5.1 Invoice PDF | Generate a real PDF from the existing admin-generated invoice record; preserve its number, dates and amounts, enforce ownership/roles, and open it from billing history. Validate required seller/GST settings without guessing business details. | Medium | A customer opens their Received-payment invoice as a readable PDF; another customer cannot access it. Final seller/GST details are needed for live use. |
| 5.2 Save/share invoice | Save the PDF to the device and use native sharing; replace the current text-only invoice actions. | Small–medium | On Android, save/open the file and share the actual PDF. Depends on 5.1; iOS device validation remains a later release check. |
| 5.3 Proof video/media | Play crew proof videos inside Service Details with loading/error/retry controls; verify photo display and signed-media expiry handling. | Medium | Play/pause an uploaded video on the phone, and recover visibly from a failed or expired URL. Can start with the existing media store. |
| 5.4 Notification destinations | Re-audit and finish customer/crew/admin inbox links and notification destinations, retaining role checks and read state. | Small–medium | Inbox events open the correct visit, payment, complaint, check-in, crew job or operations screen. Real push taps are verified after 5.5. |
| 5.5 Real FCM push | Replace the placeholder token provider and logging sender; add permission handling, token refresh, logout/account-switch handling and foreground/background/tap behavior. Retain preferences and deduplication. | Large | A real device receives a permitted event and opens its destination; disabled events do not arrive. Requires Firebase configuration/access, after inspecting current setup. Depends on 5.4 for destinations. |
| 5.6 Durable media | Add an S3 store using the existing signed-upload/download interface, retain ownership/file-size checks, and verify upload retries and persistence across backend restarts. | Large | Vehicle photo, RC and crew proof upload/read correctly and survive a redeploy; interrupted uploads retry without duplicate confirmation. Requires AWS/S3 configuration/access. Do not move/delete existing media without a reviewed migration plan. |
| 5.7 Live email/business settings | Verify the existing Resend adapter/domain and actual verification/welcome/reset delivery; supply and verify UPI/QR, invoice seller/GST and support settings. | Small–medium, configuration dependent | Real emails arrive; payment instructions and invoice/support details show supplied business values. Secrets stay outside the repository. Uses owner details and available provider setup. |
| 5.8 Scheduled jobs | Add the missing automatic next-day/next-period draft-planning job, respecting Daily/Weekly/Monthly and week-start settings without overwriting frozen/manual work. Vercel cron entries and protected endpoints already exist; verify deployment activation and `CRON_SECRET`, then verify repeat-run safety, automatic freeze, renewal reminders, due/overdue/inactive transitions and monthly check-ins on controlled test data. Existing `freeze-due` only freezes drafts already created; it does not generate the next period. | Medium–large; planning code plus deployment verification | Automatic planning creates the upcoming draft once; existing work survives repeat runs. Authorized timers trigger expected outcomes once; unauthorized requests fail. Requires a current test backend and configured deployment secret. |

Recommended order: 5.1 → 5.2 → 5.3 → 5.4, then 5.5/5.6/5.7 according to available configuration, then 5.8. Provider setup can be collected while the first four tasks are built. Standalone Deep Spa payment remains outside this plan until the owner decides it. Full cross-feature/device/offline and release validation belongs to Step 6.

### 6. Harden and release

Run complete user journeys on Android and PostgreSQL: admin onboarding, first sign-in, payment confirmation, schedule freeze, crew proof upload offline/online, customer proof/rating, skips/pauses, complaint resolution and renewal/inactivation. Check role/society/vehicle authorization, sessions, signed media expiry, CSRF and upload validation. Validate migrations against a disposable copy of the existing schema, data preservation and deployment recovery.

Refresh operational docs and feature status. Review and merge the integrated work only after required checks; deployment workflows run from main. Validate the actual dev environment, then configure AWS production and Play internal testing. Finish iOS signing/TestFlight once its accounts are available. Verify store assets, privacy/terms links and release credentials.

## Owner inputs that remain relevant

- Standalone Deep Spa behavior/payment: `ADD-15` / `ADM-ADD-12` is still an owner decision. The existing request-only implementation does not settle it.
- Starting internal-cleaning and Deep Spa checklists, plan/catalogue content and final business contact/invoice/UPI details.
- Access/configuration for Resend, Firebase, AWS/S3 and Play; Apple accounts for the later iOS release. Inspect existing setup before assuming any account is missing.

Steps 1–4 are pushed. Step 5.1/5.3 are coded locally, with tests written but execution deferred. Other Step 5 tasks and Step 6 remain pending.
