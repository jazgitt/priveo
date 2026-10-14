# Claude handoff — Priveo

Prepared: 14 October 2026 (Asia/Kolkata). Repository checkpoint: `cb2ed297bc1a3e0e47393c10a8fd244a03221e43` on `main`.

## Start here

This is the current handoff entry point. It supersedes the resume instructions in [codex-handoff-plan.md](codex-handoff-plan.md). Older documents contain useful implementation detail but also stale statements about uncommitted work, deferred tests, unresolved standalone Spa behavior and work not yet merged.

The working tree was clean before this handoff was added. The integrated implementation and coverage/fixture tooling are committed on `main`. The last code change added explicit password synchronization for hosted synthetic Customer/Crew accounts. No application changes, tests, migrations, workflow dispatches or deployments were performed while preparing this document. Remote branch alignment, GitHub run results and the currently deployed revision were not checked during preparation.

The owner has requested a handoff, not a new implementation or deployment. Resume according to their next instruction. A practical next phase is manual browser/phone validation using the scenario accounts, followed by UI E2E and remaining integration work.

## Project and workspace

- Workspace: `C:\Udemy\AI3weeks\priveo`; Windows PowerShell.
- `services/api`: Python API, SQLAlchemy, Alembic, PostgreSQL; SQLite used for isolated tests.
- `apps/mobile`: Flutter Customer, Crew and Admin applications; dev/prod Android flavors.
- `apps/web`: React/TypeScript Admin portal, served at `/portal/` by the API deployment.
- `packages/api-contract/openapi.json`: exported API contract; mobile generation tools consume it.
- `docs/reqs`: source requirements and owner decisions.
- `docs/coverage`: requirement audit, implementation packages, functional scenarios and measured coverage.
- No `AGENTS.md` was found by the repository file search during this handoff. Check again if the checkout changes.
- There is no root `package.json`; run web npm commands from `apps/web`.

## Latest commits and what they changed

| Commit | Result |
|---|---|
| `cb2ed29` | Hosted synthetic Customer/Crew password synchronization, failed-login reset and session revocation through an explicit workflow option. |
| `11ef9f4` | Additive shared-dev scenario seeder, hosted API verification and account artifacts. |
| `fda66da` | Pinned deployment CLI and patched `tar` dependency override in `tools/deploy`. |
| `970ffee` | Deployment smoke test checks actual Crew visits. |
| `a443096` | Portal readiness retries after Vercel deployment, including `/portal/customers`. |
| `82e2c6f` | Automatic-planning and overdue-complaint cron configuration changed to daily at 9 PM IST. |
| `00243f3` | Merged `integration/complete-build` into `main`. |
| `ccf0daa` | Measured per-area coverage and local scenario fixture/reset tooling. |
| `2c3ba73` | Requirement gap implementation, owner decisions and audit updates. |

Commit presence establishes source state; successful remote workflow execution requires separate evidence.

## Implemented baseline

The earlier Steps 1–4 cover customer administration, onboarding, subscriptions/payments, Deep Spa scheduling, operations outcomes/history, retry links, billing extensions and mobile Admin actions.

The requirement-gap packages added rating ownership/state checks; immutable issued checklist snapshots; reactivation and pause/payment-date fixes; owner-partitioned upload queues; resumable onboarding review; amount-bearing UPI QR/payment summaries; customer Home/calendar/account improvements; Admin pagination, session metadata, complaint proof and imported history; logout-all audit; bounded cross-client refresh; Admin email preferences and durable Resend outbox; and complaint escalation logic.

Owner-approved additions include standalone Spa for owned vehicles without subscriptions, editable five-step checklist samples, Admin mobile checklist viewing, 18% inclusive GST invoice snapshots, read-only seeded seller identity, preserved historical category names, configurable billing policies and default-disabled automatic next-period planning.

The dated source audit reports **392 Implemented, 34 Partial and 0 Open** across **426 requirement rows**. This is source coverage, not proof that every acceptance journey has passed. See [requirements-audit.md](coverage/requirements-audit.md) and [gap-implementation-plan.md](coverage/gap-implementation-plan.md).

## Owner decisions to preserve

Read [owner-decisions-2026-10-13.md](reqs/owner-decisions-2026-10-13.md) before changing business behavior.

- Admin creates customers and vehicles; no public self-signup. A no-subscription vehicle has no plan payment.
- Standalone Deep Spa follows subscriber Spa booking/payment/scheduling/cancellation/outcome/proof rules. Scheduling is independent of payment. Legacy unlinked records retain their known and unknown data.
- Issued checklists, invoice tax details and historical feedback categories retain their snapshots after catalogue edits.
- GST is 18% inclusive; tax split and supplier environment values are mock/configurable pending final business values. Do not fabricate historical GST.
- Automatic planning is disabled by default; Admin enables it and chooses an IST time.
- Billing cycle/deadline/unfreeze policies are configurable. Seller invoice identity is seeded/read-only in MVP.
- Existing environment values must be preserved. Placeholder provider keys do not establish live delivery.

