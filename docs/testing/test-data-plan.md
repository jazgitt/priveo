# Manual and E2E test data

## Hosted dev dataset

The manual `seed-test-data` GitHub Actions workflow uses
`services/api/scripts/seed_shared_test_data.py` to add the same 39 families to
the configured dev PostgreSQL database. It uses the existing `DATABASE_URL`
secret and a separate `TEST_DATA_PASSWORD` secret. It requires schema revision
0028 and the existing single `priveopapa` Admin. It adds synthetic societies,
plans and scenarios atomically, without resetting existing data, directory
settings or Admin credentials. It records scenario snapshots in
`shared_test_data_manifest`; repeat runs preserve existing scenario edits and
passwords. It does not support deleting or refreshing shared scenarios.

The workflow verifies the accounts through the hosted API and uploads the
`hosted-test-accounts` artifact containing `hosted-accounts.md` and
`hosted-manifest.json`. Download them into `.local/test-data/` for manual use.
The account sheet does not include passwords. Customer and Crew fixture
passwords are maintained in the GitHub Actions `TEST_DATA_PASSWORD` secret;
Admin keeps its existing password. Normal hosted cron/billing jobs may change
the seeded payment and scheduling states over time.

Changing the GitHub secret alone does not change stored passwords. To apply a
new fixture password, run `seed-test-data` with `sync_passwords=true`. This
explicit mode updates only verified synthetic Customer/Crew accounts, clears
failed-login blocks, and ends their existing sessions. It preserves all
scenario records, Admin credentials and the intentionally locked R04 fixture.

The original local SQLite seeder below retains its isolation and reset guards.

## Review of the requested scenarios

The original 16 cases are retained as **C01–C16** in the [executable catalogue](../../tools/test-data/scenarios.json). A plan provides daily **external** cleaning and, when included, weekly **internal** cleaning. Deep Spa is purchased separately. Multiple add-ons currently mean multiple bookings of Deep Spa; this application does not yet have several distinct Spa service types.

Keep three dimensions independent: vehicle active/inactive, subscription Active/Activating/Inactive, and add-on Requested/Scheduled/Completed/Cancelled/Missed. Payment states are **Due, Initiated, Received, Over due**. Cancelled unpaid add-ons have a voided payment, rather than an invented fifth payment status. Customers with no subscription owe no plan payment; they can owe standalone Spa payments.

Your vehicle counts needed one correction: case 14 now has **five vehicles: two with Active subscriptions and three with Inactive subscriptions**. All five vehicle records remain active. C25 separately tests an inactive vehicle record with an Active subscription.

## Seeded families

There are **39 scenario families**. Each has a synthetic customer, its own society and a Manager, Member and paired Trainee. R03/R04 have extra crew for attendance/account variants. These dependencies make each scenario independently refreshable. Names start with `TEST`, customer emails use `priveo.test`, and registrations/mobile numbers are synthetic. There is exactly **one Admin login: `priveopapa`**.

| IDs | Seeded data | Manual checks / future UI assertions |
|---|---|---|
| C01 | Owned vehicle, no subscription or payments | Account details; standalone Spa entry; no plan billing |
| C02 | External + weekly internal plan, no add-ons | Plan inclusions, internal day, calendar, subscription |
| C03–C04 | One/two completed Spa bookings and Received payments/invoices | Add-on history; invoice preview; service detail |
| C05–C07 | Requested, Scheduled and mixed Completed bookings | Pending/completed badges; dates; independent payment state |
| C08 | Four unsubscribed vehicles, standalone Spa, four payment states | Standalone ownership; payment detail; no plan payment |
| C09 | Four subscribed vehicles, four payment states | Per-vehicle billing; Admin payment review |
| C10 | Active and cancelled skips | Calendar; unskip; cancellation history; extensions |
| C11 | Three vehicles, current/future/cancelled pauses | Pause badges; dates; resume and unaffected vehicles |
| C12 | Raised/In progress/Resolved complaints; one older than four hours | Customer thread; Admin status/note; escalation action |
| C13 | Five Active subscriptions | Vehicle navigation and long lists |
| C14 | Two Active + three Inactive subscriptions | Subscription badges; reactivation; vehicle/subscription distinction |
| C15 | Five vehicles with mixed payment states | Vehicle filtering and invoice ownership |
| C16 | Five vehicles with independent skips and pauses | No cross-vehicle changes; dates and extensions |
| C17 | External-only plan | No internal service; correct price/inclusions |
| C18 | Terms/onboarding incomplete, existing password | Onboarding gates and confirmation; this is not a fresh OTP account |
| C19–C20 | Activating and overdue Inactive subscriptions | Activation, payment confirmation and reactivation actions |
| C21 | Requested/Scheduled/Missed/Cancelled Spa | Cancellation hides voided debt; missed job outcome; reschedule action |
| C22–C23 | Three months of completed history, with/without ratings/check-in | Paging; rating eligibility; duplicate rating/check-in rejection |
| C24 | Plan change pending next cycle | Current plan remains visible; effective-date handling |
| C25 | Inactive vehicle record, Active subscription | Customer vehicle list hides inactive vehicle; Admin can inspect it |
| C26 | Two owned vehicles in different societies | Each vehicle keeps its society; filters and ownership |
| C27 | Unknown imported registration/plan, unmatched old Spa, legacy invoice | Unknowns remain unknown; historical GST not fabricated |
| C28 | Customer without vehicles | Empty home/account; Admin adds first vehicle |
| C29 | Read/unread service messages and a disabled renewal preference | Inbox badge/deep-link; mark read; preference persistence |
| R01 | Five today's job outcomes; external/internal jobs; paired Trainee; history | Member cards; checklist/timing; Trainee sees paired Member jobs |
| R02 | No issued jobs | Empty day and zero counters |
| R03 | Sick/Leave/Late start crew exceptions | Manager attendance and adjusted capacity |
| R04 | Inactive crew and locked crew login | Disabled/locked login; Admin reset/unlock action |
| R05 | Ten-minute working windows, twenty-minute unassigned job | Genuine capacity shortage; needs-scheduling; manual placement |
| R06 | Draft plan visit and Frozen scheduled Spa | Draft hidden from Crew; freeze publishes; frozen changes require review |
| A01 | Initiated/Received payments, 18% mock GST invoice, read/unread alerts | Admin Mobile quick actions; Web confirm/invoice; unread badge |
| A02 | Complaints, ratings, feedback, check-ins, history | Admin Web reports and Mobile read views |
| A03 | Operations failures, skipped-job extension, unassigned work | Resolve/skip/retry; preserve original outcome; audit after action |
| A04 | Admin-created customer with no subscription and incomplete onboarding | Customer editing; standalone purchase; no fabricated plan |

