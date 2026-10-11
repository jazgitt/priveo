# Customer requirements: coverage audit

Audit date: 11-Oct-26. Branch `audit/customer`, from `integration/complete-build` at `e3f91b7`.

Scope: every ID row in `docs/reqs/customer-app-functional-requirements.md` (v0.10), checked against the code in `apps/mobile/lib`, `apps/mobile/test`, `services/api/app` and `services/api/tests`. `docs/feature-status.json` and `docs/overnight-build-report.md` were not used as evidence.

## How to read this

Verdicts:

- **Built**: the behaviour is present end to end (API and app, where both are involved).
- **Partial**: some of it is present. The "Missing / notes" column says exactly what is not.
- **Not built**: nothing usable exists for it.

A requirement whose API exists but that no screen reaches is **Partial**. A requirement the app shows but whose data the API never supplies is **Partial**.

Path shorthand in the Evidence column:

- `A:` is `services/api/app/`
- `M:` is `apps/mobile/lib/`
- `TA:` is `services/api/tests/`
- `TM:` is `apps/mobile/test/`

"Test" names the test file that exercises the behaviour. "No test" means nothing covers it.

Findings that cut across many rows:

1. **No email is ever sent.** `A:identity/service.py` never calls the `EmailSender` in `A:platform/email.py`. The sign-in code is the fixed dev value `MOCK_EMAIL_CODE`. With it unset, `/v1/auth/start` for a new customer returns 503 `not_configured`.
2. **Notifications are never emitted.** `NotificationService.notify` in `A:notifications/service.py` has no caller outside its own tests. The inbox and device registry exist. Complaint-update and check-in pushes go to a separate logging fake in `A:support/notify.py` and do not reach the inbox.
3. **No notification preferences exist** (no table, endpoint or Settings screen).
4. **No daily job is triggered.** `generate_due_payments`, `mark_overdue_and_inactive` and `notify_due_checkins` exist and are tested, but nothing calls them (no cron endpoint, no `crons` in `services/api/vercel.json`).
5. **In-app Deep Spa bookings never reach the scheduler.** The app writes `addon_bookings`. `A:scheduling/service.py` `build_demand` reads only the legacy `addon_requests` table.
6. **Proof media is not joined.** `A:customer_reads/sql_repository.py` returns jobs with empty `proof`. Customers have no way to read a media file. `A:media/router.py` is crew only, for upload.
7. **Customers cannot upload anything.** There is no vehicle photo, complaint photo or RC upload path for the customer role.
8. **Some screens are built but unreachable.** `showVisitRatingSheet` in `M:features/support/feedback_sheet.dart` is opened by no screen. The pending check-in is reachable only from a Support tile.
9. **Admin-side dependencies are missing from the API.** There is no admin create or edit of customers, vehicles, societies, plans or add-on offers. Prices come from `MONEY_*` environment placeholders. Customers are loaded by `A:customers/importer.py`.

## Coverage table

