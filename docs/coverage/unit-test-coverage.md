# Fresh automated test coverage — 13 October 2026

Baseline: `2c3ba73` on `integration/complete-build`, plus the uncommitted coverage work described here. These measurements come from newly executed suites, not earlier coverage reports. The threshold is **90% executable line coverage for each application area**, including shared code separately. An overall average cannot hide a role below the threshold.

| Application area | Covered / executable lines | Fresh line coverage | 90% gate |
|---|---:|---:|---|
| Customer Mobile | 4,659 / 5,164 | **90.22%** | Pass |
| Crew Mobile | 1,491 / 1,655 | **90.09%** | Pass |
| Admin Mobile | 1,384 / 1,518 | **91.17%** | Pass |
| Admin Web | 1,547 / 1,709 | **90.52%** | Pass |
| Shared backend/API | 8,710 / 9,377 | **92.89%** | Pass |
| Shared mobile/auth/UI | 935 / 1,007 | **92.85%** | Pass |
| Generated mobile API/localization | 4,026 / 4,027 | **99.98%** | Pass |
| Entire mobile application, including generated code | 12,495 / 13,371 | **93.45%** | Pass |
| All application sources combined | 22,752 / 24,457 | **93.03%** | Pass |

## Execution evidence

- Backend: **494 passed**, SQLite in-memory tests; clean run with line and branch instrumentation. Includes service-level and API/database regressions, not exclusively isolated unit tests.
- Mobile: **1,433 passed, 11 skipped**, clean full Flutter test run. Includes unit, widget, generated wire-contract and localization tests. The existing skips require Linux goldens or a live API; they do not count as passing tests.
- Admin Web: **99 passed**, full Vitest suite with V8 coverage and the persistent line threshold.
- Web TypeScript check and production build passed. Flutter analysis passed with no issues.
- No APK, real-device testing, live provider delivery, production migration or deployment was performed.

The OpenAPI cases exercise populated and nullable nested models, dates, lists and generated client calls against independent contract fixtures. The English catalogue cases check placeholder substitution and singular/plural forms. These cases increase the test count but are not 1,000 additional business scenarios.

## What is included

Backend coverage scans every module under `services/api/app`, including unimported modules. Web coverage includes every production TypeScript/TSX file under `apps/web/src`, including entry points and files not imported by existing tests; test files and test setup are excluded. Mobile coverage scans the `priveo` Dart package, includes generated sources, and checks every `lib/**/*.dart` file against the instrumented inventory. Only the constant-only theme-token library and export-only `main.dart` have no executable statements. No uncovered feature was excluded to reach the target.

Customer includes customer screens, money/change flows and customer support. Crew and Admin Mobile use their corresponding feature folders. Auth, networking and reusable UI are shared. The backend is shared across all clients and is not artificially counted as exclusive Customer, Crew or Admin coverage.

This is application runtime coverage. Repository development tools, migration-script source, third-party/native plugin implementations, fonts/assets, build configuration and platform scaffolding are outside these language-runner denominators. Migration behavior is exercised by existing backend tests; that does not imply migration-source or production migration coverage.

## Other coverage metrics

**90% line coverage does not mean 90% branch or function coverage.** Those thresholds have not been met:

| Metric | Backend | Admin Web |
|---|---:|---:|
| Branches | 79.62% | 80.91% |
| Statements | 92.89% | 88.29% |
| Functions | Not separately measured | 83.85% |

Flutter's LCOV run measures executable lines; branch coverage was not collected. Measured line coverage is not proof of complete requirement acceptance, device behavior, provider integration or correctness. The functional implementation backlog remains separate.

## Changes made for this measurement

Added API adapter, wire-contract, localization, validation, offline/retry, account-navigation, admin-action, payment/Spa, camera/video and upload-queue regressions. Repaired stale fixtures and test lifecycle issues exposed by running the previously deferred tests. Fixed a missing Home import and preserved backend explanations for direct Dio failures in customer money flows. Made the SQLite factory injectable so queue creation and legacy-owner upgrade callbacks are testable without a native database.

All coverage work is currently uncommitted.

## Repeat the measurement

Install the declared development dependencies first, then run from the repository root:

```powershell
.\tools\coverage\run.ps1
```

The script runs the three suites, exports fresh reports, checks the web build and Flutter analysis, and fails if any application area is below 90% line coverage or mobile executable source is missing from the instrumented inventory. `-SkipStaticChecks` skips only the build/analyzer checks. The backend uses a disposable in-memory SQLite database.

The machine-readable result, including exact counts and uncovered mobile line numbers, is [unit-test-coverage.json](unit-test-coverage.json). Raw tool outputs and HTML reports are ignored local artifacts; `tools/coverage/report.py` reads only the final tool reports, never the old `lcov.info` or requirement matrices.