Use the generated manifest for exact account names and entity IDs. Customer emails follow `test.c07@priveo.test`; Crew logins are listed in order **Manager, Member, Trainee**, then extra Members. All fixture Customers/Crew use `TEST_DATA_PASSWORD`. Admin uses `TEST_DATA_ADMIN_PASSWORD` at first initialization. Existing Admin credentials are preserved by every refresh.

## Cases requiring actions or additional fixture work

These are part of the E2E plan, not claims that database seeding has tested them:

- Fresh OTP/password setup, resend/expiry, wrong-password lockout, password reset, session expiry and logout-all. Use the local logging email sender and mock code `246810`.
- Skip/unskip, pause/resume, add-on change/cancel, overlap merging, billing-cycle extension, duplicate retries, and cutoffs immediately before/at/after the IST boundary. `--as-of` moves fixture dates; it **does not freeze the running application's clock**.
- Actual photo, RC, complaint attachment and video files; confirmation, failed/missing upload, size/type limits, signed URL expiry and interrupted upload. Seeded historical Completed jobs have checklist/timing records **without proof files**. They are historical display fixtures, not valid examples for testing completion validation. Upload real sample proof through the app for those tests.
- Device SQLite upload queues, airplane mode, reconnect, retry, app restart and login-owner changes. These cannot be created by the server seed alone.
- Customer first/last renewal cycle, leap day/month/year rollover, invoice rounding/IGST variants, Received payments without an issued invoice, paid cancellation/credit and operations retry chains. Add focused variants before automating those branches.
- Automatic planner disabled/enabled/time/error/retry cases, overdue-complaint alert generation, empty Admin reports, and Admin global settings/catalogue variants. Apply those profiles **sequentially** on the one Admin account and reset between profiles. Initial data leaves automatic planning disabled and email preferences disabled.
- Inactive societies/catalogues, deactivated/renamed checklist/options and preservation of issued/historical snapshots; invalid registrations and cross-role/cross-society access.
- Real email/S3/native push require a separate configured integration environment. The local fixtures do not prove provider delivery.

The catalogue also records these action-only cases. Expanding a scenario must update its expected state, manifest and integrity/API checks together.

## Commands

Run from the repository root. This tool **never reads `DATABASE_URL`** and initially supports a dedicated local SQLite database. It refuses to adopt any existing unmarked application database. It creates schema from current SQLAlchemy metadata for local fixtures; it does not apply or validate production Alembic migrations.

Choose local-only test passwords in this terminal. Example synthetic credentials below are for a disposable test environment:

