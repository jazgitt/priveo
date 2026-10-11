# Crew requirements: coverage audit

Audited against `docs/reqs/crew-functional-requirements.md` (v0.5) at commit `e3f91b7` (`integration/complete-build`). Verdicts come from reading the code, not from `docs/feature-status.json` or the overnight build report.

Code read: `services/api/app/{crew,visits,media,scheduling,support,identity,notifications,changes,addons,customer_reads}` with `services/api/tests/{crew,visits,media,scheduling,support}` and `tests/test_api.py`; `apps/mobile/lib/features/{crew,people}`, `apps/mobile/test/crew` and `test/screens_test.dart`.

Verdicts: **Built** (the behaviour is fully present, API and app), **Partial** (something named is missing), **Not built**.

Short names used below: `V` = `services/api/app/visits` (`service.py`, `router.py`, `schemas.py`, `models.py`), `M` = `services/api/app/media`, `S` = `services/api/app/scheduling`, `C` = `services/api/app/crew`, `I` = `services/api/app/identity`, `A` = `apps/mobile/lib/features/crew`, `TV` = `services/api/tests/visits`, `TC` = `services/api/tests/crew`, `TM` = `services/api/tests/media`, `AT` = `apps/mobile/test/crew`.

## Findings that cut across many IDs

1. **The crew directory and the scheduler are not linked.** `POST /v1/admin/crew` (C) creates a `Login` and a `CrewMember`. The scheduler and the crew job APIs read `scheduling_crew` (`SchedulingCrew`). Nothing in `app/` creates a `SchedulingCrew` row (only test conftests do). A crew member onboarded through the admin API therefore has no jobs and is never assigned work. Working hours are also kept twice: per weekday on `CrewMember.working_hours`, and as one window on `SchedulingCrew`. The scheduler uses only the single window. There is no API that sets `paired_member_id` (Trainee pairing).
2. **No crew notifications exist.** `NotificationService` (`app/notifications`) is customer-only (`/v1/customer/...`), its `EVENTS` list has no crew events, and nothing in the codebase calls `notify(...)`, not even the customer's "Service completed". The crew app has no device registration and no inbox.
3. **Proof does not reach the customer.** `customer_reads/sql_repository.py` says proof "joins in when the media tables arrive" and returns none. There is no read or download URL on the object store (`ObjectStore` only has `presign_upload` and `size_of`), so no photo (job proof, vehicle photo, profile photo) can be shown to anyone yet.
4. **Checklists, minimums and reasons are code constants** (`CHECKLISTS`, `PROOF_MINIMUMS`, `REASONS` in V `service.py`), marked DERIVED in the code. No admin module manages them (ADM-CHK, ADM-CNC). The Cleaning-Internal and Deep Spa checklists are placeholders (open question 1 in the crew file).
5. Smaller deviations: `GET /v1/crew/ratings` (support module) serves an aggregate star count to crew, which the requirement says the crew app does not show (the app does not call it, but the endpoint should go); `GET /v1/crew/home` still serves mock data from `app/home`; a crew member can still request uploads for a job that is already closed (`media.router.request_upload` does not check the job status); a Deep Spa add-on job shares the day's `Visit` row, so the visit stays open until the add-on job is done (ADD-11 says it is separate).

## Coverage table

