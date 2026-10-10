# Build and release (Phase 0)

**Status:** 9 Oct 2026. Covers the Phase 0a Android path. iOS (0b) is not built yet. Plan: `docs/build-plan.md`.

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
| App: translations | `flutter gen-l10n` (after changing `lib/l10n/app_en.arb`) |
| App: analyze and test | `flutter analyze && flutter test` |
| App: test against a live API | `flutter test test/live_api_test.dart --dart-define=LIVE_API_URL=<url> --dart-define=LIVE_PASSWORD=<mock password>` |
| App: run (dev) | `flutter run -t lib/main_dev.dart --dart-define=API_BASE_URL=<url>` |

The Android emulator reaches your computer at `http://10.0.2.2:8000`, which is the default for dev builds.

The mock passwords are configuration, never committed. An empty password switches that mock login off.

## 2. The pipelines

| Workflow | Runs on | Does |
|---|---|---|
| `api-ci` | Pull request touching the API | Lint, pytest, and a check that `openapi.json` matches the code |
| `mobile-ci` | Pull request touching the app or `tokens.json` | Theme and translations up to date, `flutter analyze`, `flutter test` |
| `api-deploy` | Merge to `main` touching the API | Build image, push to ECR, deploy to ECS `dev`, smoke test |
| `mobile-android-release` | Merge to `main` touching the app | Test, build a signed bundle, upload to Play internal testing |

`api-deploy` is skipped until `AWS_DEPLOY_ROLE_ARN` is set. `mobile-android-release` does nothing until `ANDROID_KEYSTORE_BASE64` is set. Neither fails while the accounts are missing.

To make a failing test block a merge, turn on branch protection for `main` and require `api-ci` and `mobile-ci`. **Open:** this is a GitHub setting that the owner must switch on.

## 3. Repository settings the pipelines need

**Variables** (Settings, Secrets and variables, Actions, Variables):

| Name | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | The IAM role that GitHub assumes through OIDC |
| `AWS_REGION` | `ap-south-1` (Mumbai) |
| `ECR_REPOSITORY` | The ECR repository name |
| `ECS_CLUSTER`, `ECS_SERVICE`, `ECS_TASK_FAMILY` | The `dev` ECS names |
| `API_DEV_URL` | For example `https://api-dev.<your-domain>` |

**Secrets:**

| Name | Value |
|---|---|
| `MOCK_CUSTOMER_PASSWORD`, `MOCK_CREW_PASSWORD`, `MOCK_ADMIN_PASSWORD` | Used by the smoke test. Set the same values as configuration on the ECS task |
| `ANDROID_KEYSTORE_BASE64` | The upload keystore, base64 encoded |
| `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD` | The upload key details |
| `PLAY_SERVICE_ACCOUNT_JSON` | The Google Cloud service account key with Play Console access |

## 4. One-time setup, in order

1. **AWS:** create the `dev` resources (ECR repository, ECS Fargate service behind a load balancer with a certificate, a log group), a task definition whose first container is the API image and whose environment holds `TOKEN_SECRET` and the three `MOCK_*_PASSWORD` values (from Secrets Manager), and the GitHub OIDC role. Open: the plan does not choose Terraform, so a short script or the console is fine for Phase 0.
2. **Domain:** point `api-dev` at the load balancer.
3. **Upload key:** create it once and keep a backup outside the repository.
   `keytool -genkeypair -v -keystore upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`
   Then `base64 -w0 upload.jks` goes into `ANDROID_KEYSTORE_BASE64`.
4. **Play Console:** create the app `in.priveo.app` and turn on Play App Signing. **Upload the first bundle by hand** (build it with the command in the release workflow and upload it to the internal testing track). The Play API cannot create the first release of a new app. After that the pipeline takes over.
5. **Service account:** create it in Google Cloud, give it release access in Play Console, and store its JSON key as `PLAY_SERVICE_ACCOUNT_JSON`.
6. **Testers:** add the testers' Google accounts to the internal testing list.

## 5. Build number and versions

- The Android build number is the GitHub run number (`--build-number`). The version name comes from `apps/mobile/pubspec.yaml`.
- The API build number is the same run number, passed to the image as `BUILD_NUMBER`. `GET /v1/public/health` shows it.
- Phase 0 Play builds use the `dev` entry point and the `dev` API address. A `prod` build comes with Phase 8.

## 6. Not built yet

- iOS (0b): macOS job, fastlane `match`, TestFlight.
- Native Android flavors with their own application IDs.
- A native splash screen. The animated splash inside the app is done.
- Golden tests. Make them on the CI machine, since Windows and Linux render fonts differently.
- An `integration_test` run on a device or emulator.
- A generated API client. The app has hand-written models for the three homes.
