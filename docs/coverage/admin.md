# Admin requirements: coverage audit

**Historical audit:** the verdicts and totals below predate the React portal and later backend integration. Customer administration, add-on management and scheduling actions now exist; the operations portal remains a subsequent milestone. See [the current handoff](../codex-handoff-plan.md) for verification; these counts are not current completion metrics.

Source: `docs/reqs/admin-functional-requirements.md` (v0.8), all 172 `ADM-` IDs.
Audited against the code on `integration/complete-build` (commit e3f91b7) by reading `services/api/app`, `services/api/tests` and `apps/mobile/lib/features/admin_quick`. `docs/feature-status.json` and `docs/overnight-build-report.md` were not used as evidence.

## How to read this

- **API verdict**: does the endpoint or rule exist in `services/api`, and is it exercised by a test? Built = exists and tested. Partial = exists, but a part of the requirement is missing, or it has no test or trigger. Not built = nothing usable.
- **UI verdict**: does the screen exist? The React portal (`apps/web`) does not exist, so portal-only functions are Not built. Mobile quick actions (ADM-ACC-07) are in `apps/mobile/lib/features/admin_quick`. `n/a` means the ID is a rule or data statement with no admin screen of its own.
- Paths: `api:` is `services/api/app/`, `t:` is `services/api/tests/`, `m:` is `apps/mobile/lib/features/admin_quick/`.
- "Needs account/stub?" names the outside account or adapter the item depends on. Email (Resend), push (FCM) and media (S3) run on logging or dev fakes today.

## Headline

- 172 IDs. API: 65 Built, 53 Partial, 54 Not built. UI: 2 Built, 13 Partial, 115 Not built, 42 n/a.
- The mobile admin app covers only: the alert list, confirm or reject a payment, payment alerts, and sign out of all devices. Its admin home still shows mock data from `GET /v1/admin/home`.
- The backend is strongest in payments, subscription status, scheduling (run, board, move, freeze), complaints and feedback options.
- No endpoint exists at all for: customers (create, search, view, edit, sessions, notification switches), vehicles and the catalogue, societies, plans, working slots, checklists, could-not-complete reasons, preferences, skip by operations, Missed outcomes, audit views.

## Defects found that change several IDs

1. **Crew onboarding and the scheduler are disconnected.** `POST /v1/admin/crew` writes `crew_members`. The scheduler reads `scheduling_crew` (another table, one daily window, same on every day). Nothing creates a `scheduling_crew` row from a crew member, so a crew member onboarded through the API is never scheduled. Tests create `scheduling_crew` rows directly. Affects ADM-CRW-01, -04, -14, -19, ADM-CAP-05, ADM-SCH-04.
2. **New add-on requests are not planned.** `AddonService` writes `addon_bookings` (with finish-by). The scheduler reads `addon_requests` (the migrated history table, with no finish-by). Affects ADM-SVS-10, ADM-SCH-03, -30, -31, ADM-ADD-03, -08.
3. **Skips and pauses are not honoured at demand time.** They change visits already planned (`changes/sql_gateway.py`). `build_demand` and `capacity` do not read `schedule_changes`, so a skip or pause made before a run is ignored, and capacity demand counts those days. Affects ADM-CAP-03, ADM-SCH-04.
4. **Checklists, proof minimums and could-not-complete reasons are code constants** in `visits/service.py`. The job checklist progress stores only the item key, so a rename would rewrite history (ADM-CHK-05).
5. **Admin alerts are mostly never raised.** Only new complaint, complaint reply, complaint overdue, payment initiated and auto-inactive create an alert. Skip or pause after freeze, cutoff request, add-on change after freeze, Missed job, auto-assigned visit and needs-scheduling raise nothing. Push and email are logging fakes, and the daily jobs have no HTTP or cron trigger.
6. **Plans are never seeded.** `plans` exists, but there is no row for Premium Care and no endpoint.
7. **Default working window is 6 AM to 11 AM** (`scheduling_crew.start_minute` 360), the requirement says 5 AM to 11 AM (ADM-SVS-05).

## Coverage table