The decision document's original “tests/builds deferred” wording describes that coding checkpoint. Later tests and coverage were authorized and recorded. Do not infer a blanket current prohibition or authorization for new live changes from that historical wording.

## Recorded validation and limits

The saved 13 October checkpoint records:

| Suite/check | Recorded result |
|---|---|
| Backend on SQLite | 494 tests passed |
| Flutter | 1,433 passed; 11 skipped |
| Admin Web | 99 passed |
| Flutter analysis | Passed |
| Portal TypeScript / production build | Passed |
| Local fixture targeted suite | 13 tests passed |

| Area | Executable line coverage |
|---|---:|
| Customer Mobile | 90.22% |
| Crew Mobile | 90.09% |
| Admin Mobile | 91.17% |
| Admin Web | 90.52% |
| Shared backend | 92.89% |
| Shared mobile | 92.85% |

Evidence: [unit-test-coverage.md](coverage/unit-test-coverage.md), [unit-test-coverage.json](coverage/unit-test-coverage.json), and [test-data-plan.md](testing/test-data-plan.md). The coverage report's “uncommitted” wording is historical; that work was committed in `ccf0daa`.

These totals are not a freshly executed full-suite result for `cb2ed29`. Later commits add hosted fixture tests, including password-sync preservation/session checks; their execution result was not independently retrieved for this handoff. Line coverage does not imply the same branch/function coverage, native acceptance, live provider delivery or production readiness.

## Latest work: test data and passwords

Read [test-data-plan.md](testing/test-data-plan.md) for exact commands, scenario descriptions and reset scope. The catalogue is [tools/test-data/scenarios.json](../tools/test-data/scenarios.json).

There are **39 families**: Customer `C01–C29`, Crew `R01–R06`, Admin `A01–A04`. They cover subscription/no-subscription, payment/add-on states, skips/pauses, complaints, multi-vehicle cases, onboarding/history, legacy data, inbox, Crew outcomes/capacity and Admin actions. The single Admin username is **`priveopapa`**.

Local fixtures:

- `services/api/scripts/test_data.py` owns a marked, dedicated SQLite database. It does not read `DATABASE_URL` or validate Alembic migrations.
- Supports initialization, selected refresh, all-scenario refresh and a full fresh start. These modes have different preservation rules; follow the plan.
- `tools/test-data/start-api.ps1` launches the isolated API with logging email and local media.
- `tools/test-data/api_smoke.py` exercises real HTTP routes using a manifest. It is not browser/phone UI E2E.
- Local account/manifest/database artifacts are ignored files under `.local/test-data/`.

Hosted fixtures:

- `.github/workflows/seed-test-data.yml` is manually dispatched and uses `services/api/scripts/seed_shared_test_data.py`.
- Uses GitHub secrets `DATABASE_URL` and `TEST_DATA_PASSWORD`, variable `API_DEV_URL`, and existing Admin credentials (`MOCK_ADMIN_PASSWORD` for smoke verification).
- Requires schema revision 0028 and the existing single Admin. Adds missing scenarios atomically and preserves existing records/manual edits. Shared scenarios have no delete/refresh mode.
- Writes `shared_test_data_manifest` snapshots; uploads `hosted-test-accounts` containing `hosted-accounts.md` and `hosted-manifest.json`.
- Changing `TEST_DATA_PASSWORD` alone does **not** update existing password hashes.
- Explicit `sync_passwords=true` updates verified synthetic Customer/Crew passwords, clears failed-login blocks and ends their sessions. It preserves scenario records, Admin credentials and the intentionally locked R04 account.
- Password-sync smoke uses a selected scenario subset; default seed verification uses the full manifest.

Local hosted account/manifest artifacts were present under `.local/test-data/hosted/` when inspected. Their presence does not establish the current database state or a successful latest workflow run. Credentials stay in approved secret/local storage; do not copy passwords, tokens, real customer data or `.env` contents into this document or commits.

Fixture limits: historical Completed jobs have checklist/timing data but no real proof media. Upload actual sample media for completion/proof tests. `--as-of` anchors fixture dates; it does not freeze the application clock. Hosted billing/cron execution can change fixture states over time.

## Deployment and cron checkpoint

Inspect [.github/workflows/api-deploy.yml](../.github/workflows/api-deploy.yml), [services/api/vercel.json](../services/api/vercel.json) and [tools/deploy/README.md](../tools/deploy/README.md).

