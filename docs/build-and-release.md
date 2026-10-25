# Build and release (Phase 0)

**Status:** 10 Oct 2026. Covers the Phase 0a Android path and the start of Phase 1 (real sign-in on PostgreSQL). The `dev` API host is Vercel with a Neon database, and switches to AWS with `DEPLOY_PROVIDER=aws`. iOS (0b) is not built yet. Plan: `docs/build-plan.md`.

## 1. Run it on your machine

| What | Command (from the repo root) |
|---|---|
| API: install | `cd services/api && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"` |
| API: set up the database | Put `DATABASE_URL`, `TOKEN_SECRET`, `ADMIN_PASSWORD` and, for the demo logins, `SEED_DEMO_LOGINS=true` with `MOCK_CUSTOMER_PASSWORD` and `MOCK_CREW_PASSWORD` in `services/api/.env`. To try a customer's first sign-in, add `MOCK_EMAIL_CODE` (any 6 digits). Then `.venv/Scripts/python -m alembic upgrade head && .venv/Scripts/python scripts/seed.py` |
| API: run | `.venv/Scripts/python -m uvicorn app.main:app --port 8000` (reads `.env`) |
| API: add a migration | Change the models, then `.venv/Scripts/python -m alembic revision -m "what changed"` and write the steps by hand |
| API: load the existing customers (one time) | `.venv/Scripts/python scripts/import_customers.py "../../seed/<file>.xlsx"` is a trial run that saves nothing. Add `--apply` to save. Needs `DATABASE_URL`. The spreadsheet holds real customer data and stays in `/seed`, which is git-ignored |
| API: lint and test | `.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m pytest -q`. The tests use an in-memory database and need no setup. Set `TEST_DATABASE_URL` to run them on PostgreSQL; that database is emptied |
| API: isolated PostgreSQL tests | `.venv/Scripts/python scripts/test_postgres.py`. Uses its own temporary cluster, never `DATABASE_URL`. Set `POSTGRES_BIN` if PostgreSQL is not installed at `C:/Program Files/PostgreSQL/17/bin` |
| API: export the contract | `.venv/Scripts/python scripts/export_openapi.py` (writes `packages/api-contract/openapi.json`) |
| API: smoke test a running API | `SMOKE_CUSTOMER_PASSWORD=... SMOKE_CREW_PASSWORD=... SMOKE_ADMIN_PASSWORD=... python scripts/smoke_test.py <url>` |
| App: get packages | `cd apps/mobile && flutter pub get` |
| App: theme from tokens | `dart run tool/gen_theme.dart` (after changing `docs/brand/tokens.json`) |
| App: API client from the contract | `dart run tool/gen_api.dart` (after `packages/api-contract/openapi.json` changes) |
| App: translations | `flutter gen-l10n` (after changing `lib/l10n/app_en.arb`; new slice fragment keys must be merged into that file first) |
| App: analyze and test | `flutter analyze && flutter test` |
| App: test against a live API | `flutter test test/live_api_test.dart --dart-define=LIVE_API_URL=<url> --dart-define=LIVE_PASSWORD=<mock password>`. When the three mock passwords differ, pass `LIVE_CUSTOMER_PASSWORD`, `LIVE_CREW_PASSWORD` and `LIVE_ADMIN_PASSWORD` instead |
| App: sign in as each role on a phone or emulator | `flutter test integration_test --dart-define=API_BASE_URL=<url> --dart-define=LIVE_CUSTOMER_PASSWORD=... --dart-define=LIVE_CREW_PASSWORD=... --dart-define=LIVE_ADMIN_PASSWORD=...` |
| App: run (dev) | `flutter run -t lib/main_dev.dart --dart-define=API_BASE_URL=<url>` |
| App: build and copy to the phone's Downloads | `powershell -ExecutionPolicy Bypass -File apps\mobile\tool\push_apk.ps1` (the phone plugged in by USB; uses the `dev` API unless `-ApiUrl <url>` is given). For phones that block installs over USB. Then install `priveo-dev.apk` from the Files app |