```powershell
$env:ENVIRONMENT = 'dev'
$env:TEST_DATA_PASSWORD = 'PriveoFixture123!'
$env:TEST_DATA_ADMIN_PASSWORD = 'PriveoAdminTest123!'

# List or preview; no database writes or password requirement.
services/api/.venv/Scripts/python.exe services/api/scripts/test_data.py --list
services/api/.venv/Scripts/python.exe services/api/scripts/test_data.py --refresh C07,R01 --dry-run

# Initialize a new empty dedicated file and load every scenario.
services/api/.venv/Scripts/python.exe services/api/scripts/test_data.py --database-file .local/test-data/manual.sqlite3 --init --refresh all --output .local/test-data/manifest.json

# Reset selected scenarios, removing changes made while testing those scenarios.
services/api/.venv/Scripts/python.exe services/api/scripts/test_data.py --database-file .local/test-data/manual.sqlite3 --refresh C07,R01 --output .local/test-data/manifest.json

# Reset all scenario data while keeping global settings/catalogue edits and Admin state.
services/api/.venv/Scripts/python.exe services/api/scripts/test_data.py --database-file .local/test-data/manual.sqlite3 --refresh all --output .local/test-data/manifest.json

# FULL fresh start: stop the test API first. Resets global settings/catalogues,
# manually added records and sessions; preserves the single Admin's password.
services/api/.venv/Scripts/python.exe services/api/scripts/test_data.py --database-file .local/test-data/manual.sqlite3 --fresh --output .local/test-data/manifest.json

# Optional date anchor (fixture dates only).
# Add --as-of 2026-11-01 to a refresh command.

# Export a readable account sheet after a refresh.
services/api/.venv/Scripts/python.exe tools/test-data/export_accounts.py --manifest .local/test-data/manifest.json --output .local/test-data/accounts.md
```

Selected refreshes are atomic across the requested scenarios. They remove descendants created during manual testing, including sessions and complaint alerts. Other scenario state/manifest entries remain intact. A full fresh start builds and validates a replacement before replacing the marked file; stop the API first to release Windows file handles. Keep the same `TEST_DATA_PASSWORD` across partial refreshes, otherwise retained scenarios still have the old password.

Start the isolated API in another terminal:

```powershell
./tools/test-data/start-api.ps1 -DatabaseFile .local/test-data/manual.sqlite3
```

The launcher verifies the database marker, selects logging email, disables real Resend delivery, uses a local media directory and restores process environment variables on exit. It binds port 8000 to allow phone access. For Admin Web, run `npm run dev` in `apps/web` and open `http://localhost:5173/portal/`; its existing Vite proxy defaults to the local API. For the phone, use your computer's LAN address, with the phone on the same network:

```powershell
powershell -ExecutionPolicy Bypass -File apps/mobile/tool/push_apk.ps1 -ApiUrl http://YOUR-PC-LAN-IP:8000
```

That APK uses the current checked-out code and the explicit local API URL. An existing APK configured for the hosted API will not see this local dataset. No APK build, deployment or existing application-database refresh is part of fixture verification.

Run the supplied API smoke suite against that running test API:

```powershell
services/api/.venv/Scripts/python.exe tools/test-data/api_smoke.py --base-url http://127.0.0.1:8000 --manifest .local/test-data/manifest.json
# Add --scenarios C07,R01 for a focused check.
```

This exercises real HTTP login/role reads, vehicles/calendar/visits/payments, Crew views, Admin reports/scheduling boards and customer ownership. Logins create sessions, and normal GET reconciliation can update billing data; refresh afterwards for a baseline. **It is not a browser or phone UI E2E suite.** The unit/integration fixture tests also exercise the distinct Admin Web cookie login.

## E2E implementation order

1. **Fixture foundation (implemented):** catalogue, deterministic IDs, full/partial reset, manifest, isolated launcher, reset/integrity tests and API smoke runner. Verify all scenario families are readable through the application's real routes.
2. **Manual data completion:** export the human-readable account sheet using the command above, add actual photo/RC/video/complaint files and the remaining targeted variants, and record observed manual results against IDs.
3. **Admin Web UI E2E:** add Playwright against the isolated API. Start with login/customer search, payment confirmation/invoice, complaint resolution, schedule draft/freeze and settings. Use one Admin login with sequential tests for shared/global settings.
4. **Customer Mobile UI E2E:** extend Flutter `integration_test` to choose accounts from this manifest. Automate home/vehicle navigation, standalone/subscription payments, add-on lifecycle, skip/pause, complaints, rating/check-in and invoice display. Existing login integration tests have hard-coded demo IDs and need this adaptation.
5. **Crew + Admin Mobile UI E2E:** automate Manager/Member/Trainee views, checklist/proof/completion, outcomes/reassignment/attendance and Admin quick actions. Add device offline/restart tests separately from API tests.
6. **Boundary/integration runs:** controlled IST clock cases and idempotency; then configured provider delivery and device permissions. Publish per-scenario results, screenshots and traces. Reset the relevant fixtures before every mutating test; never rely on prior test order.

## Verification

Fresh validation on 13 October 2026: **13 targeted tests passed**, including all 39 families through real API routes. The suite checks foreign keys, one Admin, standalone payment states, five-vehicle mixtures, invoice prerequisites, trainee pairing, stable IDs, partial reset isolation, removal of manual actions/composite-key preferences, preservation of Admin credentials, full fresh-start settings reset, failure rollback for both reset modes, production guards and placeholder configuration. API compatibility includes Customer, Crew, Admin bearer routes, check-in eligibility and Admin Web cookie auth. Ruff checks and skill metadata validation pass; the PowerShell launcher parses successfully. Phone/browser UI E2E, live HTTP smoke against a separately running process and real provider checks remain pending.