The configured dev path uses Vercel and PostgreSQL/Neon, with an AWS alternative selected by `DEPLOY_PROVIDER`. Vercel `--prod` publishes the configured dev API; the flag alone does not mean business production. The Vercel workflow migrates/seeds the configured database, builds the portal, deploys, retries portal readiness for up to three minutes and runs API smoke. Deployment tools install from the committed lockfile.

Current committed cron schedules include automatic planning and overdue complaints at `30 15 * * *` UTC, which is **9 PM IST daily**. The earlier five-minute escalation/minute planner host assumptions are not satisfied by this daily configuration. Verify acceptable timing, planner eligibility and freeze ordering before claiming automatic scheduling or four-hour escalation acceptance.

Migrations 0024–0028 exist in source. Older handoff statements that they are unapplied predate the merge/deployment work; their current hosted application status is **unverified here**. Check deployment logs/current schema before applying or editing migrations. Never revise an already-applied migration based only on an old note.

## Remaining work and recommended sequence

1. Establish live evidence: current deployed build, latest `api-deploy` and `seed-test-data` results, schema revision and account artifact freshness. Use read-only checks first; record run IDs and revision evidence.
2. Validate manual Admin Web, Customer, Crew and Admin Mobile journeys against the intended environment. Record results by scenario ID. Include payment/invoice, standalone Spa, schedule freeze, proof, complaints, skips/pauses and account navigation.
3. Add actual photo/RC/video/complaint samples and missing action/boundary variants. Keep the manifest, expected state and fixture tests consistent.
4. Add Admin Web UI E2E, then manifest-based Customer/Crew/Admin mobile integration tests. Global settings/Admin tests need sequential isolation. Use local resettable fixtures for mutating automation.
5. Finish remaining source gaps: native PDF save/share, inline proof video, immediate cross-client transport and real native push/provider/token/notification navigation work. Existing foreground refresh is bounded, not immediate.
6. Verify actual Resend/S3/FCM/APNs integration, cron timing, PostgreSQL locking/idempotency, offline/restart/owner-switch uploads and IST cutoff boundaries in the appropriate environment.
7. Complete release/security/device checks, migration recovery, Android distribution and eventual iOS signing/TestFlight after inspecting existing account setup.

Prepared acceptance scenarios:

- [Packages 1–4](coverage/packages-1-4-functional-scenarios.md)
- [Packages 5–7](coverage/packages-5-7-functional-scenarios.md)
- [Packages 8/11](coverage/packages-8-11-functional-scenarios.md)
- [Standalone Spa / planning / GST](coverage/standalone-planning-gst-functional-scenarios.md)

## Useful commands

Run each command from the stated directory. Follow current owner scope before starting workflows or changing shared data.

```powershell
# Repository root: establish the checkout and recent history.
git status --short
git branch --show-current
git log -12 --oneline

# Repository root: read-only GitHub run inspection, if gh is authenticated.
gh run list --workflow api-deploy.yml --limit 5
gh run list --workflow seed-test-data.yml --limit 5
# Use gh run view <run-id> and inspect failures/artifacts as needed.

# Repository root: rerun measured coverage when requested.
.\tools\coverage\run.ps1

# Repository root: list/preview local fixtures without changing a database.
services/api/.venv/Scripts/python.exe services/api/scripts/test_data.py --list
services/api/.venv/Scripts/python.exe services/api/scripts/test_data.py --refresh C07,R01 --dry-run

# Repository root: start the existing isolated local fixture API.
.\tools\test-data\start-api.ps1 -DatabaseFile .local/test-data/manual.sqlite3

# apps/web: local portal (proxy defaults to local API).
npm run dev

# Repository root: build/copy Android dev APK for the specified API.
powershell -ExecutionPolicy Bypass -File apps/mobile/tool/push_apk.ps1 -ApiUrl http://YOUR-PC-LAN-IP:8000
```

For API lint/tests use `services/api/.venv/Scripts/python.exe` from the appropriate working directory; for web checks use `apps/web`; for Flutter checks use `apps/mobile`. See [build-and-release.md](build-and-release.md) for detailed setup, but its feature/status lists are older than this handoff. `TEST_DATABASE_URL` must target a disposable database because the test setup clears it.

## Instructions for the next Claude session

Read this document, inspect the working tree, then read the requirement/scenario documents relevant to the owner's next task. Preserve existing work and business decisions. Distinguish implementation, executed automated validation, manual acceptance and live deployment evidence. Update the handoff with exact changes, checks and remaining limitations when stopping. Do not resume from stale “uncommitted,” “not merged,” or “standalone undecided” instructions in historical notes.