The app has two Android flavors that install side by side: `dev` (`in.priveo.app.dev`, labelled "Priveo Dev") and `prod` (`in.priveo.app`, labelled "Priveo"). A command with no `--flavor` uses `dev`. Add `--flavor prod -t lib/main_prod.dart` for the other.

For actual email delivery, configure `RESEND_API_KEY` and `EMAIL_FROM` using a verified sending domain. Without a provider key, dev uses the logging sender and production verification returns `not_configured`. `MOCK_EMAIL_CODE` is an optional dev override and is ignored in production. No live provider credentials are needed for the test suite.

Each role has one look, whatever the phone's light or dark setting (owner decision, 10-Oct-26): the splash, login and customer screens are dark and follow the prototype; crew screens are plain white; admin screens are cream. **Derived:** the white crew background is not in `tokens.json`. The customer look also uses the prototype's corner sizes (cards 22, inputs 15) where `tokens.json` says 18 and 12. The looks are in `apps/mobile/lib/core/ui/theme.dart`.

The Android emulator reaches your computer at `http://10.0.2.2:8000`, which is the default for dev builds.

Passwords are configuration, never committed. The database keeps only an Argon2 hash. The seed makes the admin `priveopapa` from `ADMIN_PASSWORD`, and running it again resets that password and ends any block on the login. Five wrong passwords block the admin for 15 minutes, then 1 hour, then 24 hours (CRW-ACC-07). To get in sooner on `dev`, run the `api-deploy` workflow by hand (Actions, Run workflow): it runs the seed. The demo customer and crew logins exist only where `SEED_DEMO_LOGINS` is `true`, until the admin can create real ones (Phase 2).

## Check before you push (macOS and Linux)

`tools/dev/check-local.sh` runs the same checks as the pipelines in section 2, on your machine. A run takes minutes, where a PostgreSQL run in CI takes 15 to 25. Run it before you push or open a pull request.

| Command | What it does |
|---|---|
| `tools/dev/check-local.sh` | API (ruff, tests on SQLite, the OpenAPI contract), the API tests again on a disposable local PostgreSQL, mobile (generated files, analyze, tests) and web (lint, tests, build) |
| `tools/dev/check-local.sh --changed` | Only the stages that the diff against `origin/main` touches, with the same path rules as the pipelines |
| `tools/dev/check-local.sh --only pg` | One stage: `api`, `pg`, `mobile`, `web` or `e2e` |
| `tools/dev/check-local.sh --no-pg` | Everything except the PostgreSQL run |
| `tools/dev/check-local.sh --e2e` | Also the Playwright browser tests (first run: `cd apps/web && npx playwright install chromium`) |

- **PostgreSQL:** install it once (`brew install postgresql@16` on macOS). The script finds it, starts a throwaway cluster inside the repo folder, and stops it afterwards. It never uses `DATABASE_URL` or a hosted database, and it reads no `.env`. Set `POSTGRES_BIN` for an install in another place.
- **Worktrees:** run it from the folder you changed. It checks that folder's code, even when the virtualenv belongs to another checkout. (Run alone, `scripts/export_openapi.py` imports the code of the checkout that made the virtualenv, which gives a wrong contract in a worktree. The script sets `PYTHONPATH` to avoid that.)
- **Generated files:** if the OpenAPI contract, the Dart API, the theme or the translations are stale, the script regenerates them and fails. Commit the regenerated files.
- **What it cannot run:** the golden-image tests (Linux only, skipped on macOS) and the `update-goldens` workflow. If a change moves pixels, add the label and let CI remake the images.
- **CI stays the final gate.** A pass here means the pipelines should pass, not that they are skipped.

## Dev and production are separate deployments