| ID | Verdict | Evidence (files) | Missing / notes | Needs backend? | Needs account/stub? |
|---|---|---|---|---|---|
| CRW-ACC-01 | Built | `apps/mobile/lib/core/routing/router.dart` (`/crew`), `A/home/crew_home_screen.dart`, `I/service.py` (`role_for`). Tests: `apps/mobile/test/screens_test.dart` "crew login lands on the crew home" | None | No | No |
| CRW-ACC-02 | Built | `I/service.py` `role_for`, `start`, `login`; `I/router.py` `/v1/auth/start`; login screen label "Email, mobile or user ID" in `app_en.arb`. Tests: `services/api/tests/test_api.py`, `tests/test_first_sign_in.py` | None | No | No |
| CRW-ACC-03 | Built | `C/service.py` `create` (login_id = mobile); no endpoint changes it. Test: `TC/test_crew.py` | None | No | No |
| CRW-ACC-04 | Built | `C/service.py` `generate_password`. Test: `TC/test_crew.py::test_password_format` | None | No | No |
| CRW-ACC-05 | Partial | `C/service.py` `create`, `reset_password` return `CrewPassword` once, only the hash is stored. Test: `TC/test_crew.py` | The admin screen with login ID, password and Copy button does not exist (no `apps/web`, no crew screen in `admin_quick`). API half only | Yes (admin UI is the web portal) | No |
| CRW-ACC-06 | Built | No crew password-change endpoint exists. `C/router.py` `POST /v1/admin/crew/{id}/password` resets in the same format. Test: `TC/test_crew.py::test_reset_gives_a_new_password...` | The admin screen that calls it is ADM-CRW-18 (not built) | No | No |
| CRW-ACC-07 | Built | `I/service.py` `login` (`MAX_WRONG_ATTEMPTS`, `locked`), `C/service.py` `unlock`. Tests: `tests/test_api.py::test_five_wrong_passwords_lock_crew_and_admin`, `TC/test_crew.py::test_a_locked_login...` | None | No | No |
| CRW-ACC-08 | Partial | `I/service.py` `login` and `_live` refuse `active = false`. Test: `TC/test_crew.py::test_a_deactivated_crew_member_cannot_sign_in` (sets the flag directly) | No endpoint deactivates or reactivates a crew member (ADM-CRW-15). `SchedulingCrew.active` is separate from `Login.active`, so a deactivated person would still be scheduled | Yes | No |
| CRW-ACC-09 | Built | `apps/mobile/lib/features/common/signout_button.dart` (used on crew home), `I/router.py` `/v1/auth/logout` | No crew-specific test; sign-out is tested for the shared auth controller | No | No |
| CRW-ACC-10 | Built | `C/service.py` `create` returns 409 `mobile_in_use`; `crew_members.mobile` unique. Test: `TC/test_crew.py::test_a_mobile_number_belongs_to_one_login` | None | No | No |
| CRW-ACC-11 | Partial | Reset ends all sessions (`C/service.py` `reset_password`, test `test_reset_gives_a_new_password_and_signs_the_phone_out`); `I/service.py` `_live` ends the session when the login is inactive; logout ends the session | No admin "sign out this crew member" (ADM-CRW-21): `POST /v1/admin/sessions/logout-all` signs out only the caller's own login. No deactivate endpoint to trigger the end | Yes | No |
| CRW-ACC-12 | Built | `A/upload/upload_queue.dart`, `A/upload/sqlite_store.dart` (queue persisted in SQLite, not cleared on sign-out), `A/crew_providers.dart`. Tests: `AT/queue_test.dart` (resume after app close) | No test signs out and in again with a queued file. Queue is not keyed by login (a different crew member on the same phone would send the first one's files) | No | No |
| CRW-PRF-01 | Partial | `C/router.py` `GET /v1/crew/profile`, `A/profile/crew_profile_screen.dart`. Tests: `TC/test_crew.py::test_crew_profile_...`, `AT/screens_test.dart` "the profile shows..." | Photo is never shown: the screen draws the initial letter and the text "photo saved". No photo read URL exists (finding 3) | Yes | No (dev object store) |
| CRW-PRF-02 | Built | `V/router.py` `GET/PUT /v1/crew/profile/photo`, `V/service.py` `set_profile_photo`, `A/profile/crew_profile_screen.dart` (camera and library). Test: `TV/test_crew_jobs.py::test_profile_photo_needs_a_confirmed_upload` | The saved photo cannot be displayed yet (see PRF-01). App has no test that changes the photo | No | No |
| CRW-PRF-03 | Built | No endpoint edits mobile, password, name, society or role from the crew side; profile screen is read-only except the photo | None | No | No |
| CRW-PRF-04 | Built | `M/service.py` `request_upload` (purpose `profile` must be a photo; types and 10 MB limit), `A/capture/media_capture.dart`. Tests: `TM/test_uploads.py::test_formats_and_sizes...`, `AT/models_test.dart` | None | No | No |
| CRW-SCH-01 | Partial | `V/service.py` `list_jobs` (Frozen schedules only), `V/router.py` `GET /v1/crew/visits`, `A/home/crew_home_screen.dart`. Tests: `TV/test_crew_jobs.py`, `AT/screens_test.dart` | Crew created through the admin API have no `SchedulingCrew` row, so no job can ever reach them (finding 1) | Yes | No |
| CRW-SCH-02 | Built | `V/schemas.py` `CrewJobCard`, `V/service.py` `_cards`, `A/job/job_card_screen.dart` (`JobFacts`). Test: `TV/test_crew_jobs.py::test_cards_for_a_day_show_the_vehicle...`, `AT/screens_test.dart` | None | No | No |
| CRW-SCH-03 | Not built | None. `CrewJobCard` has no vehicle photo field and no photo can be fetched (finding 3) | Add the vehicle photo to the card and a signed read URL | Yes | No |
| CRW-SCH-04 | Partial | `Job.finish_by_minute` from the customer cutoff (`S/service.py` `build_demand`), card `finish_by`, shown in `JobFacts` | Deep Spa add-on: the proposed finish-by time is not stored, so `build_demand` passes `None` (code comment cites ADM-SCH-30) and the card shows no finish-by | Yes | No |
| CRW-SCH-05 | Built | `S/service.py` `build_demand` (External daily, Internal on interior day, Deep Spa from add-on requests, standalone or not), `S/models.py` `DURATIONS`, one card per `Job`. Tests: `services/api/tests/scheduling/test_scheduling_api.py`, `TV/test_crew_jobs.py::test_a_visit_is_completed_only_when_all_its_jobs_are_done` | Internal and Deep Spa checklists are placeholders (SVC-02) | No | No |
| CRW-SCH-06 | Built | `V/router.py` `GET /v1/crew/visits?date=&all=`, `A/home/crew_home_screen.dart` `_DayBar`. Test: `AT/screens_test.dart` "the day can be moved and all jobs shown" | None | No | No |
| CRW-SCH-07 | Built | `S/models.py` `JOB_STATUSES`, `V/service.py`; status chip in `JobFacts`. (A fifth status, Skipped, also exists.) Tests in `TV/test_crew_jobs.py` | None | No | No |
| CRW-SCH-08 | Partial | `app/changes/sql_gateway.py` `skip_day`, `pause_range` set open jobs to Skipped; cards read live | A skipped job is not removed: it stays on the cards as Skipped and counts as done. Cancelling an add-on (`app/addons/service.py` `_cancel`) does not touch its job until a scheduler re-run. No test covers the crew side | Yes | No |
| CRW-SCH-09 | Built | Cards are read from the database on each request (pull to refresh in `crew_home_screen.dart`); `S/service.py` `run_schedule` on a Frozen schedule assigns late jobs; unfreeze hides the cards (Draft filter) | No push, so the change shows only on refresh (CRW-NOT-04). The automatic late assignment trigger is ADM-SCH-27, not crew | No | No |
| CRW-SCH-10 | Partial | `V/service.py` `_my_crew_ids` (Trainee also sees the paired Member's jobs), `S/rules.py` `window_for` (Trainee counts zero). Test: `TV/test_crew_jobs.py::test_a_trainee_sees_and_does_the_paired_members_jobs` | `paired_member_id` has no setter anywhere in `app/` (ADM-CRW-19 pairing is not built) | Yes | No |
| CRW-SCH-11 | Built | `V/service.py` `_job_row`, `_jobs_where` (Frozen only). Test: `TV/test_crew_jobs.py::test_a_draft_schedule_is_not_shown_to_the_crew` | None | No | No |
| CRW-SCH-12 | Built | Progress and uploads are per job, not per person (`JobChecklistProgress`, `MediaUpload.job_id`); status is on the job; Member away returns the job to the pool (`S/service.py` `run_schedule`). Test: `TV/test_crew_jobs.py::test_a_trainee_sees_and_does...` | None | No | No |
| CRW-SCH-13 | Built | `V/schemas.py` (no customer fields), `S/service.py` `crew_day`. Test: `TV/test_crew_jobs.py::test_cards_for_a_day_show_the_vehicle_and_never_the_customer`, `AT/screens_test.dart` "the home shows today's cards with no customer details" | None | No | No |
| CRW-MGR-01 | Built | `V/router.py` `GET /v1/crew/manager/schedule`, `V/service.py` `manager_schedule`, `A/manager/manager_schedule_screen.dart`. Tests: `TV/test_manager.py`, `AT/screens_test.dart` "a Manager sees the team..." | None | No | No |
| CRW-MGR-02 | Partial | `V/service.py` `manager_could_not_complete` path, `manager_skip` (JobOutcome keeps who and when), `A/manager/manager_job_screen.dart`. Tests: `TV/test_manager.py` | A skip sets the job to Skipped only. No "Service skipped" notification to the customer and no plan extension by one day for Cleaning-External (ADM-OPS-03) | Yes | No (push adapter) |
| CRW-MGR-03 | Partial | `V/service.py` `manager_reassign` (same society, Member or Manager, recorded in `JobReassignment`), `A/manager/manager_job_screen.dart`. Test: `TV/test_manager.py::test_reassign_moves_the_job_and_follows_the_trainee` | "Working that day" is not checked (code comment: "Attendance is not checked yet"); the new crew member's hours and overlaps are not checked; no push to either crew member | Yes | No |
| CRW-MGR-04 | Not built | `SchedulingCrewException` model only (`S/models.py`). No crew router, API or screen | Needs a Manager attendance read and exception add, edit, remove for the society, recalculating capacity and sending affected visits to Needs scheduling | Yes | No |
| CRW-MGR-05 | Not built | None. `ManagerScheduleScreen` doc comment says "Attendance and working hours are not here yet" | Manager edit of working hours for own society, from a date, with capacity recalculated; also needs finding 1 fixed (per-weekday hours into the scheduler) | Yes | No |
| CRW-MGR-06 | Built | Same schemas as CRW-SCH-13; manager routes return `JobDetail` and `ManagerSchedule` only. Test: `TV/test_manager.py` | None | No | No |
| CRW-SVC-01 | Built | `V/service.py` `job_detail`, `GET /v1/crew/jobs/{id}`, `A/job/job_card_screen.dart`, `A/job/perform_service_screen.dart`. Tests: `TV/test_crew_jobs.py`, `AT/screens_test.dart` | None | No | No |
| CRW-SVC-02 | Partial | `V/service.py` `CHECKLISTS`; the crew screen only ticks | Not "the one the admin set up": no admin checklist storage or API (ADM-CHK-01). Internal and Deep Spa lists are placeholders pending the owner | Yes | Owner input (starting checklists) |
| CRW-SVC-03 | Partial | `V/models.py` `JobChecklistProgress` (time and who), `V/service.py` `set_checked`. Test: `TV/test_crew_jobs.py` | Ticks and times are not exposed to the customer's Service Details (`customer_reads` has no checklist) | Yes | No |
| CRW-SVC-04 | Built | `M/router.py` (`/v1/media/uploads`, local PUT, confirm), `A/capture/media_capture.dart` (camera and gallery), `A/job/perform_service_screen.dart`. Tests: `TM/test_uploads.py`, `AT/screens_test.dart` | Real S3 signed URLs wait on the AWS account; the local-disk store is the dev adapter | No | Stub (dev object store; S3 later) |
| CRW-SVC-05 | Partial | Stage is required for proof (`M/service.py`), stored, chosen in the app (`_stages`) | Not shown in the customer's photo viewer: proof is not joined into `customer_reads` and nothing serves the file (finding 3) | Yes | No |
| CRW-SVC-06 | Built | `M/service.py` (`CONTENT_TYPES` incl. HEIC, `MAX_BYTES` 10 MB and 25 MB, size re-checked on confirm), `A/capture/media_capture.dart` `CaptureProblem`. Tests: `TM/test_uploads.py::test_formats_and_sizes_follow_rule_17`, `AT/models_test.dart`, `AT/screens_test.dart` "a file that breaks the rules is not queued" | None | No | No |
| CRW-SVC-07 | Partial | `V/service.py` `PROOF_MINIMUMS` (2 photos, 1 video, enforced in `complete_job`) | Constants, not set by the admin (ADM-CHK-06) | Yes | No |
| CRW-SVC-08 | Built | `V/service.py` `_missing`, `complete_job` (409 `job_not_ready`), `can_complete`; app button disabled with a "missing" list. Tests: `TV/test_crew_jobs.py::test_a_job_cannot_complete_until...`, `AT/screens_test.dart` | None | No | No |
| CRW-SVC-09 | Partial | `V/service.py` `complete_job` stamps `JobTiming.finished_at`; `S/service.py` `set_job_status`, `refresh_visit_status` make the visit Completed only when all jobs are done or skipped. Test: `TV/test_crew_jobs.py::test_a_visit_is_completed_only_when_all_its_jobs_are_done` | No "Service completed" push or inbox item (nothing calls `NotificationService.notify`); proof does not appear in the customer app; the add-on job shares the day's visit | Yes | Stub (push adapter) |
| CRW-SVC-10 | Built | `A/upload/upload_queue.dart`, `sqlite_store.dart` (step saved after each stage, connectivity trigger, retry); server counts pending uploads in `proof_counts` and blocks completion. Tests: `AT/queue_test.dart`, `AT/screens_test.dart` "with no connection the photo waits..." | Plugin behaviour (sqflite, connectivity) is faked in tests, not run on a device | No | No |
| CRW-SVC-11 | Built | `V/service.py` `start_job`, status In progress, progress kept in the database; app "Continue". Test: `TV/test_crew_jobs.py::test_start_moves_a_job_to_in_progress` | None | No | No |
| CRW-SVC-12 | Built | `V/service.py` `_open_job` (409 `job_closed`) on tick, start, complete, could-not-complete. Test: `TV/test_crew_jobs.py::test_a_completed_job_cannot_be_changed` | `media.router.request_upload` still accepts uploads for a closed job | Yes (small) | No |
| CRW-CNC-01 | Built | `V/router.py` `POST /v1/crew/jobs/{id}/could-not-complete`, `A/job/could_not_complete_screen.dart`. Tests: `TV/test_crew_jobs.py`, `AT/screens_test.dart` "could not complete needs a reason..." | None | No | No |
| CRW-CNC-02 | Built | `V/service.py` `_check_reason` (reason required, note up to 500, optional confirmed `reason` photo). Tests: `TV/test_crew_jobs.py::test_could_not_complete_needs_a_listed_reason`, `..._can_carry_a_confirmed_photo` | None | No | No |
| CRW-CNC-03 | Partial | `V/service.py` `REASONS`, `GET /v1/crew/reasons` | List is a constant. No admin management (ADM-CNC-01) | Yes | No |
| CRW-CNC-04 | Partial | `V/service.py` `could_not_complete` (job status, `JobOutcome`, other jobs untouched); `customer_reads/sql_repository.py` maps it to Missed | The admin push (ADM-SCH-24) is not sent | Yes | Stub (push adapter) |
| CRW-CNC-05 | Not built | None | No admin outcome (schedule again for the next day, or skip), no auto-assignment of the re-run job, no plan extension (ADM-CNC-03, ADM-SCH-26) | Yes | No |
| CRW-CNC-06 | Partial | "Missed" is shown (`customer_reads/sql_repository.py`); no push is sent (nothing sends one) | "Rescheduled on dd-Mon-yy" and "Covered on dd-Mon-yy" do not exist (no grep hit in `app/`) | Yes | No |
| CRW-RAT-01 | Built | `A` has no ratings screen or call; `support/schemas.py` `CrewRatings` has no names, tags or comments. Test: `services/api/tests/support/test_support.py` (crew ratings) | Deviation: `GET /v1/crew/ratings` still exists and serves an aggregate (finding 5). Remove it or confirm with the owner | Yes (small) | No |
| CRW-NOT-01 | Not built | None | No crew push on freeze with new or changed jobs; no crew device registration; no FCM | Yes | Stub (push adapter); real FCM needs the Firebase account |
| CRW-NOT-02 | Not built | None | No push when a job is removed (skip, pause, add-on cancel, skipped by operations) | Yes | Same as NOT-01 |
| CRW-NOT-03 | Not built | None | Nothing to switch off because there are no crew notifications. Needs to be honoured when NOT-01, 02, 04, 05 are built (no preference for crew) | Yes | Same as NOT-01 |
| CRW-NOT-04 | Not built | `S/service.py` `run_schedule` assigns late jobs on a Frozen schedule but sends nothing | Push to the crew member when a job is auto-assigned after a freeze | Yes | Same as NOT-01 |
| CRW-NOT-05 | Not built | `manager_reassign` records the move but sends nothing | Push to both crew members (and a paired Trainee) on reassignment | Yes | Same as NOT-01 |

## Summary by area

| Area | IDs | Built | Partial | Not built |
|---|---|---|---|---|
| Access and login (ACC) | 12 | 9 | 3 (05, 08, 11) | 0 |
| Profile (PRF) | 4 | 3 | 1 (01) | 0 |
| My schedule (SCH) | 13 | 8 | 4 (01, 04, 08, 10) | 1 (03) |
| Manager (MGR) | 6 | 2 | 2 (02, 03) | 2 (04, 05) |
| Performing a service (SVC) | 12 | 7 | 5 (02, 03, 05, 07, 09) | 0 |
| Could not complete (CNC) | 6 | 2 | 3 (03, 04, 06) | 1 (05) |
| Ratings (RAT) | 1 | 1 | 0 | 0 |
| Notifications (NOT) | 5 | 0 | 0 | 5 |
| **Total** | **59** | **32** | **18** | **9** |

What works end to end today (API, app and tests): the crew sign-in rules, job cards for a Frozen schedule, the day or all-jobs view, the checklist, photo and video capture with the offline queue, "Mark complete" gating, Could not complete with reason, note and photo, the Manager schedule view, skip and reassign, and the profile with a photo change. The first thing to fix is the link between a crew member created by the admin and the scheduler (finding 1): without it none of the above is reachable for a real onboarded crew member.

## Work packages

Packages are ordered by dependency. WP-A is the foundation. WP-B, WP-C, WP-D and WP-E can run in parallel once WP-A's model change (a `crew_members` to `scheduling_crew` link) is merged, except where noted. Each package that touches `models.py`, `main.py`, `openapi.json`, `api.g.dart` or `router.dart` needs the coordinator to wire it.

### WP-A: Crew directory joined to the scheduler (size M)

IDs: CRW-ACC-08, CRW-ACC-11, CRW-SCH-01, CRW-SCH-10 (also unblocks CRW-MGR-04, CRW-MGR-05).

- API: when `CrewService.create` runs, create the `SchedulingCrew` row in the same transaction (same login, society, role; start and end derived from the weekday hours). Make the scheduler use the per-weekday hours (`rules.window_for` by weekday) instead of one window, or have `SchedulingCrew` read `CrewMember.working_hours`. Add admin endpoints: deactivate and reactivate a crew member (sets `Login.active` and `SchedulingCrew.active`, ends sessions), "sign out this crew member" (ADM-CRW-21), set or clear a Trainee's paired Member (ADM-CRW-19). A migration backfills `scheduling_crew` for existing `crew_members`. Remove the `/v1/crew/ratings` endpoint (or confirm it) and the mock `GET /v1/crew/home` if nothing uses it.
- App: none, apart from a crew sign-in that is ended by the server showing the sign-in screen (already handled by the auth controller; add a test).
- Dependencies: none. Touches `app/crew`, `app/scheduling`, a new migration.
- Tests: onboarded crew gets jobs after a run and freeze; deactivated crew has no capacity and cannot sign in; pairing makes a Trainee see the Member's jobs.

### WP-B: Manager attendance, working hours and reassignment checks (size M)

IDs: CRW-MGR-04, CRW-MGR-05, CRW-MGR-03 (the "working that day" and overlap checks), CRW-MGR-02 (the plan extension half).

- API: new Manager routes under `/v1/crew/manager`: attendance for the society by date, add, edit and remove exceptions (Sick, Leave, Late start), edit working hours from a date. Record who and when. Recalculate capacity and send affected visits to Needs scheduling or auto-assign them using the existing `run_schedule` on a Frozen schedule. In `manager_reassign`, require the target to be working that day and not overlapping, and fix the time window. For a Manager skip of a Cleaning-External job, extend the plan by one day through the `app/changes` and `app/billing` cycle code (ADM-OPS-03).
- App: Manager screens for attendance (list and exception form) and working-hours edit, in `apps/mobile/lib/features/crew/manager`; a `routes.dart` entry or pushed screens as done for the other manager screens; strings in `crew_text.dart`.
- Dependencies: WP-A (the crew link and per-weekday hours). The plan extension needs the `app/changes` module only (already present).
- Tests: Manager cannot touch another society; capacity changes at once; reassign to a person on leave is refused.

### WP-C: Crew and customer notifications (size L)

IDs: CRW-NOT-01, CRW-NOT-02, CRW-NOT-03, CRW-NOT-04, CRW-NOT-05, CRW-SCH-08, CRW-SVC-09 (customer "Service completed" half), CRW-MGR-02 (customer "Service skipped" half), CRW-CNC-04 (admin push).

- API: add crew events to `NotificationService` and a crew inbox and device registration (`/v1/crew/notifications`, `/v1/crew/devices`, role crew, no preferences so crew cannot switch off). Hook the events at: freeze (`S/service.py` `freeze`, `freeze_due`), late assignment (`run_schedule` on Frozen), job removal (`app/changes` skip and pause, add-on cancel, Manager skip), reassignment (`manager_reassign`), could-not-complete (admin push through `app/support/notify.py`), and visit completion (`set_job_status` or `V/service.py` `complete_job`, calling the customer `service_completed` and `service_skipped` events). Make a skipped or cancelled job disappear from crew cards (filter Skipped from `_jobs_where` for the day view, and delete or skip the add-on job on `_cancel`). Messages stay behind the existing `PushSender` adapter.
- App: crew inbox screen and device-token registration (a stub registering a fake token, since FCM needs the Firebase account), in `features/crew`.
- Dependencies: WP-A for the crew-member to login mapping. Needs the coordinator for `main.py` and the contract.
- Account or stub: push stays on the logging fake; real FCM waits on the owner's Firebase account.
- Tests: each event reaches the right login once; a Trainee follows their Member; no customer name in any crew push.

### WP-D: Proof and photo reads (size M)

IDs: CRW-SCH-03, CRW-PRF-01 (photo), CRW-SVC-03, CRW-SVC-05, CRW-SVC-09 (proof half), CRW-SVC-12 (closed-job upload guard).

- API: add `presign_download` (and a signed GET route for the local dev store) to `ObjectStore`; return a vehicle photo URL on `CrewJobCard` and a profile photo URL on the profile or `PhotoState`; join checklist ticks with times and confirmed proof (kind, stage, URL) into `customer_reads/sql_repository.py` so Service Details shows them; refuse `request_upload` for a closed job.
- App: show the vehicle photo on the job card and the profile photo on the profile (`features/crew`); the customer Service Details screens in `features/customer` render what the API now returns (coordinate with the customer audit).
- Dependencies: none for the crew side. The customer side touches `app/customer_reads` and the customer feature, so check overlap with the customer audit's packages.
- Account or stub: the dev object store behind the existing adapter; S3 later.
- Tests: a crew member cannot fetch another society's photo; the customer sees only their own visit's proof.

### WP-E: Admin-managed checklists, minimums, reasons and outcomes (size L)

IDs: CRW-SVC-02, CRW-SVC-07, CRW-CNC-03, CRW-CNC-05, CRW-CNC-06, CRW-SCH-04 (Deep Spa finish-by).

- API: tables and admin endpoints for per-service checklists, minimum photos and videos, and the could-not-complete reasons (ADM-CHK-01, ADM-CHK-06, ADM-CNC-01), seeded from the current constants; `V/service.py` reads them instead of `CHECKLISTS`, `PROOF_MINIMUMS`, `REASONS` (keep keys stable for existing progress rows). The admin outcome for a Missed job (ADM-CNC-03): none needed for Cleaning-External, schedule again for the next day or skip for the others, with auto-assignment (ADM-SCH-26). Store the add-on finish-by time (ADM-SCH-30) and pass it through `build_demand`. Expose "Rescheduled on" and "Covered on" in `customer_reads`.
- App: crew screens already read checklist, requirements and reasons from the API, so little changes; the admin side is in the web portal (another agent). Customer Missed, Rescheduled and Covered strings.
- Dependencies: the admin web portal for the screens (not this package). Owner input is still needed for the starting checklists of Cleaning-Internal and Deep Spa (open question 1). Touches `app/scheduling` and `app/addons`, so coordinate with WP-A.
- Tests: an edited checklist changes the next job's checklist, not completed jobs; a rescheduled job lands on the crew member's cards for the next day.

### Order and parallelism

1. WP-A first (small and it unlocks real crew).
2. WP-B, WP-C, WP-D, WP-E in parallel after WP-A. WP-C and WP-B both touch `manager_reassign`: land WP-B's checks first or merge carefully. WP-D and WP-E both touch `customer_reads`: WP-D owns the proof join, WP-E owns the "Rescheduled" and "Covered" labels.
