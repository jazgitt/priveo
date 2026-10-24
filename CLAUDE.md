# CLAUDE.md

Priveo Car Concierge: a subscription car-care service for housing societies. A Flutter app (iOS and Android) serves customers and crew, with a small set of admin quick actions. Admins use a React web portal. Screens are chosen by the role on the login. See `README.md` for the product summary.

## State of the repo

Latest checkpoint: P01-P07 plus P08/P11 sources and owner-approved P12/GST/sample/planning changes are committed/pushed as `2c3ba73`. The owner authorized full automated tests and coverage improvements on 13 Oct. Fresh executable-line coverage exceeds 90% in every client role and shared runtime area; 494 API tests, 1,433 mobile tests (11 skipped) and 99 portal tests passed. Flutter analysis and the web build pass. See `docs/coverage/unit-test-coverage.md`; subsequent coverage fixes/tests are uncommitted. Audit: 392 Implemented source paths, 34 Partial, 0 Open. Owner decisions in docs/reqs/owner-decisions-2026-10-13.md authorize admin-created no-subscription customers/vehicles and subscriber Spa rules; editable five-step samples with admin mobile view; 18% GST/environment mocks; configurable policies; historical names preserved. Automatic planning is default-disabled, requires admin IST time, creates next configured period draft, preserves existing schedules and retries/alerts errors. Migrations 0024-0028 are unapplied. OpenAPI/Dart generation succeeded; no tests/builds/migrations ran. P08 at-once transport, PDF save/share/inline proof, P10 push, S3/date/security/release work remain pending. Provider keys will be supplied offline; do not claim live integration or ask the resolved business questions again.

The current requirement-level inventory is `docs/coverage/requirements-audit.md` (13 Oct 2026): all 426 ID rows, 67 business rules and 67 entity bullets. It supersedes the previous coverage summaries and adds correctness/UI gaps beyond Step 5. The coverage matrices are now current static audits, not historical snapshots; “Implemented” means a source path was found, not a runtime pass. Related test files do not establish complete acceptance coverage. No tests were run for this audit. The owner subsequently authorized tests; the fresh measured report supersedes the testing deferral, while this requirement audit remains a static snapshot.

As of 13 Oct 2026, development is on `integration/complete-build`, pushed implementation baseline `2c3ba73` plus uncommitted, validated coverage work. Full test execution and coverage are now authorized; use `tools/coverage/run.ps1` for the persistent 90% line-coverage gates. These gates include generated mobile code and do not claim 90% branch coverage. Keep PDF save/share, immediate real-time transport, push/navigation, S3, live configuration and device/release validation pending. The automatic planner is coded/default-disabled; host execution is pending. Migrations 0024-0028 are not applied to application databases. Real email needs Resend configuration; push remains a logging sender and media a local development store. See `docs/coverage/unit-test-coverage.md` for evidence.