`dev` is the test server. It runs with `ENVIRONMENT=dev`, may have demo logins (`SEED_DEMO_LOGINS`) and a fixed sign-in code (`MOCK_EMAIL_CODE`), and is the only one the `api-deploy` workflow touches. Production is customer-facing: its own host, its own database, its own secrets and its own deploy workflow, with `ENVIRONMENT=prod`. In prod the server refuses to start if `SEED_DEMO_LOGINS`, `MOCK_*`, or `EMAIL_REDIRECT_TO` is set, if `TOKEN_SECRET` is shorter than 32 characters, or if `RESEND_API_KEY` or `CRON_SECRET` is missing, and the seed never creates demo logins. The production workflow does not exist yet; it is created with the AWS move.

## 2. The pipelines

| Workflow | Runs on | Does |
|---|---|---|
| `api-ci` | Pull request touching the API | Lint, pytest on an in-memory database and again on PostgreSQL, and a check that `openapi.json` matches the code |
| `mobile-ci` | Pull request touching the app, `tokens.json` or `openapi.json` | Theme, translations and API client up to date, `flutter analyze`, `flutter test` |
| `mobile-goldens` | The label `update-goldens` added to a pull request | Remakes the golden images on Linux and commits them to the branch. Push one more commit afterwards, since that commit does not start `mobile-ci` |
| `api-deploy` | Merge to `main` touching the API | Migrate and seed the `dev` database, deploy to `dev` on the host chosen by `DEPLOY_PROVIDER` (Vercel by default, or AWS), then smoke test |
| `mobile-integration` | Started by hand (`gh workflow run mobile-integration`). Also on a merge to `main` touching the app, but only when `RUN_EMULATOR_ON_MERGE` is `true` | Runs the app on an Android emulator against the `dev` API and signs in as each role. About 15 minutes |
| `mobile-android-release` | Merge to `main` touching the app | Test, build a signed bundle, upload to Play internal testing |

`api-deploy` has two jobs. `deploy-vercel` runs when `DEPLOY_PROVIDER` is empty or `vercel` and `VERCEL_PROJECT_ID` is set. `deploy-aws` runs when `DEPLOY_PROVIDER` is `aws` and `AWS_DEPLOY_ROLE_ARN` is set. A job with missing settings is skipped. `mobile-android-release` does nothing until `ANDROID_KEYSTORE_BASE64` is set. Neither fails while the accounts are missing.

To make a failing test block a merge, turn on branch protection for `main` and require `api-ci` and `mobile-ci`. **Open:** this is a GitHub setting that the owner must switch on.

## 3. Repository settings the pipelines need

**Variables** (Settings, Secrets and variables, Actions, Variables):

| Name | Value |
|---|---|
| `RUN_EMULATOR_ON_MERGE` | `true` runs `mobile-integration` on each merge to `main` that touches the app. Unset or anything else: it runs only when started by hand |
| `DEPLOY_PROVIDER` | `vercel` (default when empty) or `aws`. This is the switch |
| `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | From `.vercel/project.json` after `vercel link` (Vercel only) |
| `AWS_DEPLOY_ROLE_ARN` | The IAM role that GitHub assumes through OIDC |
| `AWS_REGION` | `ap-south-1` (Mumbai) |
| `ECR_REPOSITORY` | The ECR repository name |
| `ECS_CLUSTER`, `ECS_SERVICE`, `ECS_TASK_FAMILY` | The `dev` ECS names |
| `API_DEV_URL` | The public address of the `dev` API: the project's production domain on Vercel (for example `https://priveo-api.vercel.app`), or `https://api-dev.<your-domain>` on AWS. The app and the smoke test both use it |

Analytics (PostHog EU) is set by three repository variables. Both the mobile release build and the portal build in `api-deploy.yml` read them. Vite bakes the values into the portal, because the portal is built in GitHub Actions, not on Vercel.

| Variable | Meaning | If unset |
|---|---|---|
| `POSTHOG_KEY` | The PostHog EU project key (public by design) | Nothing is sent |
| `POSTHOG_HOST` | Ingestion host | `https://eu.i.posthog.com` |
| `POSTHOG_REPLAY` | `true` turns session replay on | Replay off |