| ID | API verdict | UI verdict | Evidence (files) | Missing / notes | Needs account/stub? |
|---|---|---|---|---|---|
| ADM-ACC-01 | Partial | Partial | api:*/router.py (admin routers); m: | Many admin functions have no endpoint yet (customers, societies, plans, slots, catalogue). Mobile quick actions exist; the portal does not. | No |
| ADM-ACC-02 | Built | Partial | api:platform/deps.py require_role; t:test_api.py test_role_is_enforced; t:scheduling/test_scheduling_api.py test_scheduling_endpoints_are_for_their_role | Mobile router redirects by role. Portal route guard not built. | No |
| ADM-ACC-03 | Built | n/a | api:crew/models.py (CHECK role in Manager, Member, Trainee); api:scheduling/models.py CREW_ROLES | Role cannot be changed after onboarding (see ADM-CRW-03). | No |
| ADM-ACC-04 | Built | Partial | api:identity/models.py (role customer, crew, admin); api:platform/deps.py; apps/mobile router.dart role redirect | Portal not built. | No |
| ADM-ACC-05 | Built | Built | api:identity/seed.py; t:test_api.py test_seeding_again_unlocks_the_admin; test_login_and_home[admin] | None. Admin signs in on the mobile sign-in screen. | Owner supplies ADMIN_PASSWORD env |
| ADM-ACC-06 | Partial | Not built | api:identity/service.py login() (user ID and password, lock after 5 wrong); t:test_api.py test_five_wrong_passwords_lock_crew_and_admin | No web login route (channel is never set to web). No HttpOnly cookie, no CSRF. | No (same origin on Vercel) |
| ADM-ACC-07 | Partial | Partial | api:billing/router.py (payments confirm/reject); api:support/router.py (alerts, complaints, feedback); api:changes/router.py admin skips/pauses; api:scheduling/router.py (board, needs-scheduling, capacity); m:alerts, m:payments, m:home | Mobile has only: alerts list, payments to confirm/reject, payment alerts, sign out of all devices. Missing in the app: (c) needs-scheduling list and day schedule, (d) skip by operations and Missed outcome (no admin API either), (e) skip/pause on behalf, (f) customer search, complaints, feedback, check-ins, capacity, crew list, add-on requests. Push device registration is customer-only. | FCM for push |
| ADM-ACC-08 | Partial | Not built | (scope list) | Most web-only functions lack an API (customers, vehicles, crew edits, services and slots, preferences, reference data, settings, audit views). See the rows below. | No |
| ADM-ACC-09 | Partial | Partial | api:support/alerts.py raise_alert, unread_count; api:support/router.py GET /v1/admin/alerts; api:billing/models.py MoneyAlert; m:alerts; t:support/test_support.py test_alert_list_and_read_state, test_a_failing_notifier_does_not_lose_the_alert | Bell list and unread count exist. Push and email go to logging fakes. No switch to turn emails off. Two alert lists (admin_alerts and money_alerts) are not merged. Admin cannot register a device token. Most alert kinds are never raised (see ADM-SCH-24). | Resend (email), FCM (push) |
| ADM-ACC-10 | Built | n/a | api: one backend for app and portal; api:changes/service.py Actor('admin') | None. | No |
| ADM-ACC-11 | Built | n/a | (statement) | None. | No |
| ADM-ACC-12 | Not built | Not built | - | No cookie session, no CSRF, no 60-minute web idle rule (api:identity/service.py only has ADMIN_MOBILE_IDLE of 24 h for the mobile channel). | No |
| ADM-ACC-13 | Built | Built | api:identity/service.py ADMIN_MOBILE_IDLE, _live(); t:test_api.py test_admin_phone_signs_out_after_24_idle_hours, test_logout_ends_the_session_at_once | None. | No |
| ADM-ACC-14 | Built | Partial | api:identity/router.py POST /v1/admin/sessions/logout-all; t:test_api.py test_admin_signs_out_of_all_devices; m:home/admin_home_screen.dart | Action exists in the app. Portal button not built. | No |
| ADM-CUS-01 | Not built | Not built | api:customers/models.py (tables exist); api:customers/importer.py (one-time load only) | No admin create-customer endpoint (customer, vehicle, parking, plan, cutoff, interior day). | No |
| ADM-CUS-02 | Not built | Not built | - | Validation for the admin form is not written (the crew module has its own checks). | No |
| ADM-CUS-03 | Partial | Not built | api:customers/models.py Customer.email unique; api:identity unique login_id | Unique at the database only. No create flow, so no 'open the existing customer' behaviour. | No |
| ADM-CUS-04 | Partial | Not built | api:platform/email.py send_welcome (adapter and fake); t:crew/test_email.py test_fake_sender_welcome_has_no_code | Adapter exists. Nothing calls it, because there is no create flow. | Resend (email adapter fake) |
| ADM-CUS-05 | Not built | Not built | - | No add-vehicle endpoint. | No |
| ADM-CUS-06 | Partial | Not built | api:billing/router.py POST /v1/admin/payments (status can be set on create) | Not tied to onboarding; no onboarding flow. | No |
| ADM-CUS-07 | Not built | Not built | api:media/models.py PURPOSES = proof, reason, profile only | No vehicle photo field or upload purpose; no admin upload. | S3 / dev ObjectStore |
| ADM-CUS-08 | Not built | Not built | - | No customer list, search or detail endpoint for the admin. | No |
| ADM-CUS-09 | Partial | Not built | api:changes/router.py admin skips, un-skip, pauses, end pause (not bound by 9 PM); t:changes/test_changes.py test_the_admin_is_not_bound_by_9pm_but_not_by_the_past | Plan change, default cutoff time, interior care day and per-date cutoff on behalf of a customer are missing. Skip/pause have no portal or app screen. | No |
| ADM-CUS-10 | Built | n/a | api:changes/service.py (same service for both actors, last write wins) | None. | No |
| ADM-CUS-11 | Built | n/a | api:changes/rules.py require_open(bound=...); t:changes/test_changes.py test_the_admin_is_not_bound_by_9pm_but_not_by_the_past | None. | No |
| ADM-CUS-12 | Not built | Not built | - | No customer notification-switch table or endpoint (not on the customer side either). | No |
| ADM-CUS-13 | Not built | Not built | - | Depends on ADM-CUS-12. | No |
| ADM-CUS-14 | Built | n/a | api:changes/service.py (no notification sent on admin change) | None. | No |
| ADM-CUS-15 | Not built | Not built | api:customers/models.py Subscription.plan_id | No plan change; no pending plan or effective-from date on the subscription. | No |
| ADM-CUS-16 | Partial | Not built | api:changes/models.py ScheduleChange.actor, actor_login_id; api:billing/models.py PaymentEvent, SubscriptionEvent; api:scheduling/models.py SchedulingEvent | No general audit table. No audit for customer, vehicle or notification-switch edits (those edits do not exist). | No |
| ADM-CUS-17 | Not built | Not built | api:identity/models.py Login.password_hash; api:customers/models.py terms_accepted_at, onboarding_confirmed_at (data exists) | No admin read endpoint for onboarding state. | No |
| ADM-CUS-18 | Not built | Not built | api:platform/email.py send_welcome | No resend endpoint. | Resend |
| ADM-CUS-19 | Not built | Not built | - | No email-correction endpoint (clear password, end sessions, new welcome). | Resend |
| ADM-CUS-20 | Not built | Not built | api:identity/service.py (code flow for a customer with no password exists) | No admin reset endpoint that clears the password and ends sessions. | No |
| ADM-CUS-21 | Not built | Not built | api:identity/models.py AuthSession (channel, last_used_at) | No list or per-session sign-out for customers. AuthSession has no device name, platform or app version columns. | No |
| ADM-SUB-01 | Partial | Not built | api:billing/router.py PUT /v1/admin/subscriptions/{id}/status; api:billing/service.py set_subscription_status; t:billing/test_billing.py test_subscription_status_by_the_admin | Activating to Active with a first service date works. A new subscription is not created as Activating (no create flow; default status is Active). | No |
| ADM-SUB-02 | Partial | Not built | api:billing/service.py set_subscription_status; api:scheduling/service.py build_demand (Active only); t:scheduling/test_scheduling_api.py test_inactive_and_trainee_do_not_count | Future visits are removed only at the next scheduler run, not at once. 'Cars serviced' figure not built (ADM-REF-02). | No |
| ADM-SUB-03 | Partial | Partial | api:billing/service.py mark_overdue, mark_overdue_and_inactive; t:billing/test_billing.py test_over_due_then_inactive_after_seven_days, test_an_over_due_add_on_payment_does_not_make_the_subscription_inactive; m:payments (payment alerts) | No HTTP or cron trigger for the daily job. The alert goes to money_alerts only, no push or email. | Vercel cron + secret |
| ADM-SUB-04 | Built | Not built | api:billing/service.py set_subscription_status (Inactive to Activating to Active); t:billing/test_billing.py test_subscription_status_by_the_admin | None on the API. | No |
| ADM-SUB-05 | Built | Not built | api:billing/models.py SubscriptionEvent (by_login_id, reason, time) | No view of the history for the admin. | No |
| ADM-CRW-01 | Built | Not built | api:crew/router.py POST /v1/admin/crew; t:crew/test_crew.py test_admin_creates_crew_and_the_password_works_once_shown | Onboarding does not create the scheduler's crew row (see Reference data note on scheduling_crew). | No |
| ADM-CRW-02 | Built | Not built | api:crew/service.py NewCrew, create; t:crew/test_crew.py test_checks_on_the_new_crew_member | None. | No |
| ADM-CRW-03 | Not built | Not built | - | No role-change endpoint. | No |
| ADM-CRW-04 | Built | Not built | api:crew/service.py check_hours (7 days, start before end); api:crew/models.py working_hours JSON | The scheduler ignores these per-day hours (it uses one daily window in scheduling_crew). | No |
| ADM-CRW-05 | Not built | Not built | - | No working-hours edit endpoint (admin or Manager). | No |
| ADM-CRW-06 | Built | n/a | api:crew/service.py (409 mobile_in_use); t:crew/test_crew.py test_a_mobile_number_belongs_to_one_login | None. | No |
| ADM-CRW-07 | Partial | Not built | api:crew/router.py GET /v1/admin/crew?society_id= | No search. No upcoming exceptions or pairing in the output. | No |
| ADM-CRW-08 | Not built | Not built | api:scheduling/models.py SchedulingCrewException (table exists, one row for each date) | No create endpoint. Tests insert rows directly. | No |
| ADM-CRW-09 | Built | n/a | api:scheduling/rules.py window_for (Sick, Leave, Late start); t:scheduling/test_rules.py test_trainees_and_absent_crew_add_no_capacity; t:scheduling/test_scheduling_api.py test_a_crew_exception_removes_that_days_capacity | None. | No |
| ADM-CRW-10 | Not built | Not built | - | No edit or remove endpoint. | No |
| ADM-CRW-11 | Partial | Not built | api:scheduling/service.py capacity() (computed on read) | Capacity is live, but there is no exception save to trigger it. | No |
| ADM-CRW-12 | Partial | Not built | api:scheduling/service.py run_schedule (jobs of an absent crew member go back to the pool) | No 'affected visits' list at save time. Pool return happens only on a run. | No |
| ADM-CRW-13 | Built | n/a | api:crew/models.py society_id; no move endpoint | None. | No |
| ADM-CRW-14 | Built | n/a | api:scheduling/rules.py window_for (Trainee returns None); t:scheduling/test_solver.py; t:scheduling/test_scheduling_api.py test_inactive_and_trainee_do_not_count | None. | No |
| ADM-CRW-15 | Not built | Not built | api:identity/models.py Login.active; api:scheduling/models.py SchedulingCrew.active (columns exist) | No deactivate endpoint. Tests flip the flag in the database. Sessions are not ended on deactivation. | No |
| ADM-CRW-16 | Built | Not built | api:crew/service.py (no limit on Managers) | None. | No |
| ADM-CRW-17 | Built | Not built | api:crew/service.py generate_password, create; t:crew/test_crew.py test_password_format, test_admin_creates_crew_and_the_password_works_once_shown | None on the API. | No |
| ADM-CRW-18 | Built | Not built | api:crew/router.py POST /{id}/password, /{id}/unlock; t:crew/test_crew.py test_reset_gives_a_new_password_and_signs_the_phone_out, test_a_locked_login_is_unlocked_by_reset_and_by_unlock | None on the API. | No |
| ADM-CRW-19 | Partial | Not built | api:scheduling/models.py SchedulingCrew.paired_member_id; t:scheduling/test_scheduling_api.py test_a_trainee_sees_the_paired_members_jobs; t:visits/test_manager.py test_reassign_moves_the_job_and_follows_the_trainee | Pairing is read but cannot be set or changed by the admin, and the rules (same society, fix before role change) are not enforced. | No |
| ADM-CRW-20 | Partial | Not built | api:visits/router.py /v1/crew/manager/* (schedule, could-not-complete, skip, reassign); api:visits/models.py JobOutcome, JobReassignment; t:visits/test_manager.py | No Manager exceptions or working-hours edit (CRW-MGR-05). Actions are stored with the login ID, no combined audit view. | No |
| ADM-CRW-21 | Not built | Not built | api:crew/service.py reset_password ends sessions (partial) | No session list or per-session sign-out. Deactivation does not end sessions (no deactivation). | No |
| ADM-SVS-01 | Built | n/a | api:scheduling/models.py SERVICES; api:scheduling/service.py build_demand (separate jobs); t:scheduling/test_scheduling_api.py test_interior_day_and_deep_spa_are_jobs_of_their_own | None. | No |
| ADM-SVS-02 | Not built | Not built | - | No working_slots table or endpoint. | No |
| ADM-SVS-03 | Not built | Not built | - | As ADM-SVS-02. | No |
| ADM-SVS-04 | Not built | Not built | - | As ADM-SVS-02. | No |
| ADM-SVS-05 | Not built | Not built | api:scheduling/models.py SchedulingCrew start_minute 360, end_minute 660 (6 AM to 11 AM) | No default slots. The only window is the crew member's own hours, and the default is 6 AM to 11 AM, not 5 AM to 11 AM. | No |
| ADM-SVS-06 | Not built | Not built | - | No slots, so no society default. | No |
| ADM-SVS-07 | Not built | Not built | - | No slots, so no overlap check. | No |
| ADM-SVS-08 | Not built | Not built | - | No slots. | No |
| ADM-SVS-09 | Built | n/a | api:scheduling/models.py DURATIONS (20, 20, 120) | Constants in code, not editable (the requirement says fixed for now). | No |
| ADM-SVS-10 | Partial | n/a | api:scheduling/service.py build_demand; t:scheduling/test_scheduling_api.py test_interior_day_and_deep_spa_are_jobs_of_their_own | A Deep Spa is planned only from the old addon_requests table (migrated rows). New add-on requests (addon_bookings, with finish-by) are never planned, and finish-by is not read. | No |
| ADM-CAP-01 | Built | Not built | api:scheduling/router.py GET /v1/admin/scheduling/capacity; api:scheduling/service.py capacity; t:scheduling/test_scheduling_api.py test_a_run_makes_a_draft_and_respects_capacity | Mobile 'view capacity' not built. | No |
| ADM-CAP-02 | Built | n/a | api:scheduling/rules.py window_for; t:scheduling/test_rules.py test_trainees_and_absent_crew_add_no_capacity | None. | No |
| ADM-CAP-03 | Partial | Not built | api:scheduling/service.py capacity (demand_minutes, scheduled_minutes) | Demand ignores skips and pauses (only Active subscriptions count). Skips and pauses made before a run are not honoured in demand. | No |
| ADM-CAP-04 | Built | Not built | api:scheduling/service.py capacity over_capacity flag | None on the API. | No |
| ADM-CAP-05 | Partial | Not built | api:scheduling/service.py capacity (computed on each read) | Crew rows from onboarding are not in the scheduler, and exceptions cannot be saved by API. | No |
| ADM-PAY-01 | Built | Partial | api:billing/router.py GET /v1/admin/payments (status, kind, customer_id, vehicle_id, due_before, due_after); m:payments (status=Initiated list) | No society filter. Mobile shows only the Initiated list. | No |
| ADM-PAY-02 | Built | Partial | api:billing/router.py PUT /v1/admin/payments/{id}/status; t:billing/test_billing.py test_a_payment_runs_from_due_to_received; m:payments confirm/reject | Mobile can only confirm or reject, not choose any status. | No |
| ADM-PAY-03 | Built | Partial | api:billing/service.py confirm, _apply; m:payments | Portal not built. | No |
| ADM-PAY-04 | Built | Not built | api:billing/router.py POST /v1/admin/payments; t:billing/test_billing.py test_the_admin_can_record_an_offline_payment | None on the API. | No |
| ADM-PAY-05 | Built | n/a | api:billing/models.py PaymentEvent (by_login_id, at, note) | None. | No |
| ADM-PAY-06 | Partial | n/a | api:billing/service.py generate_due_payments, mark_overdue; t:billing/test_billing.py test_the_next_payment_opens_one_week_before_renewal, test_the_daily_job_creates_the_next_payment_and_follows_a_pause | No HTTP or cron trigger for the daily jobs. | Vercel cron + secret |
| ADM-PAY-07 | Built | Partial | api:billing/service.py set_status, reject; t:billing/test_billing.py test_the_admin_can_reject_and_move_back; m:payments reject | Mobile reject only (to Due or Over due). Portal not built. | No |
| ADM-PAY-08 | Built | Not built | api:billing/router.py POST /v1/admin/payments/{id}/invoice; t:billing/test_billing.py test_invoice_number_and_the_customers_copy | Seller name, address and GSTIN come from env at read time and are not saved on the invoice. | Owner values (seller, GSTIN) |
| ADM-PAY-09 | Built | n/a | api:billing/service.py issue_invoice; t:billing/test_billing.py test_invoice_number_and_the_customers_copy | None. | No |
| ADM-PAY-10 | Built | Not built | api:billing/models.py Payment.kind; kind filter on GET /v1/admin/payments; t:billing/test_billing.py test_an_over_due_add_on_payment_does_not_make_the_subscription_inactive | None on the API. | No |
| ADM-PAY-11 | Partial | Partial | api:billing/service.py mark_paid -> _alert('payment_initiated'); m:payments payment alerts | Stored in money_alerts only, no push or email. | FCM, Resend |
| ADM-SCH-01 | Built | Not built | api:scheduling/router.py POST /v1/admin/scheduling/run; api:scheduling/service.py run; t:scheduling/test_scheduling_api.py test_a_run_makes_a_draft_and_respects_capacity | None on the API. | No |
| ADM-SCH-02 | Built | n/a | api:scheduling/service.py load_crew, build_demand (by society); t:scheduling/test_scheduling_api.py | None. | No |
| ADM-SCH-03 | Built | n/a | api:scheduling/service.py build_demand; t:scheduling/test_scheduling_api.py test_interior_day_and_deep_spa_are_jobs_of_their_own | Deep Spa source is wrong (see ADM-SVS-10). | No |
| ADM-SCH-04 | Partial | n/a | api:scheduling/service.py build_demand, availability | Uses cutoff, interior day, crew windows, exceptions. Does not use skips and pauses at demand time, new add-on bookings, working slots or per-day working hours. | No |
| ADM-SCH-05 | Built | n/a | api:scheduling/solver.py solve_day; t:scheduling/test_solver.py | None. | No |
| ADM-SCH-06 | Built | Not built | api:scheduling/service.py run_schedule; api:scheduling/schemas.py Board | None on the API. | No |
| ADM-SCH-07 | Built | Not built | api:scheduling/models.py Job.late; t:scheduling/test_solver.py test_a_job_that_misses_its_cutoff_is_placed_and_flagged_late | None on the API. | No |
| ADM-SCH-08 | Built | Not built | api:scheduling/router.py GET /needs-scheduling; Job.note holds the reason | None on the API. | No |
| ADM-SCH-09 | Partial | Not built | api:scheduling/schemas.py RunRequest days (default 7, 1 to 31) | No Daily/Weekly/Monthly preference. Week start (Sunday) is not enforced; any start date is accepted. | No |
| ADM-SCH-10 | Built | n/a | api:customer_reads (calendar); see the customer audit | Not re-checked in depth here. | No |
| ADM-SCH-11 | Built | Not built | api:scheduling/models.py Schedule.status | None on the API. | No |
| ADM-SCH-12 | Built | Not built | api:scheduling/router.py GET /board (date, crew, vehicle, customer in each job) | Grouping by day/crew/customer is left to the client. No server filters. | No |
| ADM-SCH-13 | Partial | Not built | api:scheduling/router.py POST /jobs/{id}/move (move, assign, take off); t:scheduling/test_scheduling_api.py test_a_manual_change_survives_a_rerun, test_a_move_that_overlaps_or_leaves_the_hours_is_refused | No swap of two visits. | No |
| ADM-SCH-14 | Built | Not built | api:scheduling/service.py run_schedule (manual flag kept); t:scheduling/test_scheduling_api.py test_a_manual_change_survives_a_rerun | None on the API. | No |
| ADM-SCH-15 | Not built | Not built | - | No suggestions. | No |
| ADM-SCH-16 | Built | Not built | api:scheduling/router.py POST /schedules/{id}/freeze; t:scheduling/test_scheduling_api.py test_freeze_and_unfreeze_with_the_code | None on the API. | No |
| ADM-SCH-17 | Built | Not built | api:scheduling/service.py move_job, unfreeze; t:scheduling/test_scheduling_api.py test_freeze_and_unfreeze_with_the_code | None on the API. | No |
| ADM-SCH-18 | Built | n/a | api:scheduling/rules.py UNFREEZE_CODE; t:scheduling/test_scheduling_api.py test_freeze_and_unfreeze_with_the_code | None. | No |
| ADM-SCH-19 | Built | Not built | api:scheduling/models.py SchedulingEvent (admin_login_id, kind, at) | No endpoint to read the events. | No |
| ADM-SCH-20 | Built | n/a | api:scheduling/router.py GET /v1/crew/day, GET /v1/customer/next-job; t:scheduling/test_scheduling_api.py test_the_crew_day_shows_only_frozen_work_and_no_customer_details, test_next_service_for_the_customer | UI is in the crew and customer apps. | No |
| ADM-SCH-21 | Partial | n/a | api:changes/sql_gateway.py skip_day, pause_range (open jobs set to Skipped on a frozen schedule); t:changes/test_changes.py | No admin alert raised. | FCM, Resend |
| ADM-SCH-22 | Partial | Not built | api:changes/service.py change_cutoff (status Requested when frozen); t:changes/test_changes.py test_cutoff_time_change_is_applied_or_requested_when_frozen | No alert. No list of open requests. No handled-by and handled-at. | FCM, Resend |
| ADM-SCH-23 | Partial | Not built | api:scheduling/router.py run, move, freeze | Tools exist. No request list and no way to mark a request handled. | No |
| ADM-SCH-24 | Partial | Partial | api:support/service.py (complaint raised, reply, overdue alerts); api:billing/service.py (payment_initiated, auto_inactive); m:alerts | Raised: new complaint, complaint overdue, payment initiated, auto inactive. Never raised: skip or pause after freeze, cutoff request, add-on cancel or change after freeze, Missed job, auto-assigned visit, needs scheduling. | FCM, Resend |
| ADM-SCH-25 | Partial | n/a | api:scheduling/rules.py freeze_deadline; api:scheduling/service.py freeze_due; POST /freeze-due; t:scheduling/test_scheduling_api.py test_the_freeze_cutoff_time_freezes_drafts | Function and manual endpoint exist. No cron trigger. | Vercel cron + secret |
| ADM-SCH-26 | Not built | Not built | - | No redo of a Missed job for the next day. | No |
| ADM-SCH-27 | Partial | Not built | api:scheduling/service.py run_schedule (frozen: places only jobs without a crew member); t:scheduling/test_scheduling_api.py test_a_late_visit_is_placed_on_a_frozen_schedule_without_moving_others | Runs only when the admin calls run. No automatic trigger on un-skip, ended pause, new vehicle or reactivation. No admin alert and no crew push. | FCM, Resend |
| ADM-SCH-28 | Partial | Not built | api:scheduling/router.py GET /needs-scheduling | List exists. No alert. | FCM, Resend |
| ADM-SCH-29 | Partial | n/a | api:scheduling/service.py move_job (take off needs no code), run_schedule; t:scheduling/test_scheduling_api.py test_removing_from_a_frozen_schedule_needs_no_code | Exceptions, deactivation and skip by operations do not move work by themselves (exceptions and deactivation have no API; skip by operations is missing). | No |
| ADM-SCH-30 | Partial | n/a | api:scheduling/service.py build_demand (addon_requests) | Add-on bookings (addon_bookings) are not read, and finish-by is not used. | No |
| ADM-SCH-31 | Not built | Not built | api:addons/service.py _cancel (voids payment only) | Cancel does not remove the job. No admin notice. A changed date or finish-by is not saved as a request. | No |
| ADM-PRF-01 | Not built | Not built | api:scheduling/schemas.py RunRequest.days only | No preferences table, endpoint or screen. | No |
| ADM-CMP-01 | Partial | Not built | api:support/router.py GET /v1/admin/complaints (status, category); t:support/test_support.py test_admin_filters_complaints | No society filter, no vehicle in the row, no pagination. | No |
| ADM-CMP-02 | Partial | Not built | api:support/router.py GET /v1/admin/complaints/{id} (description, photo_keys, visit_id) | Photos are storage keys only, with no signed URL. The linked visit is a plain string with no detail. | S3 / dev ObjectStore |
| ADM-CMP-03 | Built | Not built | api:support/router.py POST /complaints/{id}/status; t:support/test_support.py test_complaint_goes_from_customer_to_admin_and_back | None on the API. | No |
| ADM-CMP-04 | Built | Not built | api:support/router.py POST /complaints/{id}/notes | None on the API. | No |
| ADM-CMP-05 | Partial | n/a | api:support/service.py admin_update, _push_customer; t:support/test_support.py test_a_status_change_without_a_change_sends_nothing | Push goes to a logging notifier. It is not stored in the customer inbox and the 'switched on' setting is not checked. | FCM |
| ADM-CMP-06 | Built | Not built | api:support/service.py _admin_summary overdue flag; t:support/test_support.py test_overdue_complaint_is_highlighted_and_alerted_once | None on the API. | No |
| ADM-CMP-07 | Built | n/a | api:support/models.py ComplaintUpdate.author_login_id, created_at | None. | No |
| ADM-CMP-08 | Partial | n/a | api:support/service.py create_complaint, alert_overdue_complaints; t:support/test_support.py test_overdue_complaint_is_highlighted_and_alerted_once | No cron trigger for the 4-hour alert. Push and email are fakes. | Vercel cron + secret, FCM, Resend |
| ADM-OPS-01 | Not built | Not built | api:visits/service.py manager_skip (Manager, crew role only) | No admin endpoint. No 'Service skipped' customer notification. | FCM |
| ADM-OPS-02 | Not built | Not built | api:visits/models.py JobOutcome.reason_key (manager skip stores none) | No reason on admin skip. | No |
| ADM-OPS-03 | Not built | Not built | api:visits/service.py manager_skip docstring says plan extension belongs to another module | No plan extension, no renewal shift for a skipped Cleaning-External. | No |
| ADM-CNC-01 | Not built | Not built | api:visits/service.py REASONS (code constant) | No reasons table or admin endpoints. | No |
| ADM-CNC-02 | Not built | Not built | api:visits/models.py JobOutcome (data exists); api:customer_reads (shows Missed to the customer) | No admin list of Missed jobs or filters. | S3 / dev ObjectStore (photo) |
| ADM-CNC-03 | Not built | Not built | - | No admin outcome choice (schedule again for next day, or skip by operations). | No |
| ADM-CNC-04 | Not built | Not built | - | No Missed alert. | FCM, Resend |
| ADM-CNC-05 | Not built | Not built | - | No outcome record. | No |
| ADM-CNC-06 | Not built | Not built | - | No redo placement (see ADM-SCH-26). | No |
| ADM-FDB-01 | Partial | Not built | api:support/router.py GET /v1/admin/feedback (category, rating); t:support/test_support.py test_feedback_needs_a_rating_or_a_comment | No society or date filter. | No |
| ADM-FDB-02 | Partial | Not built | api:support/router.py GET /v1/admin/ratings; t:support/test_support.py test_visit_rating_tags_follow_the_stars | No filters (society, date). | No |
| ADM-FDB-03 | Partial | Not built | api:support/service.py ratings_for_admin (average, tag_counts) | Overall only, not by society or period. | No |
| ADM-FDB-04 | Partial | Not built | api:support/router.py GET /v1/admin/checkins; t:support/test_support.py test_checkin_is_due_in_the_last_four_days_and_saved_once | Averages are overall, not by society. No filters. | No |
| ADM-FDB-05 | Built | Not built | api:support/schemas.py FeedbackAdmin, RatingAdmin testimonial_permission | None on the API. | No |
| ADM-FDB-06 | Built | Not built | api:support/router.py /v1/admin/support/options (list, add, patch name, description, active, sort); api:support/defaults.py; t:support/test_support.py test_options_start_with_the_owner_lists_and_admin_edits_them | None on the API. | No |
| ADM-FDB-07 | Built | Not built | api:support/service.py patch_option, _active | None on the API. | No |
| ADM-REF-01 | Not built | Not built | api:directory/models.py Society (table only) | No societies endpoint (add, edit, deactivate). | No |
| ADM-REF-02 | Not built | Not built | - | No cars-serviced count. | No |
| ADM-REF-03 | Not built | Not built | api:customers/models.py Vehicle make, model, variant, category are free text | No catalogue tables or endpoints. | Owner supplies the catalogue |
| ADM-REF-04 | Not built | Not built | - | No admin vehicle edit. | No |
| ADM-REF-05 | Not built | Not built | - | No RC document field, upload purpose or verified flag. | S3 / dev ObjectStore |
| ADM-REF-06 | Not built | Not built | - | No society deactivate check. | No |
| ADM-SET-01 | Not built | Not built | api:directory/models.py Plan (table only; never seeded) | No plans endpoint. 'Premium Care' is not seeded. No inclusions column. | Owner supplies plan details |
| ADM-SET-02 | Partial | Not built | api:billing/config.py MoneySettings upi_id, upi_qr_url; api:billing/service.py instructions | From env only. Not editable by the admin. No QR image upload. | Owner supplies UPI ID and QR |
| ADM-SET-03 | Partial | Not built | api:support/config.py SupportSettings; t:support/test_support.py test_contact_comes_from_settings | From env only. Not editable by the admin. | Owner supplies numbers |
| ADM-SET-04 | Partial | n/a | api:billing/config.py MoneySettings seller_*; api:billing/service.py _invoice_out | Env values, not a database seed. Not stored on each invoice. | Owner supplies seller and GSTIN |
| ADM-CHK-01 | Not built | Not built | api:visits/service.py CHECKLISTS (code constant) | No checklist tables or endpoints. | Owner supplies lists |
| ADM-CHK-02 | Partial | n/a | api:visits/service.py (only code can change the lists; the crew API has no edit) | True by default. No admin edit exists. | No |
| ADM-CHK-03 | Not built | Not built | - | No add, rename, reorder, deactivate. | No |
| ADM-CHK-04 | Built | n/a | api:visits/service.py job_detail (checked_at); api:customer_reads (service details) | None. | No |
| ADM-CHK-05 | Not built | n/a | api:visits/models.py JobChecklistProgress stores item_key only | No label snapshot, so a rename would change past visits. No versioning. | No |
| ADM-CHK-06 | Not built | Not built | api:visits/service.py PROOF_MINIMUMS (code constant, 2 photos, 1 video) | No admin edit. | No |
| ADM-CHK-07 | Partial | n/a | api:visits/service.py CHECKLISTS (Cleaning-External starting list matches; the other two are placeholders) | Cleaning-Internal and Deep Spa lists are Open (owner). | Owner supplies lists |
| ADM-ADD-01 | Not built | Not built | api:addons/service.py offers() (one Deep Spa, price from env MONEY_DEEP_SPA_*) | No add-on catalogue table or endpoints. | No |
| ADM-ADD-02 | Partial | Not built | api:addons/router.py GET /v1/admin/addons (status, standalone); t:addons/test_addons.py test_the_admin_lists_and_updates_requests_without_the_9pm_rule | No society, date or add-on filter. No assigned crew member in the row. Limited to 200. | No |
| ADM-ADD-03 | Partial | Not built | api:addons/router.py PATCH /v1/admin/addons/{id} (date, finish_by, status) | Date can be set, but the scheduler does not read bookings (see ADM-SCH-30). No crew or time shown. | No |
| ADM-ADD-04 | Partial | Not built | api:addons/service.py admin_update (change, cancel, no 9 PM rule); t:addons/test_addons.py test_the_admin_lists_and_updates_requests_without_the_9pm_rule | Admin cannot create a request for a customer. | No |
| ADM-ADD-05 | Built | Not built | api:addons/service.py request (creates an Add-on payment); api:billing/router.py invoice; t:addons/test_addons.py test_a_subscriber_requests_deep_spa_and_gets_a_payment | None on the API. | No |
| ADM-ADD-06 | Built | n/a | api:addons/service.py request; t:addons/test_addons.py test_only_a_vehicle_with_an_active_subscription_can_buy_an_add_on | None. | No |
| ADM-ADD-07 | Not built | n/a | - | Missed rules not built (see ADM-CNC-03). | No |
| ADM-ADD-08 | Partial | n/a | api:scheduling/service.py build_demand (no payment check) | True by absence, but bookings are not read at all. | No |
| ADM-ADD-09 | Not built | Not built | api:addons/service.py admin_update (no admin id kept) | No audit entry. | No |
| ADM-ADD-10 | Built | n/a | api:addons/router.py POST /v1/customer/addons/standalone; t:addons/test_addons.py test_standalone_deep_spa_is_a_request_with_contact_and_no_payment | None. | No |
| ADM-ADD-11 | Built | n/a | api:customers/importer.py (_standalone_vehicle); t:test_import.py test_the_load | None. | No |
| ADM-ADD-12 | Partial | n/a | api:addons/service.py standalone (request with contact mobile, no payment) | Open: payment and recording are not decided. | Owner decision |

## Summary by area

| Area | IDs | API Built | API Partial | API Not built | UI Built | UI Partial | UI Not built | UI n/a |
|---|---|---|---|---|---|---|---|---|
| Access and roles (ADM-ACC) | 14 | 8 | 5 | 1 | 2 | 6 | 3 | 3 |
| Customers (ADM-CUS) | 21 | 3 | 5 | 13 | 0 | 0 | 18 | 3 |
| Subscriptions (ADM-SUB) | 5 | 2 | 3 | 0 | 0 | 1 | 4 | 0 |
| Crew (ADM-CRW) | 21 | 10 | 5 | 6 | 0 | 0 | 17 | 4 |
| Services and working slots (ADM-SVS) | 10 | 2 | 1 | 7 | 0 | 0 | 7 | 3 |
| Capacity (ADM-CAP) | 5 | 3 | 2 | 0 | 0 | 0 | 4 | 1 |
| Payments (ADM-PAY) | 11 | 9 | 2 | 0 | 0 | 5 | 3 | 3 |
| Scheduling (ADM-SCH) | 31 | 16 | 12 | 3 | 0 | 1 | 19 | 11 |
| Preferences (ADM-PRF) | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 0 |
| Complaints (ADM-CMP) | 8 | 4 | 4 | 0 | 0 | 0 | 5 | 3 |
| Skipped by operations (ADM-OPS) | 3 | 0 | 0 | 3 | 0 | 0 | 3 | 0 |
| Could not complete / Missed (ADM-CNC) | 6 | 0 | 0 | 6 | 0 | 0 | 6 | 0 |
| Feedback, ratings, check-ins (ADM-FDB) | 7 | 3 | 4 | 0 | 0 | 0 | 7 | 0 |
| Reference data (ADM-REF) | 6 | 0 | 0 | 6 | 0 | 0 | 6 | 0 |
| Settings (ADM-SET) | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 1 |
| Checklists and proof (ADM-CHK) | 7 | 1 | 2 | 4 | 0 | 0 | 3 | 4 |
| Add-ons (ADM-ADD) | 12 | 4 | 5 | 3 | 0 | 0 | 6 | 6 |
| **Total** | **172** | **65** | **53** | **54** | **2** | **13** | **115** | **42** |

## Reference data: what exists and what is missing

Tables in the database today that hold admin-managed reference data: only `societies` and `plans` (both in `app/directory/models.py`), plus `support_options` (feedback categories, positive tags, check-in categories, in `app/support`). Nothing in `app/directory` has a router, a service or a seed.

| Item | Requirement | Exists today | Missing |
|---|---|---|---|
| Societies | ADM-REF-01, -02, -06 | Table `societies` (name unique, sector, city, active). Used by customers, crew, schedules. Seeded only by the importer and the demo seed. | CRUD endpoints, deactivate rule (no active subscriptions or crew), cars-serviced count, default working slots on create. |
| Plans | ADM-SET-01 | Table `plans` (name unique, monthly price, list price, includes_interior, active). Never seeded. | CRUD endpoints, inclusions list column, seed of Premium Care, "deactivated plan still works for existing subscriptions" check, pending plan on subscription (ADM-CUS-15). |
| Vehicle catalogue | ADM-REF-03 | Nothing. `vehicles.make`, `model`, `variant`, `category` are free text. | Tables for make, model, variant with category and active flag; endpoints; the customer onboarding lookup that reads them. |
| Services | ADM-SVS-01, -09 | Code constants `SERVICES` and `DURATIONS` in `scheduling/models.py`. | A table is not required while durations are fixed. Needed only if duration or name must be editable (the requirement says fixed for now). |
| Working slots | ADM-SVS-02 to -08 | Nothing. The scheduler uses each crew member's own window. | Table `working_slots` (society, service, weekdays, start, end, active), CRUD, overlap check, default rows per society, scheduler use. |
| Crew working hours | ADM-CRW-04, -05 | JSON `crew_members.working_hours` (7 days) at onboarding. `scheduling_crew.start_minute/end_minute` is a separate single window. | One source of truth; edit endpoint; the scheduler reading per-day hours. |
| Crew exceptions | ADM-CRW-08 to -12 | Table `scheduling_crew_exceptions` (one row for each date, Sick, Leave, Late start). | Endpoints for date range create, edit, remove; affected-visits list; link to the crew member. |
| Checklists | ADM-CHK-01 to -05, -07 | Code constant `CHECKLISTS` in `visits/service.py` (Cleaning-External list is from ADM-CHK-07, the other two are placeholders). Progress table stores the item key. | Table `checklist_items` (service, key, label, sort_order, active), CRUD, label snapshot on checked progress, owner lists. |
| Proof minimums | ADM-CHK-06 | Code constant `PROOF_MINIMUMS` (2 photos, 1 video for each service). | Table or columns for each service, endpoints. |
| Could-not-complete reasons | ADM-CNC-01 | Code constant `REASONS` in `visits/service.py`. `job_outcomes.reason_key` stores the key. | Table `cnc_reasons` (key, label, sort_order, active), CRUD; the crew list reading the table. |
| Feedback, rating and check-in lists | ADM-FDB-06, -07 | Table `support_options` with admin CRUD and tests. | Nothing for the API. Portal screen only. |
| Issue categories | (ISS-01, fixed list) | Constant `ISSUE_CATEGORIES`. | Nothing required (fixed in MVP). |
| Add-ons catalogue | ADM-ADD-01 | One Deep Spa offer built in code from env `MONEY_DEEP_SPA_*`. | Table `addons` (name, description, price, list price, duration, active), CRUD; `addon_bookings.service` to refer to it. |
| Payment settings | ADM-SET-02 | Env `MONEY_UPI_ID`, `MONEY_UPI_QR_URL` (placeholders). | Settings table, edit endpoint, QR image upload. |
| Support settings | ADM-SET-03 | Env `SUPPORT_HELPLINE`, `SUPPORT_WHATSAPP`, `SUPPORT_HOURS`. | Settings table, edit endpoint. |
| Invoice settings | ADM-SET-04 | Env `MONEY_SELLER_*`, read when an invoice is shown. | Seed into the database and snapshot the seller on each invoice. No edit screen (by requirement). |
| Preferences | ADM-PRF-01 | Nothing (`RunRequest.days` only). | Settings row for period and week start; the run endpoint using it; email-alerts switch (ADM-ACC-09). |
| Audit log | ADM-CUS-16, ADM-ADD-09, ADM-CNC-05 | Per-feature event tables: `payment_events`, `subscription_events`, `scheduling_events`, `complaint_updates`, `schedule_changes.actor_login_id`, `auth_events`. | A general `admin_audit` table for customer, vehicle, notification, add-on and outcome edits. |
| Customer notification switches | ADM-CUS-12, -13 | Nothing. | Table or columns for the five events; customer and admin endpoints. |
| Session metadata | ADM-CUS-21, ADM-CRW-21 | `auth_sessions` (channel, last_used_at, ended_reason). | Columns device name, platform, app version; list and sign-out endpoints. |
| Vehicle photo and RC | ADM-CUS-07, ADM-REF-05 | Nothing on `vehicles`. Media purposes are proof, reason, profile. | Photo and RC upload ids, `rc_verified`, new media purposes. |


## Work packages

Sizes: S is about one day, M is two to three days, L is four days or more, for one engineer. "Existing" means the endpoint is already built and tested.

### (a) Backend packages for the missing API

| Package | IDs | Endpoints and tables | Extends | Size |
|---|---|---|---|---|
| **BE-1 Crew bridge** (do first) | ADM-CRW-01, -04, -14, -19, ADM-CAP-05, ADM-SCH-04 | Make one crew record the scheduler reads. Option: `scheduling_crew` gets a `crew_member_id` FK and is filled when a crew member is created, role changes or hours change; or the scheduler reads `crew_members.working_hours` per weekday. Backfill migration. `POST /v1/admin/crew` creates the scheduler row. | `app/crew`, `app/scheduling` | M |
| **BE-2 Crew management** | ADM-CRW-03, -05, -07, -15, -16, -19, -20 | `PATCH /v1/admin/crew/{id}` (role, working hours), `POST /{id}/deactivate`, `POST /{id}/reactivate`, `PUT /{id}/pairing`, search and society filter on `GET`, Manager edit of hours in the same society. Deactivation ends sessions and removes visits (no code). | `app/crew`, `app/identity` | M |
| **BE-3 Crew exceptions** | ADM-CRW-08 to -12 | `GET/POST /v1/admin/crew/{id}/exceptions` (date range, expands to rows in `scheduling_crew_exceptions`), `PATCH/DELETE /exceptions/{id}`, affected-visits list in the reply, Manager create. Optional audit columns. | `app/scheduling` (table exists), `app/crew` | M |
| **BE-4 Sessions (customer and crew)** | ADM-CUS-21, ADM-CRW-21 | Add `device_name`, `platform`, `app_version` to `auth_sessions` (migration; the sign-in request sends them). `GET /v1/admin/{customers,crew}/{id}/sessions`, `POST .../sessions/{sid}/logout`, `POST .../sessions/logout-all`. Audit entry on each. | `app/identity` | M |
| **BE-5 Directory: societies and plans** | ADM-REF-01, -02, -06, ADM-SET-01 | `GET/POST/PATCH /v1/admin/societies` with the deactivate rule and cars-serviced count; `GET/POST/PATCH /v1/admin/plans`; add `inclusions` column on `plans` (migration); seed Premium Care. No new tables except the column. | `app/directory` (models only today) | M |
| **BE-6 Vehicle catalogue** | ADM-REF-03, ADM-REF-04 | New tables `vehicle_makes`, `vehicle_models`, `vehicle_variants` (with category, active). `GET/POST/PATCH /v1/admin/catalogue/...`; public read for onboarding dropdowns; `PATCH /v1/admin/vehicles/{id}` (registration, make, model, variant, category). | new `app/catalogue` or `app/directory`, `app/customers` | M |
| **BE-7 Services config: slots, checklists, proof minimums, reasons** | ADM-SVS-02 to -08, ADM-CHK-01 to -07, ADM-CNC-01 | New tables `working_slots`, `checklist_items`, `service_proof_minimums`, `cnc_reasons`; CRUD endpoints under `/v1/admin/`; `visits/service.py` reads them instead of constants; keep a label snapshot on checked progress (migration on `job_checklist_progress`); default slot rows per society; overlap check. Scheduler uses slots (see BE-12). | new `app/config_data` or `app/directory`; `app/visits` | L |
| **BE-8 Settings and preferences** | ADM-SET-02, -03, -04, ADM-PRF-01, ADM-ACC-09 (email switch) | New `app_settings` table (key, JSON value): UPI ID, QR image id, helpline, WhatsApp, support hours, scheduling period, week start, admin email alerts on/off. `GET/PUT /v1/admin/settings`. `MoneySettings` and `SupportSettings` read the table with env as fallback. Seller snapshot on `invoices` (migration). Seed seller values. | `app/billing/config.py`, `app/support/config.py`, new `app/settings` | M |
| **BE-9 Customer administration: create, edit, view** | ADM-CUS-01 to -08, -15, -17 to -20, ADM-SUB-01, ADM-REF-05 | `POST /v1/admin/customers` (customer, first vehicle, parking, plan, cutoff, interior day; subscription created Activating; welcome email), `GET /v1/admin/customers?q=&society_id=` (name, mobile, registration, society), `GET /v1/admin/customers/{id}`, `POST /{id}/vehicles`, `PATCH /{id}/email`, `POST /{id}/reset-password`, `POST /{id}/resend-welcome`, `PATCH /v1/admin/subscriptions/{id}` (plan effective next renewal, cutoff, interior day). Add `pending_plan_id` and `pending_from` to `subscriptions`; `vehicles.photo_upload_id`, `rc_upload_id`, `rc_verified`; media purposes `vehicle_photo`, `rc`. | `app/customers` (admin router and service), `app/identity`, `app/media`, `app/platform/email.py` | L |
| **BE-10 Customer notification switches** | ADM-CUS-12, -13 | Table `notification_settings` (customer_id, five event flags). `GET/PUT /v1/customer/notification-settings` and `GET/PUT /v1/admin/customers/{id}/notification-settings`. Honour the flags in `support` and `notifications` senders. | `app/notifications`, `app/support` | M |
| **BE-11 Admin audit log** | ADM-CUS-16, ADM-ADD-09, ADM-CNC-05, ADM-SCH-19 (view) | Table `admin_audit` (admin login, action, target type and id, detail, at), a helper used by BE-2, -3, -4, -9, -10, -13, -14; `GET /v1/admin/audit?target=&admin=&from=&to=`. Expose `scheduling_events` and the existing event tables through the same view. | new `app/audit` | M |
| **BE-12 Scheduler corrections** | ADM-SCH-04, -09, -13 (swap), -15, -27, -29, -30, -31, ADM-CAP-03, ADM-SVS-10, ADM-ADD-08 | (1) Demand reads `schedule_changes` (skips, pauses) and active subscriptions with `first_service_date`; (2) demand reads `addon_bookings` (not `addon_requests`) with finish-by; (3) honour working slots (BE-7) and per-day hours (BE-1); (4) period Daily/Weekly/Monthly and Sunday week start from settings (BE-8); (5) `POST /v1/admin/scheduling/jobs/swap`; (6) improvement suggestions: `GET /schedules/{id}/suggestions`, `POST .../suggestions/apply`; (7) after a freeze, auto-assign on un-skip, ended pause, new vehicle, reactivation, add-on request, with admin alert and crew push; (8) removal and pool return when an exception, deactivation or add-on cancel happens, without code. | `app/scheduling`, `app/changes/sql_gateway.py`, `app/addons` | L |
| **BE-13 Skip by operations and Missed outcomes** | ADM-OPS-01 to -03, ADM-CNC-02 to -06, ADM-SCH-26, ADM-ADD-07 | `POST /v1/admin/jobs/{id}/skip-by-operations` (reason), `GET /v1/admin/missed?society_id=&date=&reason=`, `POST /v1/admin/jobs/{id}/outcome` (`reschedule_next_day` or `skip`), plan extension by one day for a Cleaning-External skip (renewal and due date shift in `changes/cycle.py` and billing), "Service skipped" customer notification, Missed alert, record of outcome and admin. Table `job_outcomes` gets `outcome`, `outcome_by`, `outcome_at`, or a new `missed_outcomes` table. Manager skip (CRW-MGR-02) uses the same function. | `app/visits`, `app/scheduling`, `app/changes/cycle.py`, `app/billing` | L |
| **BE-14 Alerts completion** | ADM-SCH-21, -22, -23, -24, -28, ADM-ACC-09, ADM-PAY-11, ADM-SUB-03, ADM-CMP-05 | Raise alerts for: skip or pause after freeze, cutoff request, add-on cancel or change after freeze, Missed job, auto-assigned visit, needs scheduling. Move `money_alerts` into `admin_alerts` (one list, one unread count). Cutoff requests: `GET /v1/admin/cutoff-requests`, `POST /{id}/handle` (add `handled_by`, `handled_at` to `schedule_changes`). Admin device tokens: `PUT /v1/admin/devices`. Email switch from BE-8. Store complaint updates in the customer inbox. Wire Resend and FCM adapters when accounts exist. | `app/support/alerts.py`, `app/billing`, `app/changes`, `app/notifications` | M |
| **BE-15 Cron endpoints** | ADM-PAY-06, ADM-SUB-03, ADM-SCH-25, ADM-CMP-08, CHK-01 push | `POST /v1/internal/cron/{generate-due-payments,mark-overdue,freeze-due,complaint-overdue,checkin-push}` guarded by a secret header. Call the existing service functions. Vercel cron entries in `vercel.json` (coordinator file). | new `app/internal` | S |
| **BE-16 Reporting filters** | ADM-CMP-01, -02, ADM-FDB-01 to -04, ADM-ADD-02, ADM-PAY-01 | Society, date and category filters and pagination on complaints, feedback, ratings, check-ins, add-ons and payments; averages by society and period; vehicle in the complaint row; signed read URLs for complaint photos; linked visit summary. | `app/support`, `app/addons`, `app/billing` | M |
| **BE-17 Add-on administration** | ADM-ADD-01, -03, -04, -05 (list), -09, -12 | Table `addons` catalogue and CRUD; `POST /v1/admin/addons` (create a request for a customer); assigned crew and time in list rows from the job; audit; `addon_bookings.service` refers to the catalogue. ADM-ADD-12 stays open for the owner. | `app/addons` | M |
| **BE-18 Web session channel** | ADM-ACC-06, -12 | `POST /v1/auth/web/login` sets an HttpOnly, Secure, SameSite cookie, CSRF token endpoint and header check on unsafe methods, 60-minute inactivity for channel `web`, logout clears cookie. Portal served under `/portal/` on the same origin, no CORS. | `app/identity`, `app/platform/deps.py`, `app/platform/middleware.py` | M |
| **BE-19 Admin home** | ADM-ACC-07 (c) | Replace `MockHomeRepository.admin_home` with SQL: unread alert count, payments Initiated, needs-scheduling count. Add `GET /v1/admin/scheduling/day?date=&society_id=` read-only schedule for the app (or reuse the board). | `app/home` | S |

Dependencies: BE-1 before BE-12 and the portal scheduling screens; BE-7 and BE-8 before BE-12 (4) and (3); BE-11 before the audit parts of BE-2, -3, -4, -9, -10, -13, -17; BE-5 before BE-9 (plan id); BE-6 before BE-9 (catalogue lookup); BE-15 needs the `vercel.json` change by the coordinator.

### (b) Portal packages (`apps/web`, React, served under `/portal/`)

| Package | Screens (IDs) | Endpoints used | New endpoints needed | Size | Depends on |
|---|---|---|---|---|---|
| **WP-0 Shell** | Sign-in, session time-out, nav by area, role guard, error envelope, generated API client from `packages/api-contract/openapi.json`, notification bell with unread count (ADM-ACC-02, -06, -09, -12, -14) | `POST /v1/auth/login` (to become web login), `POST /v1/admin/sessions/logout-all`, `GET /v1/admin/alerts` | BE-18 | M | BE-18 |
| **WP-1 Dashboard and alerts** | Counts, alert list, mark read (ADM-ACC-09, ADM-SCH-24) | `GET /v1/admin/alerts`, `/alerts/read-all`, `/alerts/{id}/read`, `GET /v1/admin/payment-alerts` | BE-14 (merged list), BE-19 | S | WP-0 |
| **WP-2 Payments and invoices** | List with filters, change status, record offline payment, issue invoice, Initiated queue (ADM-PAY-01 to -11, ADM-ADD-05) | Existing: `GET/POST /v1/admin/payments`, `PUT .../status`, `POST .../confirm`, `.../reject`, `.../invoice` | Society filter (BE-16) | M | WP-0 |
| **WP-3 Subscriptions** | Status change with reason, first service date, history (ADM-SUB-01 to -05) | Existing: `PUT /v1/admin/subscriptions/{id}/status` | History read; BE-9 for create | S | WP-0 |
| **WP-4 Complaints, feedback, ratings, check-ins** | Complaint list and detail with status and notes; feedback, ratings and check-in reports; option lists editor (ADM-CMP-01 to -08, ADM-FDB-01 to -07) | Existing: `/v1/admin/complaints`, `.../status`, `.../notes`, `/feedback`, `/ratings`, `/checkins`, `/support/options` | Filters and signed photo URLs (BE-16) | M | WP-0 |
| **WP-5 Scheduling board** | Run, board by day/crew/customer, move and take off, needs-scheduling list, freeze and unfreeze with code, capacity per date, event history (ADM-SCH-01 to -20, -23, -25 to -29, ADM-CAP-01 to -05) | Existing: `POST /run`, `GET /board`, `POST /jobs/{id}/move`, `POST /schedules/{id}/freeze`, `.../unfreeze`, `POST /freeze-due`, `GET /needs-scheduling`, `GET /capacity` | Swap and suggestions (BE-12), events list (BE-11), cutoff requests (BE-14) | L | WP-0, BE-1 |
| **WP-6 Crew** | Crew list and detail, onboard several in a row with the password shown once and Copy, reset, unlock, role, hours, pairing, exceptions, sessions, deactivate (ADM-CRW-01 to -21) | Existing: `GET/POST /v1/admin/crew`, `POST /{id}/password`, `POST /{id}/unlock` | BE-2, BE-3, BE-4 | M (L with BE-2 to -4 screens) | WP-0; BE-1 |
| **WP-7 Customers** | Create wizard (customer, vehicle, parking, plan, cutoff, interior day, first payment status, photo), list and search, detail with onboarding state, vehicles, subscription, schedule settings, sessions, notification switches, resend welcome, email correction, password reset; skip, un-skip, pause, end pause on behalf (ADM-CUS-01 to -21, ADM-REF-04, -05) | Existing: `GET/POST/DELETE /v1/admin/vehicles/{id}/skips|pauses`, `GET /vehicles/{id}/changes` | BE-9, BE-4, BE-10, BE-11, media upload for vehicle photo and RC | L | WP-0; BE-5, BE-6, BE-9 |
| **WP-8 Add-ons** | Request list with filters, create for a customer, change date and finish-by, cancel, payment link; add-on catalogue editor (ADM-ADD-01 to -12) | Existing: `GET/PATCH /v1/admin/addons` | BE-17, BE-12 (scheduling) | M | WP-0 |
| **WP-9 Missed jobs and skip by operations** | Missed list with filters, choose outcome, skip by operations with reason (ADM-OPS-01 to -03, ADM-CNC-02 to -06) | None | BE-13 | M | WP-0, BE-13 |
| **WP-10 Reference data** | Societies, plans, vehicle catalogue, working slots by society and service, checklists and proof minimums by service, could-not-complete reasons (ADM-REF-01 to -03, -06, ADM-SET-01, ADM-SVS-02 to -08, ADM-CHK-01 to -06, ADM-CNC-01) | None for these (only `GET /v1/admin/support/options` exists) | BE-5, BE-6, BE-7 | L | WP-0 |
| **WP-11 Settings and preferences** | Scheduling period, week start, email alert switch, payment settings with QR upload, support numbers and hours, read-only invoice settings (ADM-PRF-01, ADM-SET-02 to -04, ADM-ACC-09) | None | BE-8 | S | WP-0, BE-8 |
| **WP-12 Audit views** | Audit list with filters; schedule event history; payment, subscription and complaint history (ADM-CUS-16, ADM-SCH-19, ADM-PAY-05, ADM-ADD-09, ADM-CNC-05) | None | BE-11 | S | WP-0, BE-11 |

Mobile quick actions still missing (Flutter, `apps/mobile/lib/features/admin_quick`), all small:

| Package | IDs | Endpoints | Size |
|---|---|---|---|
| **MQ-1 Complaints, feedback, ratings, check-ins (view and update)** | ADM-ACC-07 (f) | Existing: `/v1/admin/complaints`, `/status`, `/notes`, `/feedback`, `/ratings`, `/checkins` | M |
| **MQ-2 Needs scheduling and day schedule, read-only; capacity** | ADM-ACC-07 (c), ADM-CAP-01 | Existing: `GET /needs-scheduling`, `GET /board`, `GET /capacity` | S |
| **MQ-3 Skip, un-skip, pause, end pause for a customer** | ADM-ACC-07 (e), ADM-CUS-09 | Existing admin changes endpoints; customer search needs BE-9 | M |
| **MQ-4 Skip by operations and Missed outcome** | ADM-ACC-07 (d) | BE-13 | M |
| **MQ-5 Search and view customers, crew list, crew exceptions, add-on requests** | ADM-ACC-07 (f) | BE-9, BE-3, existing `GET /v1/admin/crew`, `GET /v1/admin/addons` | M |
| **MQ-6 Admin push registration** | ADM-ACC-07 (a), ADM-ACC-09 | BE-14 (device endpoint), FCM account | S |
| **MQ-7 Admin home with real data** | ADM-ACC-07 | BE-19 | S |

Suggested order: BE-1, BE-15, BE-18, BE-5, BE-8, BE-11 (foundations); then WP-0, WP-1, WP-2, WP-4, WP-5 (all use existing endpoints and give a working portal early); then BE-2, BE-3, BE-9, BE-7, BE-12, BE-13 with WP-6, WP-7, WP-9, WP-10; then BE-4, BE-10, BE-14, BE-16, BE-17 with WP-3, WP-8, WP-11, WP-12 and the MQ packages.

## Open items for the owner (not decided by this audit)

- Content: starting checklists for Cleaning-Internal and Deep Spa (ADM-CHK-07), the plan inclusions and price list for Premium Care (ADM-SET-01), the vehicle catalogue (ADM-REF-03).
- Standalone Deep Spa payment and recording (ADM-ADD-12 / ADD-15).
- Accounts: Resend, FCM, S3 (or the dev object store), UPI ID and QR, seller name, address and GSTIN, support numbers.