Build and test commands (from the repo root):
- API: `cd services/api && .venv/Scripts/python -m ruff check . && .venv/Scripts/python -m pytest -q`. Export the contract with `scripts/export_openapi.py`.
- PostgreSQL checks: from `services/api`, `.venv/Scripts/python scripts/test_postgres.py` creates, tests and stops a disposable local cluster. Set `POSTGRES_BIN` for another PostgreSQL installation. Never use an application database as `TEST_DATABASE_URL`; the test fixtures drop its tables.
- Portal: from `apps/web`, `npm run lint`, `npm test`, `npm run build`.
- App: `cd apps/mobile && flutter analyze && flutter test`. After changing `docs/brand/tokens.json` run `dart run tool/gen_theme.dart`; after changing `lib/l10n/app_en.arb` run `flutter gen-l10n`; after the contract `packages/api-contract/openapi.json` changes run `dart run tool/gen_api.dart` (writes `lib/core/api/api.g.dart`, the app's models and API calls). CI fails if any generated output is stale.
- Database changes go through an Alembic migration in `services/api/migrations/versions`, written by hand. A test checks that the migrations build the tables the models describe.
- Passwords (`ADMIN_PASSWORD`, `MOCK_*_PASSWORD`), the dev sign-in code (`MOCK_EMAIL_CODE`) and `DATABASE_URL` are environment configuration, never committed.

## Tech stack (decided by the owner)

Flutter (Riverpod, go_router, feature folders) for the app. Python FastAPI with PostgreSQL for the API, with the scheduler (OR-Tools) in the same service. AWS Mumbai (ECS Fargate, RDS, S3, EventBridge Scheduler) for hosting. Resend for email (verification codes, password reset codes, welcome email). FCM for push. S3 signed uploads for media with an offline upload queue in the app. A React web portal for admin, with every admin function in MVP, and a limited set of admin quick actions in the Flutter app. Details, supporting choices and risks are in `docs/tech-stack.md`. All choices there are decided; the risks section lists what to watch.

## Layout

- `docs/agent/mani-bond-spec_final.md`: Mani Bond Chief of Staff requirements. `docs/agent/agent-architecure.md`: initial assessment and phased implementation plan. `docs/agent/mani-bond-solution-plan.md`: subsequent solution architecture and technology-stack plan, including the Founder-selected India-only processing, AWS Mumbai hosting, Crawl-plus-voice first release and push-to-talk interaction; read all three before working on Mani Bond. Stack and implementation recommendations remain proposals unless separately approved.
- `docs/reqs/customer-app-functional-requirements.md`: customer app
- `docs/reqs/admin-functional-requirements.md`: admin (functional requirements for the web portal and the mobile quick actions)
- `docs/reqs/crew-functional-requirements.md`: crew
- `docs/tech-stack.md`: technical stack (all choices decided)
- `docs/design/admin-portal-ui-review.md`: the portal's functional review and UI decisions. The portal uses shadcn/ui (`apps/web/src/ui/`), with shared page blocks in `apps/web/src/blocks/`: every change goes through `useAppMutation`, every destructive action through `useConfirm`, long runs through `useTasks`.
- `docs/security-backlog.md`: open findings from the 18 Oct 2026 security review, with what is done and what is planned for security testing.
- `docs/architecture.md`: technical architecture (draft). `docs/build-plan.md`: original phased build plan. Current work (Requirements V2) is recorded in `docs/reqs/owner-decisions-2026-10-23.md`.
- `tools/priveo-reqs/`: a Claude Code mod for the requirements files. It checks IDs after each edit, guards `docs/prototype/` and `.env`, and adds `/ids`, `/open`, `/synccheck`, `/fstatus` and `/priveo-status` (a side pane with the stage counts, open bugs and a role and area breakdown). `/fstatus` tracks each requirement ID through Draft, Backlog, Ready for Dev, In Dev, Unit Tested >95%, Functional Tested and Security Test, with an open-bug count, in `docs/feature-status.json`. A new or changed requirement row goes back to Draft. Load it with `claude --plugin-dir tools/priveo-reqs`. Test it with `claude plugin test tools/priveo-reqs`.
- `docs/prototype/`: interactive prototype HTML, vision deck, marketing images. Read-only source material. The prototype HTML is about 1 MB, so search it with grep instead of reading it whole.

## Rules for editing the requirements

- **Owner decisions win.** Where the prototype disagrees with an owner decision, the requirements follow the owner. The prototype's known differences are listed in `README.md`. Keep that list current when a decision makes the prototype more out of date.
- **Do not decide for the owner.** If something is not stated, ask. If you must fill a gap to keep a requirement workable, mark it **Derived** or **Open** in the Status column and say so in your reply. Never mark your own assumption as **Owner**.
- **IDs:** each requirement has an ID (customer: `AUTH-`, `ONB-`, `PAY-`, `HOME-`, `CAL-`, `SVC-`, `SKIP-`, `PAUSE-`, `SCHED-`, `SUB-`, `VEH-`, `SUP-`, `ISS-`, `CMP-`, `FDBK-`, `CHK-`, `NOTIF-` and others; admin: `ADM-<area>-NN`; crew: `CRW-<area>-NN`). Never renumber. Add new IDs at the end of their group, even if that puts them out of order in the table.
- **Cross-references:** an ID cited in one file must exist in a file. After any edit, check that every cited ID is defined and no ID is defined twice. A one-line grep over the table rows is enough.
- **Keep the three files consistent.** A change in one often needs a matching change in the others: statuses, notifications, the business-rules list, the data-entities list and the "needed by / covered by" table in the admin file. Update section 13 (open questions) and the deferred list when an item is answered or added.
- **Format:** tables with columns ID, Requirement, Status. Plain, short sentences. English only. Only functional requirements.
- **Dates** in the app are `dd-Mon-yy`, for example `07-Nov-26`. Currency is rupees and prices include GST.
- **Version and sources:** bump the version line at the top of a file when its content changes.

## Domain facts to keep straight

- Services: Cleaning-External (20 min, every day), Cleaning-Internal (20 min, on the interior care day), Deep Spa (2 hours). Each service is a separate job. Deep Spa is not in the plan. A subscriber buys it separately as an add-on, proposing one date and a finish-by time. A customer without a subscription can take it as a standalone service; how they do that is not decided yet (`ADD-15`). Scheduling does not wait for its payment in MVP.
- A visit is Completed only when all its jobs are done or skipped.
- Billing cycle is 30 calendar days from the first service date. Payments are manual by UPI (statuses Due, Over due, Initiated, Received). A payment Over due for 7 days makes a subscription Inactive.
- A schedule is frozen once, by 8 PM the day before its first day (a weekly schedule before the week starts). Customers change their schedule until 9 PM the day before. The admin is not bound by the 9 PM rule.
- Ratings are general to the visit and not given to any crew member. No crew member sees a customer's name or mobile number.
- Customers sign in by email: an emailed 6-digit code on first sign-in, then a password. Only customers the admin has created can sign in. Crew sign in with mobile number and password. Admins sign in with a user ID (the first is `priveopapa`) and password. Passwords are never sent by SMS or WhatsApp: the admin sees a new crew password once and hands it over. The admin password comes from `.env`, never from the repo.

## Working conventions

- This project is its own git repo with remote `https://github.com/jazgitt/priveo`. It sits inside the parent `AI3weeks` repo's folder, so run git commands from this folder.
- Nothing is carried over from the user's other projects. Do not assume their tools, hosting or setup. Ask when a choice is needed.
- Commit and push only when the user asks. Never commit `.env` files or secrets.