| ID | Verdict | Evidence (files) | Missing / notes | Needs backend? | Needs account/stub? |
|---|---|---|---|---|---|
| AUTH-01 | Not built | `M:features/splash/splash_screen.dart`, `M:features/auth/presentation/login_screen.dart` | No welcome screen. The splash goes straight to the sign-in field. The `tagline` string exists in `app_en.arb` but no widget uses it. No "Get started" and "Already a member? Log in" buttons. | No | No |
| AUTH-02 | Partial | `M:features/auth/presentation/login_screen.dart`, `A:identity/service.py` (`role_for`, `normalise`) | Email is trimmed and lower-cased on the server. The app only checks for empty, so there is no invalid-format error and any text with `@` goes to the API. Test: `TM:unit_test.dart`, `TM:screens_test.dart` (empty field only). | No | No |
| AUTH-03 | Partial | `A:identity/service.py` (`start`, `_customer`, `_send_code`), `A:identity/router.py`, `M:features/auth/presentation/login_screen.dart`. Test: `TA:test_first_sign_in.py`, `TM:screens_test.dart` | Branching (unknown email, no password, password set) works. The code is the fixed dev value and nothing is emailed (cross-cutting finding 1). | Yes: call the email sender | Yes: Resend |
| AUTH-04 | Built | `M:features/auth/presentation/login_screen.dart` (`termsNotice`), `A:identity/service.py` (`set_password` sets `terms_accepted_at`), `A:customers/models.py`. Test: `TA:test_first_sign_in.py` | The notice is plain text with no links to Terms or Privacy Policy. Acceptance is stamped when the password is set. | No | No |
| AUTH-05 | Partial | `M:features/auth/presentation/login_screen.dart` (`_CodeBoxes`, countdown), `A:identity/service.py` (`CODE_LIFETIME`, `CODE_RESEND_AFTER`). Test: `TM:screens_test.dart`, `TA:test_first_sign_in.py` | Six boxes, email shown, 30-second countdown and 10-minute life are present. The code is never emailed (finding 1). | Yes: email sending | Yes: Resend |
| AUTH-06 | Built | `M:features/auth/presentation/login_screen.dart` (`_CodeBoxes` hidden input, digits only) | Paste into the hidden input fills the boxes. There is no explicit paste button. No dedicated test for paste. | No | No |
| AUTH-07 | Built | `A:identity/service.py` (`MAX_WRONG_CODES`, `MAX_CODES_AN_HOUR`, `_send_code`), `M:features/auth/presentation/login_screen.dart`. Test: `TA:test_first_sign_in.py`, `TM:screens_test.dart` | None. | No | No |
| AUTH-08 | Built | `A:customers/service.py` (`home.onboarding_confirmed`), `M:features/customer/home/customer_shell.dart` (shows the review until confirmed). Test: `TM:customer_test.dart`, `TA:test_first_sign_in.py` | None. | No | No |
| AUTH-09 | Built | `M:features/customer/onboarding/onboarding_review_screen.dart` (Back and per-section Edit), `M:features/auth/presentation/login_screen.dart` (Change). Test: `TM:customer_test.dart` | None. | No | No |
| AUTH-10 | Built | `M:core/routing/router.dart` (`redirectFor`), `A:platform/deps.py` (`require_role`). Test: `TM:unit_test.dart` | None. | No | No |
| AUTH-11 | Built | `A:identity/service.py` (`role_for`, `start`), `M:features/auth/presentation/login_screen.dart`. Test: `TA:test_first_sign_in.py` (crew and admin asked for a password) | None. | No | No |
| AUTH-12 | Built | `A:identity/service.py` (`password_problem`), `M:features/auth/presentation/login_screen.dart` (`isAcceptablePassword`). Test: `TA:test_first_sign_in.py`, `TM:screens_test.dart` | None. | No | No |
| AUTH-13 | Built | `A:identity/service.py` (`login`, `CUSTOMER_BLOCK`), `M:features/auth/presentation/login_screen.dart` (Forgot password). Test: `TA:test_first_sign_in.py` (`test_a_reset_lifts_the_15_minute_block`), `TM:screens_test.dart` | None. | No | No |
| AUTH-14 | Partial | `A:identity/service.py` (`_customer`), `A:customers/importer.py`, `A:customers/models.py` | Only existing customers can sign in. There is no admin API to create a customer (`ADM-CUS-01`); customers arrive by `scripts/import_customers.py`. Test: `TA:test_import.py`, `TA:test_first_sign_in.py`. | Yes: admin customer create (admin portal slice) | No |
| AUTH-15 | Partial | `A:identity/service.py` (`_not_registered`), `M:features/auth/presentation/login_screen.dart`. Test: `TM:screens_test.dart` | The message is shown. The "Call support" and "WhatsApp support" buttons are not. The support contact endpoint is customer-only, so an unregistered visitor cannot read the numbers. | Yes: unauthenticated contact endpoint | Yes: real support numbers |
| AUTH-16 | Partial | `A:identity/service.py` (`send_code`, `verify_code`, `set_password` ends other sessions), `M:features/auth/presentation/login_screen.dart`. Test: `TA:test_first_sign_in.py`, `TM:screens_test.dart` | Flow and rules work. The code is not emailed (finding 1). | Yes: email sending | Yes: Resend |
| AUTH-17 | Partial | `M:core/auth/session.dart` (`SecureSessionStore`), `M:core/auth/auth_controller.dart`, `A:identity/service.py` (`refresh`, `set_password`) | Session persists in secure storage with no inactivity time-out. Password reset ends other sessions. There is no way for the admin to end a customer's sessions (`ADM-CUS-21`): `logout-all` is for the admin's own sessions. Test: `TM:screens_test.dart` (stored session). | Yes: admin end-customer-sessions | No |
| ONB-01 | Built | `M:features/customer/onboarding/onboarding_review_screen.dart` (`_detailsStep`), `A:customers/service.py` (`confirm_onboarding`). Test: `TM:customer_test.dart`, `TA:test_customer_home.py` | Email is read-only with a verified icon. Mobile is a contact number, 10 digits when changed. | No | No |
| ONB-02 | Built | `A:customers/service.py` (`_NAME`), `M:features/customer/onboarding/onboarding_review_screen.dart` (`_name`). Test: `TA:test_customer_home.py` | None. | No | No |
| ONB-03 | Not built | None. The review shows the society read-only (`_societyStep`). | No society list endpoint for customers. No list with sector, city and cars serviced. Needed when a customer adds a vehicle (VEH-07). | Yes: societies read endpoint | No |
| ONB-04 | Not built | None | No society search. | Yes: with ONB-03 | No |
| ONB-05 | Not built | None | No society selection. | Yes: with ONB-03 | No |
| ONB-07 | Not built | None | No empty-list message. | No | No |
| ONB-09 | Not built | None | No Make, Model, Variant dropdowns and no catalog endpoint. | Yes: vehicle catalog read endpoint | No |
| ONB-10 | Not built | `A:customers/service.py` (`_REGISTRATION` is used only to format display) | No registration entry with upper-casing and format validation. | Yes: with VEH-07 | No |
| ONB-11 | Not built | `A:customers/models.py` (`Vehicle.category` is a stored field) | No automatic category detection from the model, and no "Auto-detected" indicator. | Yes: model-to-category mapping | No |
| ONB-12 | Not built | None | No RC upload. The prototype marked it a stub. | Yes: customer media upload | No |
| ONB-13 | Built | `M:features/customer/onboarding/onboarding_review_screen.dart` (`_basements`), `A:customers/service.py` (`BASEMENTS`). Test: `TM:customer_test.dart`, `TA:test_customer_home.py` | None. | No | No |
| ONB-14 | Built | same as ONB-13 (digits only, up to 5) | None. | No | No |
| ONB-15 | Built | `M:features/customer/onboarding/onboarding_review_screen.dart` (`parkingPreview`) | Preview shows "B2 · 123". No dedicated test. | No | No |
| ONB-16 | Built | `A:customers/service.py` (`read_cutoff`), `M:features/customer/onboarding/onboarding_review_screen.dart` (`_pickCutoff`, 30-minute list). Test: `TM:customer_test.dart`, `TA:test_customer_home.py` | None. | No | No |
| ONB-17 | Built | `M:l10n/app_en.arb` (`cutoffNote`), `M:features/customer/onboarding/onboarding_review_screen.dart` | None. | No | No |
| ONB-18 | Built | `A:customers/service.py` (`_asks_interior_day`), `M:features/customer/onboarding/onboarding_review_screen.dart` (`asksInteriorDay`). Test: `TA:test_customer_home.py` | Hidden when the plan has no interior cleaning. | No | No |
| ONB-20 | Built | `A:customers/service.py` (`confirm_onboarding` error texts), `M:features/customer/onboarding/onboarding_review_screen.dart` (`_check`). Test: `TA:test_customer_home.py` (`test_the_gaps_must_be_filled_before_confirming`) | None. | No | No |
| ONB-21 | Built | `A:customers/service.py` (`confirm_onboarding`) | Preferences are saved once, at the final confirm, not at each Continue. Behaviour is equivalent for the review flow. | No | No |
| ONB-22 | Not built | None. `Vehicle` has no photo field. | No vehicle photo in the review, no camera or gallery pick, no upload, nothing required. `image_picker` is in `pubspec.yaml` but not used for this. | Yes: customer media upload and vehicle photo field | No |
| ONB-23 | Partial | `M:features/customer/onboarding/onboarding_review_screen.dart` (plan row, read-only) | The review shows the admin's plan read-only, inside the vehicle step. The plan step before preferences for a customer-added vehicle does not exist (VEH-07). | Yes: with VEH-07 | No |
| ONB-25 | Built | `A:customers/router.py` (`/v1/customer/onboarding`, `/confirm`), `A:customers/service.py`, `M:features/customer/home/customer_shell.dart`, `M:features/customer/onboarding/onboarding_review_screen.dart`. Test: `TA:test_customer_home.py`, `TM:customer_test.dart` | Steps are: details, society, one per vehicle, review. Home opens only after confirm. | No | No |
| ONB-26 | Partial | same as ONB-25 | Names, mobile, parking, cutoff and interior day can be changed. The vehicle photo cannot (no photo, ONB-22). Society, vehicle and plan are shown read-only. | Yes: with ONB-22 | No |
| PAY-01 | Partial | `M:features/customer/onboarding/onboarding_review_screen.dart` (plan row: name and price per month) | No struck-through list price, no "Founding member" badge, no "Cancel anytime", no inclusions list. The home `VehicleCard` has no list price. | Yes: plan inclusions and list price | No |
| PAY-02 | Not built | None | No inclusions list on any screen. | Yes: plan inclusions from admin plan data | No |
| PAY-03 | Partial | `M:features/customer/onboarding/onboarding_review_screen.dart` (`_reviewStep`) | Shows name, email, mobile, society, registration, parking, cutoff, interior day, plan. No make and model, no "Priveo will confirm the start date" message. | No | No |
| PAY-04 | Partial | same as PAY-03 | Monthly price is shown. There is no "total payable today" line. | No | No |
| PAY-05 | Partial | `M:features/changes_money/pay_screen.dart`, `A:billing/router.py` (`/payments/{id}`), `A:billing/config.py`. Test: `TM:changes_money/changes_money_test.dart`, `TA:billing/test_billing.py` | The UPI screen exists with a copyable UPI ID and a QR image from a URL. Nothing opens it from the onboarding "Confirm & pay" (PAY-13). UPI ID and QR are `MONEY_*` placeholders. | No | Yes: real UPI ID and QR image |
| PAY-06 | Built | `A:billing/service.py` (`mark_paid`), `M:features/changes_money/pay_screen.dart`. Test: `TA:billing/test_billing.py`, `TM:changes_money/changes_money_test.dart` | Status goes to Initiated and an admin alert is raised. | No | No |
| PAY-07 | Built | `M:features/changes_money/pay_screen.dart` (`_Submitted`) | Shows amount, description and status Initiated, with "Go to home". The vehicle name is not on the screen beyond the description text. | No | No |
| PAY-08 | Built | `A:billing/router.py` (`/admin/payments/{id}/confirm`, `/reject`), `A:billing/service.py`. Test: `TA:billing/test_billing.py` | Customer-side result is correct. The admin screen is covered by the admin audit (quick actions exist in `M:features/admin_quick/payments`). | No | No |
| PAY-09 | Built | `A:billing/schemas.py`, `M:features/changes_money/money_widgets.dart` (`PaymentStatusChip`), `M:features/changes_money/data/money_models.dart`. Test: `TM:changes_money/changes_money_test.dart` ("Due by dd-Mon-yy") | None. | No | No |
| PAY-10 | Built | `A:customers/models.py` (`Subscription.status`), `A:billing/service.py` (`set_subscription_status`), `M:features/changes_money/subscription_screen.dart`. Test: `TA:billing/test_billing.py` | Home and My subscription both show the status chip. | No | No |
| PAY-11 | Not built | None | Adding a vehicle does not exist (VEH-07). | Yes: with VEH-07 | No |
| PAY-12 | Partial | `M:features/customer/onboarding/onboarding_review_screen.dart` (admin's plan, read-only) | The admin's plan is shown on the review. There is no plan list endpoint, so no plan step for an added vehicle. | Yes: customer plans read endpoint, admin plan data (`ADM-SET-01`) | No |
| PAY-13 | Not built | None | The review step has no payment status and no "Confirm & pay". The first payment is not surfaced in onboarding. The API has `POST /v1/admin/payments` for the admin to set it. | No (API exists) | No |
| HOME-01 | Partial | `M:features/customer/home/customer_shell.dart` (`_TopBar`, greeting) | Avatar with initials opens Account. The greeting is a fixed "Hello," with the first name, not by time of day. | No | No |
| HOME-02 | Partial | `M:features/customer/home/customer_shell.dart` (`_VehicleCard`), `A:home/schemas.py` (`VehicleCard`) | Shows registration, model, society, parking, status and price. No vehicle photo and no variant. | Yes: photo URL and variant on `VehicleCard` | No |
| HOME-03 | Not built | None | No "Today's clean is done" banner, no checks count, no photo count, no "View proof" action. The home API carries no completion data. | Yes: today's completion summary | No |
| HOME-04 | Partial | `M:features/customer/home/customer_shell.dart` (`_NextServiceCard`), `A:customer_reads/router.py` (`/next-service`). Test: `TM:customer/customer_slice_test.dart` | Status, date, service, cutoff, interior day and "View calendar" are shown. The date is plain `dd-Mon-yy`, not "Tomorrow, Wed ...". No crew name or assigned time (CAL-10). `/v1/customer/next-job` has them but the app does not call it. | No (API exists) | No |
| HOME-05 | Partial | `M:features/customer/home/customer_shell.dart` (`_QuickAction`), `A:customers/service.py` (`QUICK_ACTIONS`) | Skip or pause, Service history, Report an issue are present. "Give Feedback" is present (the spec puts it in Support). "Rate today's clean" is missing. Subscription and Add-ons tiles are extra. | Yes: today's visit id on home | No |
| HOME-07 | Built | `M:features/customer/home/customer_shell.dart` (`_VehicleCarousel`), `M:features/customer/home/customer_home_data.dart` (`selectedVehicleProvider`). Test: `TM:customer_test.dart` | Calendar, history and money screens follow the selection. | No | No |
| HOME-08 | Partial | `A:support/service.py` (`pending_checkins`), `A:support/router.py` (`/checkins/pending`), `M:features/support/help_screen.dart` | The API returns what is due. Home has no "Monthly check-in" card. The check-in is a tile on the Support tab only. Test: `TA:support/test_support.py`, `TM:support/support_test.dart` (tile). | No (API exists) | No |
| HOME-09 | Partial | `M:features/customer/home/customer_shell.dart` (Add-ons quick action) | It is a quick-action tile, not a card, and it is shown for every vehicle, not only Active ones. | No | No |
| CAL-01 | Partial | `M:features/customer/calendar/calendar_screen.dart`, `A:customer_reads/router.py` (`/calendar`). Test: `TM:customer/customer_slice_test.dart`, `TA:customer_reads/test_customer_reads.py` | Monday-first month grid with arrows. Only visits the scheduler has already created are shown. Future months do not project expected visits from the subscription. | Yes: projected visits from subscription | No |
| CAL-02 | Partial | `M:features/customer/calendar/calendar_screen.dart` (`markerFor`, `MarkerDot`) | Done, Done + Interior, Spa, Scheduled, Skipped and Missed exist. An upcoming interior day and an upcoming Deep Spa day both show the same outlined Scheduled marker, not the outlined interior or Full spa marker. | No | No |
| CAL-03 | Built | `M:features/customer/calendar/calendar_screen.dart` (`_Legend`) | None. | No | No |
| CAL-04 | Built | `M:features/customer/calendar/calendar_screen.dart` (`_DayCell`) | Today and the selected date are highlighted. | No | No |
| CAL-05 | Partial | `M:features/customer/calendar/calendar_screen.dart` (`_DayCard`, `_DayVisit`) | Service type, status chip and a one-line note are there. A completed day shows "View service details" and not the finish time and checks. Test: `TM:customer/customer_slice_test.dart`. | Yes: finish time and checks in the calendar read | No |
| CAL-06 | Partial | `M:features/customer/calendar/calendar_screen.dart` (`_DayVisit`) | Completed opens Service Details. A scheduled day shows the "Scheduled to be completed by ..." text. Crew member and assigned time are missing (CAL-10). | No | No |
| CAL-07 | Partial | `M:features/changes_money/skip_pause_screen.dart` (invalidates providers), `A:changes/service.py` (`change_cutoff`: Applied or Requested). Test: `TA:changes/test_changes.py` | Skip, un-skip and pause appear on the calendar after they are made (the calendar reloads). A frozen-schedule cutoff request is stored as Requested, but no screen shows "Change requested, awaiting Priveo". | No (API exists) | No |
| CAL-08 | Partial | `A:changes/router.py` (`POST /vehicles/{id}/cutoff-changes`), `A:changes/service.py`. Test: `TA:changes/test_changes.py` | API is built with the 9 PM rule. The calendar day card has no "Change cutoff time" action, and `MoneyRepository` has no cutoff call. | No (API exists) | No |
| CAL-09 | Partial | `M:features/customer/calendar/calendar_screen.dart` (Missed marker, `missedNote`), `A:customer_reads/sql_repository.py` (status map) | Missed marker and chip exist. The text is "This service was missed." The "Covered on dd-Mon-yy" and "Rescheduled on dd-Mon-yy" lines are not built, and the API gives no covering or new date. | Yes: covered or rescheduled date on the visit read | No |
| CAL-10 | Partial | `A:scheduling/router.py` (`/v1/customer/next-job`, with `crew_name`, `start_time`, `end_time`), `M:features/scheduling/dto.dart` | API returns the next job with crew and time. The customer app does not call it, so Home and the day card never show them. The calendar API has no per-visit assignment. Test: `TA:scheduling/test_scheduling_api.py`. | Yes: assignment on calendar read | No |
| SVC-01 | Partial | `M:features/customer/visit/visit_details_screen.dart`, `A:customer_reads/router.py` (`/visits/{id}`). Test: `TM:customer/customer_slice_test.dart`, `TA:customer_reads/test_customer_reads.py` | Date, status chip, vehicle and jobs are shown. Service type shows per job. No finish time. | Yes: finish time | No |
| SVC-02 | Not built | None | No crew member card per job. `VisitDetail` has no crew name. The screen's own comment says the crew card "comes with the crew slice". | Yes: crew name per job | No |
| SVC-03 | Not built | None | No checklist or per-item completion on the customer's visit. The crew checklist exists (`A:visits/service.py`) but is not exposed to customers. | Yes: checklist items on the visit read | No |
| SVC-04 | Partial | `M:features/customer/visit/visit_details_screen.dart` (grid), `A:customer_reads/schemas.py` (`ProofOut`), `A:customer_reads/sql_repository.py` | The photo grid and the model exist and work with fake data (`TA:customer_reads/test_customer_reads.py` uses an in-memory repository). The SQL repository returns no proof, so a real visit shows no photos. No "AFTER" labels and no "View all" action. | Yes: join `media_uploads`, signed read URLs | No (dev store is used) |
| SVC-05 | Partial | `M:features/customer/visit/visit_details_screen.dart` (`PhotoViewer`) | Full-screen viewer with "1 / 4" and a close button. No caption with stage, time and area, and no Before/During/After. Depends on SVC-04 data. | Yes: stage and time on proof | No |
| SVC-06 | Partial | `M:features/customer/visit/visit_details_screen.dart` (video tile) | A "Play video" tile opens the URL in the external player. No duration, no play-in-place, no progress bar. Depends on SVC-04 data. | Yes: with SVC-04 | No |
| SVC-07 | Partial | `M:features/support/feedback_sheet.dart` (`showVisitRatingSheet`, `VisitRatingForm`), `A:support/router.py` (`PUT /visits/{id}/rating`), `A:support/service.py` (`rate_visit`). Test: `TM:support/support_test.dart`, `TA:support/test_support.py` | Rating, thank-you and storage work and are general to the visit. No screen opens the sheet: Service Details has no rating control. The API does not check that the visit belongs to the customer or is Completed. | Yes: visit ownership check | No |
| SVC-08 | Partial | `M:features/support/routes.dart` (`/customer/support/report?visit=`), `M:features/support/report_issue_screen.dart` | The report form accepts a linked visit. Service Details has no "Report an issue with this clean" button. | No | No |
| SVC-09 | Partial | `M:features/customer/calendar/calendar_screen.dart`, `M:features/customer/history/history_screen.dart`, `M:features/customer/notifications/notifications_screen.dart`. Test: `TM:customer/customer_slice_test.dart` | Opens from the calendar, history and a notification. Not from Home (no "View proof", HOME-03). | No | No |
| SVC-11 | Partial | `A:support/service.py` (`options`, `rate_visit`, `defaults.POSITIVE_TAGS`), `M:features/support/feedback_sheet.dart`. Test: `TM:support/support_test.dart`, `TA:support/test_support.py` | Tags load from the backend and are offered at 5 stars. Admin can edit them. The rating sheet is unreachable (SVC-07). | No | No |
| SVC-12 | Built | `A:support/models.py` (`VisitRating`, no crew link), `A:support/service.py` (`rate_visit`). Test: `TA:support/test_support.py` | Tags saved with the rating, never tied to a crew member. | No | No |
| SVC-13 | Built | `A:support/models.py` (`testimonial_permission`), `A:support/schemas.py` (`RatingAdmin`) | Permission is stored and sent to the admin. Nothing uses a comment without it. | No | No |
| SVC-14 | Partial | `A:support/service.py` (`rate_visit` allows feedback categories below 5), `M:features/support/feedback_sheet.dart`. Test: `TM:support/support_test.dart`, `TA:support/test_support.py` | Works, but the sheet is unreachable (SVC-07). | No | No |
| SVC-15 | Partial | `M:features/support/feedback_sheet.dart` (comment box, testimonial checkbox off by default). Test: `TM:support/support_test.dart` | Built at every star level, but the sheet is unreachable (SVC-07). | No | No |
| HIST-01 | Partial | `M:features/customer/history/history_screen.dart`, `A:customer_reads/router.py` (`/history`). Test: `TM:customer/customer_slice_test.dart`, `TA:customer_reads/test_customer_reads.py` | Newest first, date, service type, status, photo count, opens Service Details for Completed. No finish time and no rating given. | Yes: finish time and rating on the history item | No |
| HIST-02 | Partial | same as HIST-01 | One flat list, newest first, from `limit` and `offset`. No month grouping or month navigation, no member-since footer, and the app never asks for more pages. | Yes: month filter and member-since | No |
| SKIP-01 | Built | `M:features/changes_money/skip_pause_screen.dart` (`_DayChip`), `A:changes/service.py` (`upcoming`). Test: `TM:changes_money/changes_money_test.dart`, `TA:changes/test_changes.py` | Weekday, day number and service type (Exterior, + Interior). | No | No |
| SKIP-02 | Built | `M:features/changes_money/strings.dart` (`skipInstruction`), `A:changes/rules.py` (`require_open`). Test: `TA:changes/test_changes.py` | None. | No | No |
| SKIP-03 | Built | `M:features/changes_money/skip_pause_screen.dart`. Test: `TM:changes_money/changes_money_test.dart` | Note and "Confirm skip". | No | No |
| SKIP-04 | Built | `M:features/changes_money/strings.dart` (`skipPickFirst`). Test: `TM:changes_money/changes_money_test.dart` | None. | No | No |
| SKIP-05 | Partial | `A:changes/sql_gateway.py` (`skip_day`), `M:features/changes_money/skip_pause_screen.dart`. Test: `TA:changes/test_changes.py` | The visit's jobs become Skipped (the crew day reflects it) and the app confirms "The crew has been told". No push is sent to the crew, and no "Service skipped" notification is made (finding 2). | Yes: crew and customer notification | Yes: FCM |
| SKIP-06 | Partial | `M:features/changes_money/skip_pause_screen.dart` (`_UpcomingRow`) | Upcoming list shows the next 7 dates with type and Skipped state. No "View calendar" link. | No | No |
| SKIP-07 | Built | `A:changes/service.py` (`unskip`), `M:features/changes_money/skip_pause_screen.dart` ("Undo skip"). Test: `TA:changes/test_changes.py`, `TM:changes_money/changes_money_test.dart` | The crew is told only through the job status (as SKIP-05). | No | No |
| SKIP-08 | Built | `A:changes/service.py` (`inside_pause`). Test: `TA:changes/test_changes.py` | Paused dates are not selectable in the app. | No | No |
| PAUSE-01 | Built | `M:features/changes_money/skip_pause_screen.dart` (date pickers) | None. | No | No |
| PAUSE-02 | Partial | `A:changes/schemas.py` (`visits_paused`, `renewal_date`), `M:features/changes_money/skip_pause_screen.dart` | The new renewal date is shown after confirming. There is no preview of visits paused and renewal before confirming, and `visits_paused` is not displayed. | No | No |
| PAUSE-03 | Built | `M:features/changes_money/strings.dart` (`pauseChoose`, `pauseDone`). Test: `TM:changes_money/changes_money_test.dart` | None. | No | No |
| PAUSE-04 | Built | `A:billing/service.py` (`effective_status`). Test: `TA:billing/test_billing.py` | Status reads "Paused" on the paused days. | No | No |
| PAUSE-05 | Built | `A:changes/service.py` (`end_pause`), `M:features/changes_money/skip_pause_screen.dart`. Test: `TA:changes/test_changes.py`, `TM:changes_money/changes_money_test.dart` | None. | No | No |
| PAUSE-06 | Built | `A:changes/service.py` (`pause` merges skips), `A:changes/cycle.py`. Test: `TA:changes/test_changes.py` | None. | No | No |
| PAUSE-07 | Built | `A:changes/service.py` (`pause`). Test: `TA:changes/test_changes.py` | None. | No | No |
| SCHED-01 | Built | `A:changes/rules.py`, `A:changes/service.py`, `A:addons/service.py`. Test: `TA:changes/test_changes.py`, `TA:addons/test_addons.py` | Covers skip, un-skip, pause start and end, cutoff change, add-on change and cancel. Admin is exempt. | No | No |
| SCHED-02 | Partial | `M:features/changes_money/skip_pause_screen.dart` (chips disabled), `M:features/changes_money/strings.dart` (`callSupport` is defined) | Controls are disabled after cutoff. The "call the helpline" message and "Call support" button are not shown (`callSupport` is never used). | No | No |
| ACC-01 | Not built | `M:features/customer/account/account_screen.dart` | Account shows a name line only. No avatar, no mobile number, not tappable, no Edit profile. | Yes: profile read | No |
| ACC-02 | Not built | None | No subscription cards on Account. My subscription is reached from the Home quick action. | No (API exists) | No |
| ACC-03 | Partial | `M:features/customer/account/account_screen.dart` | Has My vehicles, Service history, Notifications and Sign out. Missing: Service calendar (it is a tab), Add-ons, Skip or pause, My complaints, Help & support (a tab), Settings. Test: `TM:customer/customer_slice_test.dart`. | No | No |
| ACC-04 | Built | `M:features/customer/account/account_screen.dart`, `M:features/common/signout_button.dart`, `A:identity/router.py` (`/logout`). Test: `TM:customer/customer_slice_test.dart`, `TM:screens_test.dart` | None. | No | No |
| ACC-06 | Not built | None | No Edit profile screen. First and last name and mobile can be changed only once, in the onboarding review. No endpoint for later edits. | Yes: profile update endpoint | No |
| ACC-07 | Built | `M:l10n/app_en.arb` (English only, no selector) | None. | No | No |
| ACC-08 | Not built | None | No email change, no code to the new email, no duplicate check. | Yes: email-change code flow | Yes: Resend |
| SET-01 | Not built | `M:features/customer/account/account_screen.dart` | A "Settings" heading with "Notification choices will be available in a later update." | No | No |
| SET-02 | Not built | None | No switches. No preference table or endpoint. | Yes: notification preferences | No |
| SET-03 | Not built | None | No defaults stored. | Yes: with SET-02 | No |
| SET-04 | Not built | None | No Settings content. | Yes: with SET-02 | No |
| NOTIF-01 | Partial | `A:notifications/router.py` (`PUT /devices`), `A:notifications/push.py` (`LoggingPushSender`), `M:features/customer/data/customer_reads_repository.dart` (`registerDevice`) | Token registry and a logging push sender exist. The app never registers a token, has no Firebase and never asks for OS permission. Test: `TA:notifications/test_notifications.py`. | Yes: real push sender | Yes: FCM (Firebase account) |
| NOTIF-02 | Partial | `A:notifications/service.py` (`EVENTS`, `notify`), `M:features/customer/notifications/notifications_screen.dart`. Test: `TA:notifications/test_notifications.py`, `TM:customer/customer_slice_test.dart` | The five events are defined and the inbox works. No module calls `notify`, so no event is produced (finding 2). | Yes: emit events | Yes: FCM |
| NOTIF-03 | Not built | None | No preference check anywhere. | Yes: with SET-02 | No |
| NOTIF-04 | Not built | `A:visits/service.py` (`manager_skip` comment: notification belongs to another module), `A:changes/service.py` | No "Service skipped" notification for a customer skip or for a skip by operations. | Yes: emit on skip and ops skip | Yes: FCM |
| NOTIF-05 | Not built | `A:billing/service.py` (`generate_due_payments`) | No reminder schedule (one week, one day, every 2 days) and no stop or restart rules. `renewal_reminder` is only a name in the event list. | Yes: reminder job | Yes: FCM, cron |
| NOTIF-06 | Partial | `A:support/service.py` (`notify_due_checkins`), `A:support/notify.py`. Test: `TA:support/test_support.py` (`test_checkin_push_goes_out_four_days_before_renewal`) | The function picks the right day, once. It sends through a logging fake, not the inbox or FCM, ignores preferences and is not scheduled. | Yes: schedule and real push | Yes: FCM, cron |
| SUB-01 | Built | `M:features/changes_money/subscription_screen.dart` (`_PlanCard`), `A:billing/service.py` (`subscription_view`), `A:changes/cycle.py`. Test: `TM:changes_money/changes_money_test.dart`, `TA:billing/test_billing.py` | Ring, days left, cycle dates, amount and method. Note: a visit skipped by operations should also move the renewal date (rule 25), and `cycle.py` counts pauses only. | Yes: ops-skip extension (with admin ops skip) | No |
| SUB-02 | Built | `M:features/changes_money/subscription_screen.dart`, `A:billing/schemas.py` (`SubscriptionView`) | None. | No | No |
| SUB-03 | Built | `M:features/changes_money/subscription_screen.dart` ("Pause service") | Shown for Active and Paused. | No | No |
| SUB-05 | Built | `A:billing/service.py` (`effective_status`, `set_subscription_status`), `M:features/changes_money/subscription_screen.dart`. Test: `TA:billing/test_billing.py` | None. | No | No |
| SUB-06 | Built | `A:billing/router.py` (`/vehicles/{id}/payments`), `M:features/changes_money/billing_history_screen.dart`. Test: `TM:changes_money/changes_money_test.dart`, `TA:billing/test_billing.py` | None. | No | No |
| SUB-08 | Not built | `A:changes/router.py` (per-date `cutoff-changes` only) | No way to edit the default cutoff time or interior day after signup. No endpoint and no screen. | Yes: subscription preferences update | No |
| SUB-09 | Built | `A:billing/service.py` (`ensure_next_payment`, `PAY_AHEAD_DAYS`), `M:features/changes_money/subscription_screen.dart`, `M:features/changes_money/pay_screen.dart`. Test: `TA:billing/test_billing.py`, `TM:changes_money/changes_money_test.dart` | None. | No | Yes: real UPI details |
| SUB-10 | Built | `A:billing/schemas.py` (`latest_payment`), `M:features/changes_money/subscription_screen.dart`. Test: `TM:changes_money/changes_money_test.dart` | None. | No | No |
| SUB-11 | Partial | `A:billing/service.py` (`mark_overdue`, `mark_overdue_and_inactive`), `A:billing/router.py` (admin status). Test: `TA:billing/test_billing.py` | The 7-day rule, the add-on exception and the admin set and reactivate all work when the job runs. Nothing runs the job (finding 4). | Yes: cron endpoint | Yes: Vercel cron |
| SUB-12 | Partial | `A:billing/router.py` (`/payments/{id}/invoice`), `M:features/changes_money/billing_history_screen.dart`. Test: `TM:changes_money/changes_money_test.dart`, `TA:billing/test_billing.py` | The invoice opens in a dialog. The customer cannot save or share it (no PDF, no share action). | No | No |
| VEH-01 | Not built | None | No vehicle photo field, no capture, no "Change photo", no photo on Home or My vehicles. | Yes: customer media upload, photo field | No |
| VEH-02 | Built | `M:features/customer/vehicles/vehicles_screen.dart` (`VehicleDetailScreen`), `A:customer_reads/router.py` (`/vehicles/{id}`). Test: `TM:customer/customer_slice_test.dart`, `TA:customer_reads/test_customer_reads.py` | Registration, make and model, variant, category. | No | No |
| VEH-03 | Partial | same as VEH-02 | Society, basement and parking number are shown. RC document status is not. | Yes: RC status | No |
| VEH-04 | Not built | `M:features/customer/vehicles/vehicles_screen.dart` (`carDetailsViaSupport` text) | The detail screen is read-only. No parking edit and no photo edit. No endpoint to update parking after onboarding. | Yes: vehicle parking update | No |
| VEH-06 | Built | `M:features/customer/vehicles/vehicles_screen.dart`, `A:customer_reads/router.py` (`/vehicles`). Test: `TM:customer/customer_slice_test.dart`, `TA:customer_reads/test_customer_reads.py` | None. | No | No |
| VEH-07 | Not built | None | No "Add vehicle" action or flow, and no endpoint for a customer to create a vehicle or subscription. | Yes: customer add-vehicle | No |
| VEH-08 | Built | `A:customers/service.py` (`home` lists all active vehicles), `M:features/customer/home/customer_shell.dart` | Any vehicle on the account appears in the switcher. Creation is by the admin (VEH-07 not built). | No | No |
| VEH-09 | Partial | `A:customers/models.py` (`Customer.society_id`) | Society is fixed, and nothing changes it. It is stored on the customer, not the vehicle, so vehicles of one customer cannot be in different societies. | Yes: move society to the vehicle | No |
| ADD-01 | Partial | `A:addons/service.py` (`request`: Active and not paused), `M:features/changes_money/subscription_screen.dart` (button only when Active) | The API refuses otherwise. The Home Add-ons tile opens the screen for any vehicle, so the screens are not hidden. Test: `TA:addons/test_addons.py`. | No | No |
| ADD-02 | Partial | `A:addons/service.py` (`offers`, `mine`), `M:features/changes_money/addon_screen.dart`, `M:features/customer/home/customer_shell.dart`. Test: `TM:changes_money/changes_money_test.dart`, `TA:addons/test_addons.py` | Offer (name, description, price, struck-through price) and earlier requests with status. Price comes from `MONEY_*` settings, not an admin-managed add-on table (`ADM-ADD-01`). No "Add-ons" item in the Account menu. | Yes: admin add-on offer data | No |
| ADD-03 | Built | `A:addons/service.py` (`request`). Test: `TA:addons/test_addons.py` | Each request has its own payment. | No | No |
| ADD-04 | Built | `A:addons/service.py` (`request`, `_time`), `M:features/changes_money/addon_screen.dart`. Test: `TA:addons/test_addons.py`, `TM:changes_money/changes_money_test.dart` | Date from tomorrow, before 9 PM cutoff, finish-by in 30-minute steps, summary. | No | No |
| ADD-05 | Built | `A:addons/service.py` (`open_addon_payment`), `M:features/changes_money/addon_screen.dart`, `M:features/changes_money/pay_screen.dart`. Test: `TA:addons/test_addons.py` | Same UPI screen. Invoice via admin (`issue_invoice`). | No | Yes: real UPI details |
| ADD-06 | Partial | `A:addons/service.py` (no payment gating) | Nothing waits for payment, but the request is not planned at all (ADD-08). | Yes: with ADD-08 | No |
| ADD-07 | Partial | `A:addons/models.py` (`ADDON_STATUSES`), `M:features/changes_money/addon_screen.dart` (chips) | The five statuses exist. Only Requested and Cancelled are ever set by the system. Scheduled, Completed and Missed arrive only by manual admin patch. | Yes: status follows the job | No |
| ADD-08 | Not built | `A:scheduling/service.py` (`build_demand` reads `addon_requests`) | The scheduler does not read `addon_bookings`, so an in-app request is never planned and never gets a crew member or time. The finish-by time of an add-on is not used (comment in `build_demand`). | Yes: scheduler reads bookings | No |
| ADD-09 | Not built | `A:scheduling/router.py` (`/needs-scheduling`) | Bookings are not in the Needs scheduling list. | Yes: with ADD-08 | No |
| ADD-10 | Partial | `A:addons/router.py` (`PATCH`, `DELETE /addons/{id}`), `M:features/changes_money/addon_screen.dart` (cancel only). Test: `TA:addons/test_addons.py`, `TM:changes_money/changes_money_test.dart` | Cancel works and a cancelled add-on is voided. The app cannot change the date or time (the API can). No "Change requested, awaiting Priveo" after a freeze and no "Call support" message after the cutoff. | No (API exists, except the frozen request) | No |
| ADD-11 | Not built | None | A booked add-on does not appear on the calendar (no job exists, ADD-08), so no Full spa marker and no proof flow for it. | Yes: with ADD-08 | No |
| ADD-12 | Not built | None | No Missed handling or "Rescheduled on" text for an add-on. | Yes: with ADD-08 | No |
| ADD-13 | Not built | None | "Service completed" is never produced (finding 2). | Yes: with NOTIF-02 | Yes: FCM |
| ADD-14 | Partial | `A:addons/router.py` (`POST /addons/standalone`), `M:features/changes_money/addon_screen.dart` (`StandaloneDeepSpaScreen`). Test: `TA:addons/test_addons.py`, `TM:changes_money/changes_money_test.dart` | A derived request form with a contact number. No payment, no price, no status follow-up beyond the request list. | No | No |
| ADD-15 | Not built | `A:addons/service.py` (`standalone`, marked Derived or Open) | Owner decision still open. The simplest path (request, Priveo calls) stands in. | No (owner decision) | No |
| SUP-01 | Partial | `M:features/support/help_screen.dart`, `A:support/router.py` (`/support/contact`). Test: `TM:support/support_test.dart` | Report an issue, My complaints (count in progress) and Give feedback are listed. No Frequently asked questions. | No | No |
| SUP-02 | Built | `M:features/support/help_screen.dart` (`tel:`), `A:support/config.py`. Test: `TM:support/support_test.dart`, `TA:support/test_support.py` | The number is a `SUPPORT_HELPLINE` placeholder `+910000000000`. | No | Yes: real helpline number |
| SUP-03 | Built | `M:features/support/help_screen.dart` (`whatsappUri`). Test: `TM:support/support_test.dart` | Placeholder number as SUP-02. | No | Yes: real WhatsApp number |
| SUP-04 | Built | `A:support/config.py` (`support_hours`), `M:features/support/help_screen.dart` | "6 AM to 10 PM". | No | No |
| SUP-05 | Not built | None | No FAQ screen and no Markdown asset. | No | Yes: Priveo's FAQ content |
| SUP-06 | Built | `M:features/support/help_screen.dart`, `M:features/support/feedback_sheet.dart`. Test: `TM:support/support_test.dart` | None. | No | No |
| ISS-01 | Built | `A:support/models.py` (`ISSUE_CATEGORIES`), `M:features/support/report_issue_screen.dart`. Test: `TM:support/support_test.dart`, `TA:support/test_support.py` | None. | No | No |
| ISS-02 | Partial | `M:features/support/report_issue_screen.dart`, `A:support/schemas.py` (`visit_id`) | A visit id from the entry point is stored and a line says it is linked. There is no selector to choose or change the visit, and the API does not check ownership. | Yes: visit list and ownership check | No |
| ISS-03 | Built | `M:features/support/report_issue_screen.dart`, `A:support/service.py` (`create_complaint`). Test: `TM:support/support_test.dart` | None. | No | No |
| ISS-04 | Not built | `A:support/schemas.py` (`photo_keys` accepted) | The app has no photo picker on the form and sends no photo. The API stores keys only, and customers have no upload endpoint. | Yes: customer media upload | No |
| ISS-05 | Built | `M:features/support/report_issue_screen.dart`, `A:support/service.py`. Test: `TM:support/support_test.dart` | "Choose what went wrong." | No | No |
| ISS-06 | Built | `A:support/service.py` (`display_id`, `create_complaint`), `M:features/support/report_issue_screen.dart`. Test: `TM:support/support_test.dart`, `TA:support/test_support.py` | ID `#C-NNNN`, "reply within 4 hours", lands on My complaints, newest first. | No | No |
| CMP-01 | Built | `M:features/support/complaints_screen.dart`, `A:support/router.py` (`/complaints`). Test: `TM:support/support_test.dart` | None. | No | No |
| CMP-02 | Built | `M:features/support/complaints_screen.dart` (`LinearProgressIndicator`), `A:support/models.py` (`COMPLAINT_STATUSES`) | None. | No | No |
| CMP-03 | Built | `A:support/service.py` (`_latest_notes`), `M:features/support/complaints_screen.dart`. Test: `TA:support/test_support.py` | Latest admin note on the card, full thread on the detail (reply is extra, deferred to V2 in the spec). | No | No |
| CMP-04 | Partial | `A:support/service.py` (`_push_customer`), `A:support/notify.py` | A push is requested on status change or note, but it goes to a logging fake, not the inbox or a device, and ignores preferences. | Yes: use `NotificationService`, preferences | Yes: FCM |
| FDBK-01 | Not built | `M:features/customer/home/customer_shell.dart` (a Home quick action only) | No side tab on the right edge on every screen, no dragging. Reachable only from Home and Support. | No | No |
| FDBK-02 | Built | `M:features/support/feedback_sheet.dart` (`FeedbackForm`), `A:support/router.py` (`/feedback`). Test: `TM:support/support_test.dart` | Category, rating, comments. | No | No |
| FDBK-03 | Built | `M:features/support/feedback_sheet.dart`. Test: `TM:support/support_test.dart` | Snackbar thank-you, closes without sending. | No | No |
| FDBK-04 | Built | `M:features/support/feedback_sheet.dart` (`StarRating`) | One tap. | No | No |
| FDBK-05 | Built | `M:features/support/feedback_sheet.dart`, `A:support/models.py`. Test: `TM:support/support_test.dart` | Off by default, exact wording. | No | No |
| FDBK-06 | Built | `A:support/service.py` (`options`, `add_option`, `patch_option`), `A:support/defaults.py`, `M:features/support/feedback_sheet.dart`. Test: `TA:support/test_support.py` | Categories with helper text, admin editable through the API. | No | No |
| FDBK-07 | Built | `M:features/support/feedback_sheet.dart` (`_canSend`), `A:support/service.py` (`give_feedback`). Test: `TM:support/support_test.dart`, `TA:support/test_support.py` | None. | No | No |
| CHK-01 | Partial | `A:support/service.py` (`notify_due_checkins`) | Same as NOTIF-06: logging fake only, not scheduled. | Yes: schedule and real push | Yes: FCM, cron |
| CHK-02 | Partial | `M:features/support/checkin_screen.dart`, `A:support/service.py` (`options`) | Lists all active categories from the backend, each with its own star rating and optional. The seeded default list has 3 of the 6 owner categories. Test: `TM:support/support_test.dart`. | Yes: seed 6 categories | No |
| CHK-03 | Partial | `A:support/defaults.py` (`CHECKIN_CATEGORIES`), `A:support/router.py` (admin options) | Loaded from the backend and admin editable. The default list lacks Crew professionalism, App and support, and Interest in add-ons, and the descriptions differ. | Yes: seed 6 categories | No |
| CHK-04 | Built | `A:support/models.py` (`CheckIn`, unique per subscription and cycle), `A:support/service.py` (`submit_checkin`). Test: `TA:support/test_support.py` | None. | No | No |
| CHK-05 | Partial | `M:features/support/checkin_screen.dart`, `M:features/support/routes.dart` (`/customer/support/checkin`) | Rating, submit and thank-you work. No notification delivers a tap-through (finding 2, NOTIF-06). It is reached from a Support tile. | Yes: with NOTIF-06 | Yes: FCM |
| CHK-06 | Built | `M:features/support/checkin_screen.dart`, `A:support/service.py`. Test: `TM:support/support_test.dart` | None. | No | No |
| CHK-07 | Built | `M:features/support/checkin_screen.dart` (`_ratings.isEmpty`). Test: `TM:support/support_test.dart` | The API also needs at least one answer. | No | No |
| CHK-08 | Partial | `A:support/service.py` (`pending_checkins`: last 4 days of the cycle until given, independent of preferences) | Rule is implemented in the API. No Home card (HOME-08). Test: `TA:support/test_support.py`. | No (API exists) | No |
| NAV-01 | Built | `M:features/customer/home/customer_shell.dart` (`_TabBar`). | Home, Calendar, Account, Support. Detail screens are pushed over it. | No | No |
| NAV-02 | Built | `M:features/customer/routes.dart`, `M:features/support/routes.dart` | Back returns to the previous screen. | No | No |
| NAV-03 | Built | `M:features/customer/home/customer_shell.dart` (`_go`) | Switching tabs replaces the body. No dedicated test. | No | No |
| NAV-04 | Built | `M:features/changes_money/money_widgets.dart` (`showMessage`), `M:features/support/feedback_sheet.dart` (snackbars) | Used across the screens. | No | No |
| C-01 | Built | `M:l10n/app_en.arb`, `M:features/customer/onboarding/onboarding_review_screen.dart` ("Interior care day") | Decision followed. | No | No |
| C-02 | Built | `A:scheduling/service.py` (`build_demand`: interior on the chosen weekday) | Decision followed. | No | No |
| C-03 | Partial | `A:customers/models.py` (`monthly_price_rupees`), `A:directory/models.py` (`Plan`) | Price is stored per subscription. The struck-through list price is not shown anywhere for the plan. | Yes: list price in plan read | No |
| C-04 | Built | `A:changes/cycle.py`, `A:billing/service.py` | Dates come from the backend. | No | No |
| C-05 | Built | `M:features/customer/home/customer_shell.dart` | Tabs match. | No | No |
| C-07 | Partial | `M:features/customer/home/customer_shell.dart` | "Rate today's clean" is missing (HOME-05). | Yes: with HOME-05 | No |
| C-08 | Not built | `M:features/customer/visit/visit_details_screen.dart` | Service Details has no crew card and no star rating (SVC-02, SVC-07). | Yes: with SVC-02 | No |

## Summary by area

195 rows: **86 Built, 68 Partial, 41 Not built**. The `C-` rows are the resolved conflict decisions in section 14 of the requirements file.

| Area | Built | Partial | Not built | Total |
|---|---|---|---|---|
| AUTH | 9 | 7 | 1 | 17 |
| ONB | 11 | 2 | 9 | 22 |
| PAY | 5 | 5 | 3 | 13 |
| HOME | 1 | 6 | 1 | 8 |
| CAL | 2 | 8 | 0 | 10 |
| SVC | 2 | 10 | 2 | 14 |
| HIST | 0 | 2 | 0 | 2 |
| SKIP | 6 | 2 | 0 | 8 |
| PAUSE | 6 | 1 | 0 | 7 |
| SCHED | 1 | 1 | 0 | 2 |
| ACC | 2 | 1 | 4 | 7 |
| SET | 0 | 0 | 4 | 4 |
| NOTIF | 0 | 3 | 3 | 6 |
| SUB | 7 | 2 | 1 | 10 |
| VEH | 3 | 2 | 3 | 8 |
| ADD | 3 | 6 | 6 | 15 |
| SUP | 4 | 1 | 1 | 6 |
| ISS | 4 | 1 | 1 | 6 |
| CMP | 3 | 1 | 0 | 4 |
| FDBK | 6 | 0 | 1 | 7 |
| CHK | 3 | 5 | 0 | 8 |
| NAV | 4 | 0 | 0 | 4 |
| C (decisions) | 4 | 2 | 1 | 7 |
| **All** | **86** | **68** | **41** | **195** |

Where the customer app is solid: sign-in and password rules, the onboarding review, skip, pause and the 9 PM rule, the subscription and UPI payment flow, billing history, complaints, feedback and the check-in screen. Where it is weakest: proof of service (Service Details), notifications and settings, the account and profile area, adding a vehicle, and Deep Spa reaching the scheduler.

## Work packages

Every Partial and Not built ID above is in exactly one package. Sizes: S is under a day, M is one to three days, L is more than three days. The packages are built to run in parallel. Where two share a file the note says so.

### WP1. Sign-in entry and email delivery (S)

IDs: AUTH-01, AUTH-02, AUTH-03, AUTH-05, AUTH-14, AUTH-15, AUTH-16, AUTH-17.

- API: call `EmailSender` from `A:identity/service.py` for the sign-in and reset codes (keep `MOCK_EMAIL_CODE` as the dev override). Send the welcome email when the admin creates a customer. Add an unauthenticated `GET /v1/auth/support-contact` returning the helpline and WhatsApp numbers (for AUTH-15). Add the admin "sign this customer out everywhere" endpoint for AUTH-17.
- App: a Welcome screen with the tagline and the two buttons before the sign-in field (AUTH-01). Email format check with an inline error (AUTH-02). On "not registered", show Call support and WhatsApp support buttons (AUTH-15). Make the Terms and Privacy words real links (AUTH-04 note).
- Depends on: Resend account for real delivery (the fake sender is enough to build and test). AUTH-14 and AUTH-17 need the admin portal's customer create and sign-out actions (`ADM-CUS-01`, `ADM-CUS-21`).
- Touches: `login_screen.dart`, `identity/service.py`.

### WP2. Notifications, settings and scheduled jobs (L)

IDs: NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05, NOTIF-06, SET-01, SET-02, SET-03, SET-04, SKIP-05, CMP-04, CHK-01, CHK-05, ADD-13, SUB-11.

- API: a `notification_preferences` table (all on by default) with `GET` and `PUT /v1/customer/notification-preferences`. One notify helper that checks the preference, writes the inbox row and pushes. Call it from: job completed (`A:visits`), skip and un-skip (`A:changes`), skipped by operations, complaint update (replace the logging fake in `A:support`), renewal reminders, monthly check-in. Reminder rules: 7 days, 1 day, then every 2 days, stop on Initiated or Received or Inactive, restart when the admin moves it back. Cron endpoints guarded by a secret, with `crons` in `services/api/vercel.json`, for `generate_due_payments`, `mark_overdue_and_inactive`, `notify_due_checkins`, the reminders and `alert_overdue_complaints`. Also notify the crew on a customer skip (SKIP-05).
- App: a Settings screen with one switch per event, opened from Account. Firebase init, OS permission request, `registerDevice` after sign-in, tap-through from a push to the visit, the complaint or the check-in (CHK-05).
- Depends on: Firebase account for real push (the logging fake stands in). Needs the scheduling and visits modules unchanged. NOTIF-04 for "skipped by operations" also needs the admin ops-skip flow (admin audit).
- Touches: `account_screen.dart` (shared with WP5), `A:support/service.py`, `A:billing`.

### WP3. Service details, proof and history (L)

IDs: SVC-01, SVC-02, SVC-03, SVC-04, SVC-05, SVC-06, SVC-07, SVC-08, SVC-09, SVC-11, SVC-14, SVC-15, HIST-01, HIST-02, HOME-03, HOME-05, C-07, C-08.

- API: extend `GET /v1/customer/visits/{id}` with, for each job, the crew name, the checklist items with times, and the finish time. Join confirmed `media_uploads` into `proof` with stage, time and a signed read URL (add a read URL method to the `ObjectStore` adapter). Add the rating given to the visit and history item. Check on `PUT /visits/{id}/rating` that the visit is the customer's and Completed. Add month filter and member-since to `/history`. Add a "today" summary (completed time, checks, photo count) for Home.
- App: crew cards (one per job), checklist, gallery with AFTER labels and "View all", captions in the viewer, in-place video with a progress bar. A rating control and a "Report an issue with this clean" button on Service Details. Home banner "Today's clean is done" with "View proof", and a "Rate today's clean" quick action. History grouped by month with paging, finish time and rating.
- Depends on: the media read adapter (dev object store). No account needed.
- Touches: `visit_details_screen.dart`, `history_screen.dart`, `customer_shell.dart` (shared with WP4), `A:customer_reads`.

### WP4. Calendar, Home schedule and change controls (M)

IDs: CAL-01, CAL-02, CAL-05, CAL-06, CAL-07, CAL-08, CAL-09, CAL-10, HOME-01, HOME-04, HOME-08, HOME-09, SKIP-06, PAUSE-02, SCHED-02, SUB-08, CHK-08.

- API: add the assignment (crew name, start and end time) and the covered or rescheduled date to each calendar visit. Project expected future visits from the subscription for months not yet planned. Add `PATCH /v1/customer/vehicles/{id}/preferences` for the default cutoff time and interior day (9 PM rule). Return the cutoff-request state on the calendar read.
- App: outlined interior and Full spa markers on upcoming days. "Change cutoff time" on the day card and "Change requested, awaiting Priveo". "Missed. Covered on" and "Rescheduled on" lines. Crew name and time on the Next service card and the day card (the `/next-job` call already exists). Greeting by time of day. "Monthly check-in" card on Home from `/checkins/pending`. Add-ons card shown only for Active vehicles. "View calendar" link on the skip list. Visits-paused and renewal preview before confirming a pause. A "Call support" message and button when controls are closed. Edit default cutoff and interior day on My subscription.
- Depends on: the scheduling module for covered and rescheduled dates. Nothing from the admin portal.
- Touches: `calendar_screen.dart`, `customer_shell.dart` (shared with WP3), `skip_pause_screen.dart`, `subscription_screen.dart`.

### WP5. Account, profile, vehicle photo and customer uploads (L)

IDs: ACC-01, ACC-02, ACC-03, ACC-06, ACC-08, VEH-01, VEH-03, VEH-04, ONB-22, ONB-26, HOME-02, ISS-02, ISS-04.

- API: customer upload endpoints on the media module (purposes `vehicle_photo` and `complaint`, with the 10 MB photo rule and HEIC accepted) plus read URLs. A photo and RC status field on the vehicle, returned on home and vehicle reads. `PATCH /v1/customer/profile` for names and mobile, and an email-change flow (code to the new email, duplicate check, old email stays until verified). `PATCH /v1/customer/vehicles/{id}` for parking and photo only. A complaint visit selector read (the customer's recent visits) and an ownership check on `visit_id`.
- App: a rebuilt Account screen with the avatar, name and mobile, tappable to Edit profile, one subscription card per vehicle, and the full menu (calendar, vehicles, add-ons, skip or pause, history, complaints, help, settings, sign out). Edit profile and email change screens. Vehicle photo capture or pick (also in the onboarding review), "Change photo", edit parking, RC status. Photo picker and visit selector on Report an issue. Photo and variant on the Home vehicle card.
- Depends on: Resend for the email-change code (WP1). Settings entry from WP2. Photo upload is needed by WP6.
- Touches: `account_screen.dart` (shared with WP2), `vehicles_screen.dart`, `onboarding_review_screen.dart`, `report_issue_screen.dart`, `A:media`, `A:customers`.

### WP6. Add a vehicle, plan choice and first payment (L)

IDs: VEH-07, VEH-09, ONB-03, ONB-04, ONB-05, ONB-07, ONB-09, ONB-10, ONB-11, ONB-12, ONB-23, PAY-01, PAY-02, PAY-03, PAY-04, PAY-05, PAY-11, PAY-12, PAY-13, C-03.

- API: read endpoints for serviced societies (with sector, city, cars serviced), the make, model and variant catalog with category mapping, and active plans (name, price, list price, inclusions). `POST /v1/customer/vehicles` to create a vehicle and an Activating subscription with its first payment. Move the society to the vehicle (migration) so vehicles of one customer can be in different societies, fixed once added. Return the first payment on the onboarding read.
- App: an Add vehicle flow with the onboarding steps (society with search, vehicle with dropdowns and auto category, photo, parking, plan, preferences, review). In the onboarding review: plan card with list price, "Founding member", "Cancel anytime", inclusions, total payable, "Priveo will confirm the start date", and "Confirm & pay" opening the existing UPI screen when the first payment is Due or Over due (otherwise its status).
- Depends on: the admin portal for the data these read (`ADM-REF` for societies and vehicles, `ADM-SET-01` for plans), and WP5 for the vehicle photo upload. The UPI screen exists.
- Touches: `onboarding_review_screen.dart` (shared with WP5), `vehicles_screen.dart`, `A:customers`, `A:directory`.

### WP7. Deep Spa lifecycle (M)

IDs: ADD-01, ADD-02, ADD-06, ADD-07, ADD-08, ADD-09, ADD-10, ADD-11, ADD-12, ADD-14, ADD-15.

- API: make the scheduler plan `addon_bookings` (change `build_demand` in `A:scheduling/service.py`, or copy a booking into `addon_requests`), with its finish-by time. Put an unfittable booking in the Needs scheduling list. Keep the booking status in step with the job (Scheduled, Completed, Missed). Treat a date or time change after a freeze as a request. Read the add-on offers from an admin-managed table (`ADM-ADD-01`) instead of `MONEY_*` settings. Decide ADD-15 (owner) and extend the standalone path to match.
- App: change date and time on a request, "Change requested, awaiting Priveo", the "Call support" message after the cutoff, hide add-on screens for a vehicle that is not Active (Home tile and Account item), Full spa marker and proof for the add-on job (uses WP3 and WP4 views).
- Depends on: the scheduling module owner (this changes the scheduler's demand input), the admin portal's add-on offers and Needs scheduling list, and an owner decision for ADD-15. ADD-13 is in WP2.
- Touches: `A:scheduling`, `A:addons`, `addon_screen.dart`.

### WP8. Feedback tab, FAQ, check-in categories and invoice save (S)

IDs: FDBK-01, SUP-01, SUP-05, CHK-02, CHK-03, SUB-12.

- API: seed the six check-in categories with the owner's descriptions (`A:support/defaults.py`), and add the missing three for existing databases through a data migration or a reseed step.
- App: the side feedback tab on the right edge of every customer screen after onboarding, draggable along the edge and not hideable (an overlay in the customer shell). A FAQ screen that reads a Markdown asset, listed on Support (SUP-01). Save or share the invoice (PDF or share sheet) from billing history.
- Depends on: FAQ content from Priveo. Nothing else.
- Touches: `customer_shell.dart` (shared with WP3 and WP4), `help_screen.dart`, `billing_history_screen.dart`.

### Order and conflicts

- Start now, no prerequisites: WP1, WP3, WP4, WP8, and the API half of WP2.
- WP5 should land before WP6 (vehicle photo upload). WP1 should land before the email-change part of WP5.
- WP7 needs a decision on how the scheduler reads bookings before it starts.
- Files several packages edit: `customer_shell.dart` (WP2 push tap, WP3, WP4, WP8), `account_screen.dart` (WP2, WP5), `onboarding_review_screen.dart` (WP5, WP6). Agree one owner per file or merge in the order above.
- The coordinator-owned files (`main.py`, `models.py`, `openapi.json`, `api.g.dart`, `app_en.arb`, `router.dart`) will need changes from WP1, WP2, WP5 and WP6.

### Not buildable inside the customer slice

- Real Resend, FCM, UPI ID and QR image, support numbers and FAQ text are owner or account items. Each is behind an adapter or a `MONEY_*` or `SUPPORT_*` setting today.
- The admin-side data these screens read (customers, vehicles, societies, plans, add-on offers, ops skip, sign-out) belongs to the admin portal audit.

