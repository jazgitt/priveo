---
name: priveo-test-data
description: Generate or reset Priveo synthetic manual and E2E test data, for a full fresh start or selected Customer, Crew and Admin scenarios. Use the repository fixture tools; excludes production imports and database migrations.
---

# Priveo test data

Find the Priveo repository from the current workspace; the usual Windows location is `C:\Udemy\AI3weeks\priveo`. Read `docs/testing/test-data-plan.md` and `tools/test-data/scenarios.json` there. They are the maintained scenario definitions, rules and exact commands. Use `services/api/.venv/Scripts/python.exe` and `services/api/scripts/test_data.py`; do not create a second competing seed script.

## Choose the reset scope

- **Preview/list:** `--list`, or `--refresh C07,R01 --dry-run`. No credentials or database writes.
- **Selected scenarios:** `--database-file <file> --refresh C07,R01 --output <manifest>`. Reset those families and dependent test actions while preserving others, global catalogue/settings and Admin credentials/state.
- **All scenario baselines:** `--refresh all`. Preserve global settings/catalogue edits and Admin state.
- **Full fresh start:** `--fresh`. Reset the entire marked test file, including global settings, sessions and manually added records. Preserve the one Admin login/password. Stop the test API first so Windows releases the database file.
- **First creation:** `--init --refresh all` on a new empty dedicated SQLite file.

For an ambiguous “full refresh,” clarify whether settings/catalogue edits must reset; do not silently substitute `--refresh all` for `--fresh`. Respect an already stated choice. If the target is missing, prepare/preview commands and ask for the dedicated test-file location while continuing independent work. Authorization to generate scripts is not authorization to reset an unspecified application database.

## Execute and verify

For explicitly requested hosted dev seeding, read the Hosted dev dataset
section in `docs/testing/test-data-plan.md`. The separate reviewed
`seed-test-data` workflow uses the existing database secret and additive
`seed_shared_test_data.py` implementation. It preserves all existing records,
settings and Admin credentials. Do not use the SQLite reset tool for hosted
databases. Check the workflow's hosted API verification result and retrieve
its password-free account artifact. Shared refresh/deletion is not supported.
If the user explicitly requests applying a changed fixture password, run that
workflow with `sync_passwords=true`. This rotates only verified synthetic
Customer/Crew credentials, clears login blocks and ends their old sessions.
Admin credentials and scenario data remain intact; the intentionally locked
R04 crew fixture stays locked. A changed secret alone does not update accounts.

The tool requires an explicit file and a fixture marker, and never consumes `DATABASE_URL`. Only local SQLite and `ENVIRONMENT=dev` are supported. Do not point it at production or try to bypass the marker. PostgreSQL/shared dev seeding needs a separate reviewed implementation.

Read `TEST_DATA_PASSWORD` and, for first initialization, `TEST_DATA_ADMIN_PASSWORD` from the process environment. Do not print secrets or tokens, copy real `.env` values, or silently change retained accounts' passwords. Use the same fixture password on partial refreshes. Exactly one Admin login, `priveopapa`, serves every Admin variation.

Preview the selected IDs, then execute the authorized scope. Always pass `--output .local/test-data/manifest.json` (or the user's selected manifest path). The manifest retains untouched scenario entries and provides Customer/Crew logins and entity IDs. Report reset IDs/date anchor, manifest path, checks performed and any cases still requiring actions.

For manual access, use `tools/test-data/start-api.ps1 -DatabaseFile <file>`. It disables real email, uses a local media directory and binds the test API for phone access. The APK must use the computer's LAN API address; a hosted-API APK will not see local data. Do not rebuild/deploy the app merely because fixtures were refreshed.

For API smoke checks, use `tools/test-data/api_smoke.py --base-url <test-api> --manifest <manifest> [--scenarios C07,R01]`. These checks create sessions and can trigger normal billing reconciliation. Describe them as API smoke checks, not UI E2E. Run tests when authorized; respect explicit user instructions deferring tests.

## Extend a scenario

Add or update its definition in the catalogue, builder in `services/api/scripts/test_data.py`, meaningful invariants/API checks in `services/api/tests/test_manual_test_data.py`, and the manual/E2E mapping in the plan. Keep IDs stable and data synthetic. Follow application models and owner decisions rather than inventing statuses.

Payment state, subscription state, vehicle activation and Spa service state are independent. No-subscription customers get standalone Spa debt, never fabricated plan payments. Multiple add-ons are multiple Deep Spa bookings. Received invoices use mock 18% GST; legacy unknown tax remains unknown. Issued checklist snapshots and historical feedback labels must survive catalogue edits. Trainees have zero capacity and see a paired Member's jobs.

Server seeding cannot create device offline queues, freeze the running clock, prove native push/provider delivery or supply missing proof files. The initial historical Completed-job fixtures omit media. Route those cases to controlled actions/device fixtures and report the limitation explicitly instead of claiming they are complete.
