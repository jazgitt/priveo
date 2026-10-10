# Build and release (Phase 0)

**Status:** 10 Oct 2026. Covers the Phase 0a Android path. The `dev` API host is Vercel by default and switches to AWS with `DEPLOY_PROVIDER=aws`. iOS (0b) is not built yet. Plan: `docs/build-plan.md`.

## 1. Run it on your machine

| What | Command (from the repo root) |
|---|---|
| API: install | `cd services/api && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"` |
| API: run | `MOCK_CUSTOMER_PASSWORD=... MOCK_CREW_PASSWORD=... MOCK_ADMIN_PASSWORD=... .venv/Scripts/python -m uvicorn app.main:app --port 8000` |
| API: lint and test | `.venv/Scripts/python -m ruff check . && .venv/Scripts/python -m pytest -q` |
| API: export the contract | `.venv/Scripts/python scripts/export_openapi.py` (writes `packages/api-contract/openapi.json`) |
| API: smoke test a running API | `SMOKE_CUSTOMER_PASSWORD=... SMOKE_CREW_PASSWORD=... SMOKE_ADMIN_PASSWORD=... python scripts/smoke_test.py <url>` |
| App: get packages | `cd apps/mobile && flutter pub get` |
| App: theme from tokens | `dart run tool/gen_theme.dart` (after changing `docs/brand/tokens.json`) |
| App: API client from the contract | `dart run tool/gen_api.dart` (after `packages/api-contract/openapi.json` changes) |
| App: translations | `flutter gen-l10n` (after changing `lib/l10n/app_en.arb`) |
| App: analyze and test | `flutter analyze && flutter test` |
| App: test against a live API | `flutter test test/live_api_test.dart --dart-define=LIVE_API_URL=<url> --dart-define=LIVE_PASSWORD=<mock password>`. When the three mock passwords differ, pass `LIVE_CUSTOMER_PASSWORD`, `LIVE_CREW_PASSWORD` and `LIVE_ADMIN_PASSWORD` instead |
| App: sign in as each role on a phone or emulator | `flutter test integration_test --dart-define=API_BASE_URL=<url> --dart-define=LIVE_CUSTOMER_PASSWORD=... --dart-define=LIVE_CREW_PASSWORD=... --dart-define=LIVE_ADMIN_PASSWORD=...` |
| App: run (dev) | `flutter run -t lib/main_dev.dart --dart-define=API_BASE_URL=<url>` |

The app has two Android flavors that install side by side: `dev` (`in.priveo.app.dev`, labelled "Priveo Dev") and `prod` (`in.priveo.app`, labelled "Priveo"). A command with no `--flavor` uses `dev`. Add `--flavor prod -t lib/main_prod.dart` for the other.

Each role has one look, whatever the phone's light or dark setting (owner decision, 10-Oct-26): the splash, login and customer screens are dark and follow the prototype; crew screens are plain white; admin screens are cream. **Derived:** the white crew background is not in `tokens.json`. The customer look also uses the prototype's corner sizes (cards 22, inputs 15) where `tokens.json` says 18 and 12. The looks are in `apps/mobile/lib/core/ui/theme.dart`.

The Android emulator reaches your computer at `http://10.0.2.2:8000`, which is the default for dev builds.

The mock passwords are configuration, never committed. An empty password switches that mock login off.

## 2. The pipelines

| Workflow | Runs on | Does |
|---|---|---|
| `api-ci` | Pull request touching the API | Lint, pytest, and a check that `openapi.json` matches the code |
| `mobile-ci` | Pull request touching the app, `tokens.json` or `openapi.json` | Theme, translations and API client up to date, `flutter analyze`, `flutter test` |
| `mobile-goldens` | The label `update-goldens` added to a pull request | Remakes the golden images on Linux and commits them to the branch. Push one more commit afterwards, since that commit does not start `mobile-ci` |
| `api-deploy` | Merge to `main` touching the API | Deploy to `dev` on the host chosen by `DEPLOY_PROVIDER` (Vercel by default, or AWS), then smoke test |
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

The AWS names (`AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`, `ECR_REPOSITORY`, `ECS_*`) are needed only when `DEPLOY_PROVIDER` is `aws`.

**Secrets:**

| Name | Value |
|---|---|
| `VERCEL_TOKEN` | A Vercel access token (Vercel only) |
| `MOCK_CUSTOMER_PASSWORD`, `MOCK_CREW_PASSWORD`, `MOCK_ADMIN_PASSWORD` | Used by the smoke test. Set the same values as environment variables on the host (Vercel project or ECS task) |
| `ANDROID_KEYSTORE_BASE64` | The upload keystore, base64 encoded |
| `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` | The upload key details |
| `PLAY_SERVICE_ACCOUNT_JSON` | The Google Cloud service account key with Play Console access |

## 4. One-time setup, in order

**Vercel (default host)**

1. Sign in once: `npx vercel login`.
2. Create and link the project from `services/api`: `cd services/api && npx vercel link --yes --project priveo-api`. Leave the project's Root Directory empty and do not connect Git. The workflow deploys from `services/api`, and `vercel.json` sets the Mumbai region (`bom1`).
3. Add the runtime environment variables to the project (Production): `TOKEN_SECRET` (a long random value), `MOCK_CUSTOMER_PASSWORD`, `MOCK_CREW_PASSWORD`, `MOCK_ADMIN_PASSWORD`. Use `npx vercel env add <NAME> production`.
4. First deploy: `npx vercel deploy --prod`. Set `API_DEV_URL` to the project's `*.vercel.app` production domain. The app needs an address that needs no Vercel sign-in. The production domain is public under the default protection, but the per-deployment URLs are not.
5. Add the repository variables and secrets from section 3.

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

- iOS (0b): macOS job, fastlane `match`, TestFlight.
- Higher-resolution brand files. `apps/mobile/tool/gen_brand_mark.py` (needs Pillow) makes the icon, the splash mark, the in-app logo and the P mark from the owner's files in `docs/brand`. They are white with gold and low resolution, so they are only shown on the dark look and are slightly soft.
- Prototype content that needs data the API does not send yet: the car photo on the vehicle card, the "Today's clean is done" strip, the service time window and the vehicle variant.
- Branch protection on `main`. GitHub does not allow it on a private repository on the free plan, so a failing check does not block a merge yet. **Open:** GitHub Pro, a public repository, or leave it.
- An Android package build in `mobile-ci`. Only `mobile-integration` builds one, and it runs on request, so a native build error is not caught on the pull request.