A change takes effect on the next build. For a phone build, `push_apk.ps1 -Replay` reads the key from the `POSTHOG_KEY` environment variable.

To try the portal on your PC: `VITE_POSTHOG_KEY=phc_... VITE_POSTHOG_REPLAY=true npm run dev` in `apps/web`.

The AWS names (`AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`, `ECR_REPOSITORY`, `ECS_*`) are needed only when `DEPLOY_PROVIDER` is `aws`.

**Secrets:**

| Name | Value |
|---|---|
| `VERCEL_TOKEN` | A Vercel access token (Vercel only) |
| `DATABASE_URL` | The `dev` PostgreSQL address. The deploy uses it to migrate and seed. The same value is in the Vercel project's environment |
| `MOCK_CUSTOMER_PASSWORD`, `MOCK_CREW_PASSWORD`, `MOCK_ADMIN_PASSWORD` | The passwords of the demo customer, the demo crew member and the admin on `dev`. The deploy seeds them and the smoke test signs in with them |
| `ANDROID_KEYSTORE_BASE64` | The upload keystore, base64 encoded |
| `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` | The upload key details |
| `PLAY_SERVICE_ACCOUNT_JSON` | The Google Cloud service account key with Play Console access |

## 4. One-time setup, in order

**Vercel (default host)**

1. Sign in once: `npx vercel login`.
2. Create and link the project from `services/api`: `cd services/api && npx vercel link --yes --project priveo-api`. Leave the project's Root Directory empty and do not connect Git. The workflow deploys from `services/api`, and `vercel.json` sets the Singapore region (`sin1`) for the `dev` API, the same region as the Neon database, so each query is a short hop. Production on AWS runs in Mumbai with the database beside it.
3. Add the database: `npx vercel integration add neon --name priveo-dev`. The first time, accept Neon's terms in the browser when asked. It adds `DATABASE_URL` to the project. Copy that value into the GitHub secret `DATABASE_URL`.
4. Add the runtime environment variables `TOKEN_SECRET` (a long random value, 32 or more characters) and `ENVIRONMENT` (`dev`) to the project (Production). Use `npx vercel env add TOKEN_SECRET production` and `npx vercel env add ENVIRONMENT production`. Add `CRON_SECRET` too, or the scheduled jobs answer 503. The server will not start without `TOKEN_SECRET`, and a hosted server will not start unless `ENVIRONMENT` is set to exactly `dev` or `prod`. Add `ENVIRONMENT` **before** the first deploy of this change.
   - Until email is connected, also add `MOCK_EMAIL_CODE` (6 digits of your choice) the same way, then deploy again. It is the code every customer enters at first sign-in and after "Forgot password" on `dev`. No email is sent. Without it those two steps answer "Email is not set up yet". It does nothing when `ENVIRONMENT=prod`.
5. First deploy: `npx vercel deploy --prod`. Set `API_DEV_URL` to the project's `*.vercel.app` production domain. The app needs an address that needs no Vercel sign-in. The production domain is public under the default protection, but the per-deployment URLs are not.
6. Add the repository variables and secrets from section 3.

**AWS (switch with `DEPLOY_PROVIDER=aws`)**

1. **AWS:** create the `dev` resources (ECR repository, ECS Fargate service behind a load balancer with a certificate, a log group), a task definition whose first container is the API image and whose environment holds `TOKEN_SECRET` and the three `MOCK_*_PASSWORD` values (from Secrets Manager), and the GitHub OIDC role. Open: the plan does not choose Terraform, so a short script or the console is fine for Phase 0.
2. **Domain:** point `api-dev` at the load balancer.

**Android release (either host)**

1. **Upload key:** create it once and keep a backup outside the repository.
   `keytool -genkeypair -v -keystore upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`
   Then `base64 -w0 upload.jks` goes into `ANDROID_KEYSTORE_BASE64`.
