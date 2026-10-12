# Overnight build report: Phases 2 to 7

This is the original overnight snapshot. Later integration has closed several gaps below; see [the current handoff](codex-handoff-plan.md) before planning new work.

**Status:** 11 Oct 2026. Built by six parallel slices on `integration/mobile-phases-2-7`, integrated and checked together. Nothing here was deployed. The `dev` database and the `dev` API were not touched.

## What is in

| Slice | PR | Backend | App |
|---|---|---|---|
| People | #25 | `crew` module, crew password shown once, `EmailSender` adapter (logging fake) | Crew profile |
| Scheduling | #26 | OR-Tools scheduler, capacity, Draft and Frozen, freeze and unfreeze, needs-scheduling, `next-job` and `crew/day` reads | None (admin board is for the web portal) |
| Crew app | #30 | Job status, checklist, could-not-complete, manager endpoints, media uploads behind an `ObjectStore` adapter (local disk) | Crew home on real data, job card, perform service, camera and video capture, offline upload queue, manager screens, profile photo |
| Customer app | #27 | Calendar, visit details with proof, history, vehicles, notifications inbox, device tokens, logging `PushSender` | Next service on Home, Calendar tab, Account tab, history, vehicles, inbox |
| Changes and money | #29 | Skip, pause, 9 PM rule, UPI payment statuses, invoices, 7-day Inactive job, Deep Spa add-on | Skip or pause, My subscription, billing history, pay by UPI, Deep Spa, admin payments |
| Support | #28 | Complaints, feedback, visit ratings, check-ins, admin alerts | Help, report an issue, my complaints, feedback, check-in, crew ratings, admin alert list |

Integration work: migrations chained `0005` to `0010`, the scheduler's `visits` and `jobs` tables shared by every slice, the customer read repository and the change gateway bound to those tables, colliding schema names made unique, `gen_api.dart` made to skip what it cannot express (the new screens call their endpoints with hand-written DTOs), the Support tab and the quick actions wired.

## Checks run on the integration branch

- API: `ruff check` clean, `pytest -q` 214 passed (includes the migration-versus-models test and a single Alembic head).
- App: `flutter analyze` no issues. `flutter test` results are in the PR description.
- No goldens were added or regenerated. The crew home golden image will differ on Linux CI: add the `update-goldens` label to the PR.
- Not run: the emulator workflow, a deploy, a migration on the `dev` database, a real device.

## Stubs and what unblocks each

| Stub | Replace with | Needs |
|---|---|---|
| Email goes to a logging sender; the first sign-in code is still the fixed `MOCK_EMAIL_CODE` on `dev` | Resend sender, and `identity` switched to the `EmailSender` adapter | Resend account and sending domain |
| Push goes to a logging sender; the app registers no token | FCM sender, `firebase_messaging`, `google-services.json` | Firebase project |
| Media is stored on local disk (`MEDIA_ROOT`), and `upload_url` points at the API | An S3 `ObjectStore` with real signed URLs | S3 bucket and CloudFront |
| UPI ID, payee, QR URL, seller name, address, GSTIN, Deep Spa price are `MONEY_*` placeholders | Real values in configuration | UPI details, GSTIN |
| Helpline and WhatsApp are `SUPPORT_*` placeholders | Real numbers | Support numbers |
| Nothing calls `freeze_due`, `mark_overdue_and_inactive`, `generate_due_payments`, `alert_overdue_complaints`, `notify_due_checkins` on a timer | EventBridge Scheduler jobs | AWS account |

## Derived and Open choices

None is marked Owner. The requirement tables were not edited: the Status cells for these IDs still say what they said before, and need the owner's review.

**Open (needs an owner answer)**

- `CRW-RAT-01` says the crew app does not show ratings; the plan says there is a crew ratings screen. Built as a 30-day average, count and star spread, with no names, tags or comments.
- `ADD-15` standalone Deep Spa: built as a request with date, finish-by, mobile and notes, no price, no payment, status Requested.
- Deep Spa has no stored finish-by in the solver, so it is placed without one.
- Crew profile photo cannot be shown yet (no download URL endpoint).
- Admin email switch (`ADM-ACC-09`) and customer notification switches (`NOTIF-03`) are not applied.
- Missed-day text (`CAL-09`) shows plain "This service was missed."
- Internal and Deep Spa checklists are placeholders. Photo and video minimums (2 photos, 1 video) are code constants for every service.

