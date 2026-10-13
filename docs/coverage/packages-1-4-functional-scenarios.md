# Packages 1–4: prepared functional scenarios

Code and scenario/test sources written on 13 October 2026. **Not executed.** Use an isolated development environment and test accounts; apply migrations there only after the owner asks for validation. These scenarios complement the API/component scripts and queue tests; they are not claims of device or live-provider coverage.

## P01: completed-visit rating

Arrange two customers, one completed visit owned by each, and one unfinished visit. Sign in as customer A. Rate A's completed visit, then edit the rating; the admin report must contain one updated record. Attempt B's completed visit, an unknown ID and a malformed ID: reject with the same ownership/selection error and save nothing. Attempt A's unfinished visit: reject with visit_not_completed. Try the endpoint as crew/admin: reject by role. Script sources: services/api/tests/support/test_rating_authorization.py and the updated rating/tag scenario in test_support.py.

## P02: checklist history

Create an assigned job, tick its checklist and complete it using the required proof. Capture both crew and customer checklist names, order and timestamps. Rename/reorder/deactivate items and add an item in the directory. Reopen the completed visit: preserve the captured definition/times. Create another job after the edits: use the new active definition. An issued unfinished job retains its issued definition and cannot accept newly introduced keys. On a disposable legacy database upgrade, inspect checklist_snapshot.legacy=true; previously changed labels cannot be reconstructed and use the documented current-label/key fallback. Scripts: visits/test_checklist_snapshots.py, updated test_crew_jobs.py and the existing migration/model parity suite.

## P03: billing

Keep an old Received plan payment. Inactivate → reactivate to Activating → activate with a new first-service date: create one new Due payment at that date with a 30-day cycle. Repeat activation: reject without another payment. Missing date or an existing cycle must fail without changing subscription state. Historical old pauses/debt must not shift or immediately inactivate the new cycle. An upcoming first-cycle payment must not be moved to renewal by the billing cron.

For each of Due, Initiated and Over due, create an unpaid renewal payment, pause three days before renewal and inspect payment/cycle/due dates immediately, before any cron. Move forward three days without changing status; cancel the future pause to restore dates. End a running pause early: retain elapsed pause days and remove only the remaining shift. Received and voided records must remain unchanged. Multiple future payments must retain unique cycle keys. Change a subscription from an interior-inclusive plan to an exterior-only plan through the portal: Save settings must succeed, preserve the current cycle and defer the plan/price switch to renewal. Scripts: billing/test_gap_billing.py, billing/test_billing.py and customers/customers.test.tsx.

## P04: uploads and strict boundaries

Sign in as crew A and enqueue proof while offline. Restart the app and verify A's queued files/tickets remain. Sign out and sign in as B: A's items must not be listed, sent or confirmed by B. Switch while a request/send is pending: stop subsequent API stages; a 401 must never retry using B's credentials. Return as A: resume and delete the local file only after confirmation. Upgrade a version-1 queue: unowned legacy entries remain quarantined; do not assign them to the first login. Files for new entries live under the owner's uploads directory. Re-check closed-job upload rejection. Native SQLite/file upgrade, offline/restart and account-switch behavior remain device validation milestones.

Photos/videos at one byte below 10/25 MB may be accepted; exact-limit and larger files must be rejected by capture validation, request, signed local PUT and confirmation. Profile/vehicle/complaint photo paths use the same backend rule. RC documents retain their separate inclusive 5 MB limit. Check Android/iOS gallery/camera HEIC and compressed video separately; accepted MIME types do not prove native decoding. Scripts: media/test_uploads.py, crew/queue_test.dart, crew/queue_store_test.dart and crew/models_test.dart.