2. **Play Console:** create the app `in.priveo.app` and turn on Play App Signing. **Upload the first bundle by hand** (build it with the command in the release workflow and upload it to the internal testing track). The Play API cannot create the first release of a new app. After that the pipeline takes over.
3. **Service account:** create it in Google Cloud, give it release access in Play Console, and store its JSON key as `PLAY_SERVICE_ACCOUNT_JSON`.
4. **Testers:** add the testers' Google accounts to the internal testing list.

## 5. Build number and versions

- The Android build number is the GitHub run number (`--build-number`). The version name comes from `apps/mobile/pubspec.yaml`.
- The API build number is the same run number, passed to the image as `BUILD_NUMBER`. `GET /v1/public/health` shows it.
- Phase 0 Play builds are the `prod` flavor (`in.priveo.app`, the Play app) started from the `dev` entry point with the `dev` API address. **Derived:** the owner has not chosen whether Play testers should get `in.priveo.app` or `in.priveo.app.dev` in Phase 0. A real `prod` build comes with Phase 8.

## 6. Not built yet

Phases 2 to 7 are on the branch `integration/mobile-phases-2-7` and are not on `main` until it is merged. Their gaps and stubs are in `docs/overnight-build-report.md`. The list below is from before that branch.

- iOS (0b): macOS job, fastlane `match`, TestFlight.
- Sending the customer's code by email (Resend). The first sign-in, set password and forgot password are built, and on `dev` the code is the fixed `MOCK_EMAIL_CODE`. The Resend sender is built and the key has been provided (25 Oct 2026). What is left is verifying the sending domain at Resend and setting `RESEND_API_KEY` and the from-address in the environment.
- The rest of Phase 1 sign-in: the web portal's cookie sign-in, and the admin screens that reset a password or sign someone out.
- The links to the Terms and the Privacy Policy on the sign-in screen.
- In the onboarding review (`ONB-25`): the vehicle photo (`ONB-22`, needs uploads) and the plan name (needs the plans). The review has one step for each vehicle, holding its parking, service preferences and plan together. **Derived:** the requirement lists these as separate steps and does not say how several vehicles are handled.
- On the customer home: the next service (needs scheduling; the card says "Not scheduled yet"), the vehicle photo, the "Today's clean is done" strip and the add-ons card. The crew and admin homes still serve mock data.
- Higher-resolution brand files. `apps/mobile/tool/gen_brand_mark.py` (needs Pillow) makes the icon, the splash mark, the in-app logo and the P mark from the owner's files in `docs/brand`. They are white with gold and low resolution, so they are only shown on the dark look and are slightly soft.
- Prototype content that needs data the API does not send yet: the car photo on the vehicle card and the vehicle variant.
- Branch protection on `main`. GitHub does not allow it on a private repository on the free plan, so a failing check does not block a merge yet. **Open:** GitHub Pro, a public repository, or leave it.
- An Android package build in `mobile-ci`. Only `mobile-integration` builds one, and it runs on request, so a native build error is not caught on the pull request.

## Try the admin portal on localhost

Run `tools\dev\portal-local.ps1` from the repo root. It starts the API on `http://localhost:8000` and the portal dev server on `http://localhost:5173/portal/`, which reloads on every edit. The database is the dev Neon database; no local copy is made. The first run pulls the Vercel environment into `services/api/.env.neon` (git-ignored, never printed). Use `-Refresh` after a Vercel variable changes. The script does not run migrations or the seed; the deploy does that. What you save while testing is real dev data.

### Run the portal against a local copy of the dev database

`tools\dev\portal-local.ps1 -Local` does the same as above but uses a local PostgreSQL (port 5433) holding a copy of the shared dev database, so nothing you do reaches Neon. The first run starts the local server and makes the copy with `tools\dev\local-db.ps1`; use `tools\dev\local-db.ps1 -Refresh` to copy again, and `-Stop` to stop the server. The copy lives in the git-ignored `.local-db` folder and holds real dev data. In this mode email, push and S3 are switched off. The copy is made by `services/api/scripts/copy_dev_db.py` (schema from the migrations, rows streamed from Neon), because Neon runs a newer PostgreSQL than the local `pg_dump`.