**Derived**

- Crew passwords look like `Axx4821$`: the first three letters of the name, capitalised, padded with `x`.
- Working hours are required for all seven days, `HH:MM`, start before end. Mobile numbers are 10 digits, unique across all logins.
- A crew password reset ends the crew member's sessions and clears the lock. Unlock alone keeps the password.
- Scheduler: cutoff is soft (a late job is placed and flagged). Only Active subscriptions create demand, nothing before `first_service_date`. Unfreeze keeps assignments but does not lock them. The unfreeze code is the constant `unfreeze`. A run defaults to 7 days from the given start. One schedule per society and start date.
- Skip and pause act on jobs the scheduler has already planned, so they reach only the planned weeks. A paused visit's jobs are set to Skipped.
- Renewal date is `first_service_date` plus paused days plus 30 per cycle. A skip inside a pause is merged. "Paused" is computed at read time. Over due starts the day after the due date. Add-on payments never make a subscription Inactive. A cutoff change on a frozen day is saved as Requested.
- Invoice number is `PRV` + month + year + last 4 of the mobile + 4 random digits. The invoice is a JSON record shown in a dialog.
- Complaints: the customer may reply until Resolved; the admin may set any status in any order. Check-in is due in the last 4 days of the 30-day cycle. A re-rating of a visit replaces the earlier one. Alert read state is shared by all admins.
- Uploads: photo under 10 MB, video under 25 MB. An unconfirmed request older than 30 minutes does not block completion. Reassign does not check attendance or capacity.
- The customer vehicle screens come from the customer slice. The people slice's own vehicle screens are not routed.

## Known gaps

- Crew: attendance and working-hours management (`CRW-MGR-04`, `CRW-MGR-05`), vehicle photo on the card (`CRW-SCH-03`), push refresh and reassign push (`CRW-SCH-08`, `CRW-SCH-09`, `CRW-NOT-05`).
- Customer: vehicle photo and parking edit (`VEH-01`, `VEH-04`, `VEH-07`), crew name and checklist on visit details (`SVC-02`, `SVC-03`), change cutoff action (`CAL-08` in the calendar), default cutoff edit (`SUB-08`), FAQ (`SUP-05`).
- Admin: crew deactivate and edit (`ADM-CRW-03`, `-05`, `-08` to `-15`), session management (`ADM-CRW-21`), trainee pairing screen (`ADM-CRW-19`), add-on catalogue (`ADM-ADD-01`), resolving Requested cutoff changes (`ADM-SCH-22`).
- The scheduler has no skips and pauses as demand, no alerts, and no Daily or Monthly period preferences.
- Real QR rendering for UPI (no QR package), and playing videos in the app (they open in the viewer).
- The web portal is untouched.

## Things to look at first in review

1. `services/api/app/changes/sql_gateway.py`: skips and pauses are done by changing job statuses, with no separate state for "paused".
2. `services/api/app/customer_reads/sql_repository.py`: the status names are mapped between the scheduler and the customer screens, and proof is empty until the media tables are joined in.
3. `apps/mobile/tool/gen_api.dart`: the generator now skips unsupported models and endpoints silently. Check that nothing you need is missing from `api.g.dart`.
4. The new screens each read English text from a small Dart strings file, mirrored by an ARB fragment in `lib/l10n/fragments/`. The fragments are also merged into `app_en.arb`. Swapping the screens over to `AppLocalizations` is left.
5. `apps/mobile/pubspec.yaml`: `camera`, `image_picker`, `video_compress`, `sqflite`, `connectivity_plus`, `url_launcher`, `table_calendar` and `path_provider` were added. `workmanager` was left out: the upload queue resumes on app open and on a connectivity change.
